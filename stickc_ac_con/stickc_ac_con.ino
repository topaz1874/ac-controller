#include <M5StickCPlus.h>
#include <IRremoteESP8266.h>
#include <IRsend.h>
#include <WiFi.h>
#include <PubSubClient.h>

const uint16_t kIrLed = 9;  // IR LED 在 GPIO9
IRsend irsend(kIrLed);      // 设置IR发送对象

// 格力空调协议常量定义
const uint16_t kGreeBitMark = 620;      // 位标记持续时间（微秒）
const uint16_t kGreeOneSpace = 1600;    // 1位的空间持续时间
const uint16_t kGreeZeroSpace = 540;    // 0位的空间持续时间
const uint16_t kGreeHdrMark = 9000;     // 头部标记持续时间
const uint16_t kGreeHdrSpace = 4500;    // 头部空间持续时间
const uint16_t kGreeGapSpace = 19980;   // 消息之间的间隔

// 开机命令数据
const uint8_t kGreePowerOnLength = 8;  // 命令长度（字节）

// 全局变量记录当前状态
bool isPowerOn = false;
uint8_t currentTemp = 25;  // 添加当前温度变量

// Wi-Fi连接参数
const char* ssid = "office";       // Wi-Fi名称
const char* password = "gdzsam632"; // Wi-Fi密码

// MQTT服务器设置
const char* mqtt_server = "192.168.1.59"; // MQTT服务器地址
const char* mqtt_topic = "aircon";        // MQTT主题
const int mqtt_port = 1883;               // MQTT端口

// 创建网络客户端实例
WiFiClient espClient;              // Wi-Fi客户端实例
PubSubClient client(espClient);    // MQTT客户端实例

// LED 控制相关定义
const uint8_t LED_PIN = 10;      // LED引脚
const uint8_t LED_CHANNEL = 0;   // LED使用的LEDC通道
const double LED_FREQ = 5000;    // LED PWM频率
const uint8_t LED_RESOLUTION = 8; // LED PWM分辨率（8位，0-255）

// 函数声明
void sendCommand(uint8_t temperature = 25);  // 在文件开头声明函数
void updateDisplay();
void connectMQTT();
void beepFeedback();
void breatheLED();
void breatheLEDOn();
void breatheLEDOff();

// 校验和计算函数
uint8_t calculateChecksum(const uint8_t *block, uint16_t length) {
  uint8_t sum = 10;  // 起始值为10
  
  // 计算前4个字节的低4位
  for (uint8_t i = 0; i < 4 && i < length - 1; i++) {
    sum += (block[i] & 0b1111);
  }
  
  // 计算剩余字节的高4位
  for (uint8_t i = 4; i < length - 1; i++) {
    sum += (block[i] >> 4);
  }
  
  // 取低4位
  return sum & 0b1111;
}

// 温度转换函数 (16-30度)
uint8_t temperatureToByte(uint8_t temp) {
  if (temp < 16) temp = 16;
  if (temp > 30) temp = 30;
  return (temp - 16) & 0b1111;  // 0000 = 16度, 1110 = 30度
}

// 蜂鸣器反馈函数
void beepFeedback() {
  // 第一声蜂鸣
  M5.Beep.tone(4000);  // 开始蜂鸣
  delay(50);           // 持续50ms
  M5.Beep.mute();      // 停止蜂鸣
  
  delay(100);          // 间隔100ms
  
  // 第二声蜂鸣
  M5.Beep.tone(4000);  // 开始蜂鸣
  delay(50);           // 持续50ms
  M5.Beep.mute();      // 停止蜂鸣
}

// LED 呼吸灯效果 - 开机（渐变）
void breatheLEDOn() {
  // 渐亮
  for(int i = 0; i < 255; i++) {
    ledcWrite(LED_CHANNEL, i);
    delay(1);
  }
  
  // 保持最亮
  delay(100);
  
  // 渐暗
  for(int i = 255; i >= 0; i--) {
    ledcWrite(LED_CHANNEL, i);
    delay(1);
  }
  
  // 确保完全关闭
  ledcWrite(LED_CHANNEL, 0);
}

// LED 呼吸灯效果 - 关机（快速闪烁两次）
void breatheLEDOff() {
  // 第一次闪烁
  ledcWrite(LED_CHANNEL, 255);
  delay(100);
  ledcWrite(LED_CHANNEL, 0);
  delay(100);
  
  // 第二次闪烁
  ledcWrite(LED_CHANNEL, 255);
  delay(100);
  ledcWrite(LED_CHANNEL, 0);
}

// MQTT消息回调函数 - 当收到MQTT消息时被调用
void callback(char* topic, byte* payload, unsigned int length) {
  // 创建一个空字符串用于存储接收到的消息
  String message = "";
  // 将接收到的字节数组转换为字符串
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  // 处理开机命令：如果收到"on"且当前是关机状态
  if (message == "on" && !isPowerOn) {
    isPowerOn = true;                   // 更新开关状态为开机
    sendCommand(currentTemp);           // 发送红外开机命令，使用当前温度
    client.publish(mqtt_topic, "stickc send on");   // 发送MQTT确认消息
    breatheLEDOn();                     // 开机呼吸灯效果
    beepFeedback();                     // 蜂鸣器提示音
    updateDisplay();                    // 更新显示屏内容
  } 
  // 处理关机命令：如果收到"off"且当前是开机状态
  else if (message == "off" && isPowerOn) {
    isPowerOn = false;                  // 更新开关状态为关机
    sendCommand(currentTemp);           // 发送红外关机命令，使用当前温度
    client.publish(mqtt_topic, "stickc send off");  // 发送MQTT确认消息
    breatheLEDOff();                     // 关机呼吸灯效果
    beepFeedback();                     // 蜂鸣器提示音
    updateDisplay();                    // 更新显示屏内容
  }
  // 处理温度设置命令：检查消息是否以"set "开头
  else if (message.startsWith("set ")) {
    String tempStr = message.substring(4);  // 从第4个字符开始提取温度值
    int temp = tempStr.toInt();            // 将字符串转换为整数
    if (temp >= 16 && temp <= 30) {        // 检查温度是否在有效范围内（16-30度）
      currentTemp = temp;                   // 更新当前温度值
      sendCommand(currentTemp);             // 发送红外温度设置命令
      breatheLEDOn();                         // 温度设置使用开机效果
      client.publish(mqtt_topic, 
        String("stickc send temp:" + String(currentTemp)).c_str());  // 发送确认消息
      beepFeedback();                       // 蜂鸣器提示音
      updateDisplay();                      // 更新显示屏内容
    }
  }
}

// 连接MQTT服务器
void connectMQTT() {
  while (!client.connected()) {                  // 如果未连接到MQTT服务器
    String clientId = "M5StickC-";              // 创建随机客户端ID
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {     // 尝试连接
      client.subscribe(mqtt_topic);              // 订阅主题
    } else {
      delay(5000);                              // 连接失败等待5秒
    }
  }
}

// 更新显示屏函数 - 显示当前状态信息
void updateDisplay() {
  M5.Lcd.fillScreen(BLACK);           // 清空屏幕，背景设为黑色
  M5.Lcd.setCursor(0, 0);            // 将光标位置设置到屏幕左上角
  
  // 显示WiFi网络信息
  M5.Lcd.printf("SSID: %s\n",        // 显示WiFi名称
                ssid);
  M5.Lcd.printf("RSSI: %ddBm\n",     // 显示WiFi信号强度（分贝毫瓦）
                WiFi.RSSI());
  
  // 显示空调电源状态
  M5.Lcd.printf("Power: %s\n",       // 显示开关机状态
                isPowerOn ? "ON" : "OFF");
  
  // 显示当前设置的温度
  M5.Lcd.printf("Temp: %dC\n",       // 显示温度值，单位：摄氏度
                currentTemp);
}

// 初始化设置
void setup() {
  // 初始化 M5StickC Plus
  M5.begin();
  
  // 设置LED PWM
  ledcSetup(LED_CHANNEL, LED_FREQ, LED_RESOLUTION);
  ledcAttachPin(LED_PIN, LED_CHANNEL);
  ledcWrite(LED_CHANNEL, 0);  // 确保LED初始状态为关闭
  
  // 设置显示屏方向和字体
  M5.Lcd.setRotation(3);
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setTextSize(2);
  
  // 初始化红外发射器
  irsend.begin();
  
  // 连接WiFi
  WiFi.begin(ssid, password);
  
  // 显示连接状态
  M5.Lcd.setCursor(0, 0);
  M5.Lcd.print("Connecting to WiFi");
  
  // 等待WiFi连接
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    M5.Lcd.print(".");
  }
  
  // 显示IP地址
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);
  M5.Lcd.print("WiFi connected");
  M5.Lcd.setCursor(0, 20);
  M5.Lcd.print("IP: ");
  M5.Lcd.println(WiFi.localIP());
  
  // 设置MQTT服务器
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  
  // 初始化显示
  updateDisplay();
}

// 发送命令函数实现
void sendCommand(uint8_t temperature) {
  // 定义第一个命令
  uint8_t powerOnCommand[8] = {
    isPowerOn ? 0b00001001 : 0b00000001,  // 第0字节：开机0x09/关机0x01
    0b00000000,  // 第1字节：温度（将被设置）
    0b00100000,  // 第2字节：默认设置
    0b01010000,  // 第3字节：默认设置
    0b00000000,  // 第4字节：默认设置
    0b01000000,  // 第5字节：默认设置
    0b00000000,  // 第6字节：默认设置
    0b00000000   // 第7字节：校验和
  };

  uint8_t powerOnCommand2[8] = {
    isPowerOn ? 0b00001001 : 0b00000001,  // 第0字节：开机0x09/关机0x01
    0b00000000,  // 第1字节：温度（将被设置）
    0b00100000,  // 第2字节：默认设置
    0b01110000,  // 第3字节：默认设置
    0b00000000,  // 第4字节：默认设置
    0b00000000,  // 第5字节：默认设置
    0b00000000,  // 第6字节：默认设置
    0b00000000   // 第7字节：校验和
  };

  // 设置温度
  uint8_t tempByte = temperatureToByte(temperature);
  powerOnCommand[1] = tempByte;
  powerOnCommand2[1] = tempByte;

  // 计算校验和
  uint8_t checksum1 = calculateChecksum(powerOnCommand, 8);
  powerOnCommand[7] = checksum1 << 4;
  
  uint8_t checksum2 = calculateChecksum(powerOnCommand2, 8);
  powerOnCommand2[7] = checksum2 << 4;

  // 第一个命令 - Block #1 头部和前4字节数据
  irsend.sendGeneric(kGreeHdrMark, kGreeHdrSpace,  // 头部标记和空间
                    kGreeBitMark, kGreeOneSpace,    // 1位的标记和空间
                    kGreeBitMark, kGreeZeroSpace,   // 0位的标记和空间
                    0, 0,                           // 无Footer
                    powerOnCommand, 4,              // 发送前4字节数据
                    38, false, 0, 50);              // 载波频率、LSB、占空比
  
  // 第一个命令 - Block #1 footer (3位结尾标记B010)
  irsend.sendGeneric(0, 0,                         // 无头部
                    kGreeBitMark, kGreeOneSpace,    // 1位的标记和空间
                    kGreeBitMark, kGreeZeroSpace,   // 0位的标记和空间
                    kGreeBitMark, kGreeGapSpace,    // Footer标记和空间
                    0b010, 3,                       // 发送结尾标记(010)
                    38, false, 0, 50);              // 载波频率、LSB、占空比
  
  // 第一个命令 - Block #1 后4字节数据
  irsend.sendGeneric(0, 0,                         // 无头部
                    kGreeBitMark, kGreeOneSpace,    // 1位的标记和空间
                    kGreeBitMark, kGreeZeroSpace,   // 0位的标记和空间
                    kGreeBitMark, kGreeGapSpace*2,    // Footer标记和空间
                    powerOnCommand + 4,             // 发送后4字节数据
                    kGreePowerOnLength - 4,         // 剩余字节数
                    38, false, 0, 50);              // 载波频率、LSB、占空比


  // 第二个命令 - Block #2 头部和前4字节数据
  irsend.sendGeneric(kGreeHdrMark, kGreeHdrSpace,  // 头部标记和空间
                    kGreeBitMark, kGreeOneSpace,    // 1位的标记和空间
                    kGreeBitMark, kGreeZeroSpace,   // 0位的标记和空间
                    0, 0,                           // 无Footer
                    powerOnCommand2, 4,             // 发送前4字节数据
                    38, false, 0, 50);              // 载波频率、LSB、占空比
  
  // 第二个命令 - Block #2 footer (3位结尾标记B010)
  irsend.sendGeneric(0, 0,                         // 无头部
                    kGreeBitMark, kGreeOneSpace,    // 1位的标记和空间
                    kGreeBitMark, kGreeZeroSpace,   // 0位的标记和空间
                    kGreeBitMark, kGreeGapSpace,    // Footer标记和空间
                    0b010, 3,                       // 发送结尾标记(010)
                    38, false, 0, 50);              // 载波频率、LSB、占空比
  
  // 第二个命令 - Block #2 后4字节数据
  irsend.sendGeneric(0, 0,                         // 无头部
                    kGreeBitMark, kGreeOneSpace,    // 1位的标记和空间
                    kGreeBitMark, kGreeZeroSpace,   // 0位的标记和空间
                    kGreeBitMark, kGreeGapSpace*2,    // Footer标记和空间
                    powerOnCommand2 + 4,            // 发送后4字节数据
                    kGreePowerOnLength - 4,         // 剩余字节数
                    38, false, 0, 50);              // 载波频率、LSB、占空比
}

// 处理按钮事件
void handleButton() {
  M5.update();  // 更新按钮状态
  
  if (M5.BtnA.wasPressed()) {  // 如果按下按钮A
    isPowerOn = !isPowerOn;    // 切换电源状态
    if (isPowerOn) {
      client.publish(mqtt_topic, "stickc send on");
      sendCommand(currentTemp);  // 开机时发送当前温度设置
      breatheLEDOn();           // 开机呼吸灯效果
    } else {
      client.publish(mqtt_topic, "stickc send off");
      breatheLEDOff();          // 关机呼吸灯效果
    }
    beepFeedback();           // 蜂鸣器提示音
    updateDisplay();          // 更新显示
  }
  
  if (M5.BtnB.wasPressed()) {  // 如果按下按钮B
    if (isPowerOn) {           // 只在开机状态下调节温度
      currentTemp++;           // 增加温度
      if (currentTemp > 30) currentTemp = 16;  // 温度循环
      sendCommand(currentTemp);
      client.publish(mqtt_topic, String("stickc send temp:" + String(currentTemp)).c_str());
      breatheLEDOn();         // 温度调节使用开机效果
      beepFeedback();        // 蜂鸣器提示音
      updateDisplay();       // 更新显示
    }
  }
}

// 主循环
void loop() {
  M5.update();
  
  // 检查Wi-Fi连接
  if (WiFi.status() != WL_CONNECTED) {         // 如果Wi-Fi断开
    WiFi.begin(ssid, password);                // 尝试重新连接
  }
  
  // 检查MQTT连接
  if (!client.connected()) {                   // 如果MQTT断开
    connectMQTT();                            // 尝试重新连接
  }
  client.loop();                              // MQTT消息处理
  
  handleButton();                              // 处理按钮事件
}