#include <M5StickCPlus.h>     // M5StickC Plus 库
#include <IRremoteESP8266.h>   // 红外发射库
#include <IRsend.h>            // 红外发送功能库
#include <WiFi.h>              // Wi-Fi连接库
#include <PubSubClient.h>      // MQTT客户端库

const uint16_t kIrLed = 9;     // IR LED 在 GPIO9
IRsend irsend(kIrLed);         // 设置IR发送对象

// 格力空调协议常量定义
const uint16_t kGreeBitMark = 620;      // 位标记持续时间（微秒）
const uint16_t kGreeOneSpace = 1600;    // 1位的空间持续时间
const uint16_t kGreeZeroSpace = 540;    // 0位的空间持续时间
const uint16_t kGreeHdrMark = 9000;     // 头部标记持续时间
const uint16_t kGreeHdrSpace = 4500;    // 头部空间持续时间
const uint16_t kGreeGapSpace = 19980;   // 消息之间的间隔

// 开机命令数据
const uint8_t kGreePowerOnLength = 8;   // 命令长度（字节）

// 全局变量记录当前状态
bool isPowerOn = false;                 // 电源开关状态
uint8_t currentTemp = 25;               // 当前温度设置
uint8_t tempToSend = 0;                 // 等待发送的温度值
unsigned long tempSetTime = 0;          // 上次设置温度的时间
const int TEMP_SEND_DELAY = 1000;       // 温度发送延迟(毫秒)
bool tempChanged = false;               // 温度是否已修改

// Wi-Fi连接参数
const char* ssid1 = "office";           // 第一个Wi-Fi名称
const char* ssid2 = "office_2.4";       // 第二个Wi-Fi名称
const char* password = "gdzsam632";     // Wi-Fi密码
const int WIFI_TIMEOUT = 60000;         // Wi-Fi连接超时时间(1分钟)
unsigned long wifiStartTime = 0;        // Wi-Fi连接开始时间

// MQTT服务器设置
const char* mqtt_server = "192.168.1.59";      // MQTT服务器地址
const char* mqtt_sub_topic = "stickc/aircon";  // MQTT订阅主题
const char* mqtt_pub_topic = "stickc/up";      // MQTT发布主题
const int mqtt_port = 1883;                    // MQTT端口

// API指令集定义
// 控制指令 (发送到 stickc/aircon 主题)
const char* API_POWER_ON = "api/power/on";     // 开机指令
const char* API_POWER_OFF = "api/power/off";   // 关机指令
const char* API_TEMP_PREFIX = "api/temp/";     // 温度设置指令前缀，后跟温度值(16-30)
const char* API_STATUS = "api/status";         // 状态查询指令

// 状态反馈 (发送到 stickc/up 主题)
// 设备上线: {"device":"stickc","status":"online"}
// 电源状态: {"status":"on|off","temp":当前温度}

// 创建网络客户端实例
WiFiClient espClient;                    // Wi-Fi客户端实例
PubSubClient client(espClient);          // MQTT客户端实例

// 按键长按检测
const int LONG_PRESS_TIME = 2000;        // 长按时间阈值(2秒)
unsigned long btnAPressTime = 0;         // 按钮A按下时间
bool btnALongPressed = false;            // 按钮A是否长按

// 调试模式设置
bool debugMode = true;                  // 调试模式默认开启

// 函数声明
void sendCommand(uint8_t temperature = 25);          // 发送红外命令
void updateDisplay();                                // 更新显示屏
void connectMQTT();                                  // 连接MQTT服务器
void beepFeedback();                                 // 蜂鸣器反馈
void connectToStrongestWiFi();                       // 连接信号最强的WiFi
void restartDevice();                                // 重启设备
void publishMessage(const char* topic, const char* payload); // 发布MQTT消息
void checkAndSendTemp();                             // 检查并发送温度命令

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
  if (temp < 16) temp = 16;    // 最低温度限制
  if (temp > 30) temp = 30;    // 最高温度限制
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

// 连接信号最强的Wi-Fi网络
void connectToStrongestWiFi() {
  M5.Lcd.fillScreen(BLACK);                  // 清空屏幕
  M5.Lcd.setCursor(0, 0);                    // 设置光标位置
  M5.Lcd.println("Scanning WiFi...");        // 显示扫描信息
  
  // 记录开始连接时间
  wifiStartTime = millis();                  // 记录当前时间
  
  // 扫描可用网络
  int networksFound = WiFi.scanNetworks();   // 开始Wi-Fi扫描
  
  if (networksFound == 0) {                  // 如果没找到网络
    M5.Lcd.println("No networks found!");
    return;
  }
  
  int rssi1 = -100;  // office 信号强度初始值
  int rssi2 = -100;  // office_2.4 信号强度初始值
  
  // 查找目标网络的信号强度
  for (int i = 0; i < networksFound; i++) {  // 遍历所有找到的网络
    if (WiFi.SSID(i) == ssid1) {             // 检查是否是第一个目标网络
      rssi1 = WiFi.RSSI(i);                  // 记录信号强度
      M5.Lcd.printf("%s: %d dBm\n", ssid1, rssi1);
    }
    if (WiFi.SSID(i) == ssid2) {             // 检查是否是第二个目标网络
      rssi2 = WiFi.RSSI(i);                  // 记录信号强度
      M5.Lcd.printf("%s: %d dBm\n", ssid2, rssi2);
    }
  }
  
  // 选择信号更强的网络
  const char* selectedSSID;
  if (rssi1 > rssi2 && rssi1 > -90) {        // 如果第一个网络信号更强
    selectedSSID = ssid1;
  } else if (rssi2 > -90) {                  // 如果第二个网络信号足够强
    selectedSSID = ssid2;
  } else {
    // 如果两个网络信号都很弱，选择第二个（优先office_2.4）
    selectedSSID = ssid2;
  }
  
  M5.Lcd.printf("Connecting to %s\n", selectedSSID); // 显示选择的网络
  
  // 连接选中的网络
  WiFi.begin(selectedSSID, password);        // 开始连接Wi-Fi
  
  // 等待WiFi连接
  int attempts = 0;                          // 连接尝试次数
  while (WiFi.status() != WL_CONNECTED && attempts < 20) { // 等待连接或超时
    delay(500);                              // 每500ms检查一次
    M5.Lcd.print(".");                       // 显示进度
    attempts++;                              // 增加尝试次数
  }
  
  if (WiFi.status() == WL_CONNECTED) {       // 如果连接成功
    M5.Lcd.fillScreen(BLACK);                // 清空屏幕
    M5.Lcd.setCursor(0, 0);                  // 重置光标位置
    M5.Lcd.print("WiFi connected");          // 显示连接成功
    M5.Lcd.setCursor(0, 20);                 // 移动光标
    M5.Lcd.printf("SSID: %s\n", selectedSSID); // 显示连接的SSID
    M5.Lcd.printf("RSSI: %d dBm\n", WiFi.RSSI()); // 显示信号强度
    M5.Lcd.printf("IP: %s\n", WiFi.localIP().toString().c_str()); // 显示IP地址
  } else {                                   // 如果连接失败
    M5.Lcd.println("\nConnection failed!");
    // 如果连接失败，尝试另一个网络
    const char* fallbackSSID = (selectedSSID == ssid1) ? ssid2 : ssid1;
    M5.Lcd.printf("Trying %s\n", fallbackSSID);
    WiFi.begin(fallbackSSID, password);      // 尝试备用网络
  }
}

// 重启设备
void restartDevice() {
  M5.Lcd.fillScreen(BLACK);                  // 清空屏幕
  M5.Lcd.setCursor(0, 0);                    // 设置光标位置
  M5.Lcd.println("Restarting...");           // 显示重启信息
  delay(1000);                               // 等待1秒
  ESP.restart();                             // 重启设备
}

// 发布MQTT消息并打印调试信息
void publishMessage(const char* topic, const char* payload) {
  // 打印调试信息到屏幕
  M5.Lcd.fillScreen(BLACK);                  // 清空屏幕
  M5.Lcd.setCursor(0, 0);                    // 设置光标位置
  M5.Lcd.println("MQTT Publish:");           // 显示发布标题
  M5.Lcd.printf("Topic: %s\n", topic);       // 显示主题
  M5.Lcd.printf("Payload: %s\n", payload);   // 显示内容
  
  // 如果开启调试模式且Serial可用，打印到Serial
  if (debugMode && Serial) {
    Serial.printf("MQTT Publish - Topic: %s, Payload: %s\n", topic, payload);
  }
  
  // 发布消息
  boolean result = client.publish(topic, payload); // 发布MQTT消息
  
  // 显示发布结果
  M5.Lcd.printf("Result: %s\n", result ? "Success" : "Failed");
  
  // 如果开启调试模式且Serial可用，打印结果到Serial
  if (debugMode && Serial) {
    Serial.printf("Publish Result: %s\n", result ? "Success" : "Failed");
  }
  
  // 2秒后恢复正常显示
  delay(2000);                               // 等待2秒
  updateDisplay();                           // 更新正常显示
}

// 检查并发送温度命令
void checkAndSendTemp() {
  // 如果温度发生变化且延迟时间已到
  if (tempChanged && (millis() - tempSetTime >= TEMP_SEND_DELAY)) {
    currentTemp = tempToSend;                // 更新当前温度为等待发送的温度
    sendCommand(currentTemp);                // 发送温度命令
    
    // 发送温度更新状态
    String payload = "{\"status\":\"" + String(isPowerOn ? "on" : "off") + 
                    "\",\"temp\":" + String(currentTemp) + "}";
    publishMessage(mqtt_pub_topic, payload.c_str()); // 发布更新后的状态
    
    tempChanged = false;                     // 重置温度变化标志
    updateDisplay();                         // 更新显示
  }
}

// MQTT消息回调函数 - 当收到MQTT消息时被调用
void callback(char* topic, byte* payload, unsigned int length) {
  // 创建一个空字符串用于存储接收到的消息
  String message = "";
  // 将接收到的字节数组转换为字符串
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  // 处理API命令
  if (message == API_POWER_ON && !isPowerOn) {
    // 开机命令: api/power/on
    isPowerOn = true;                   // 更新开关状态为开机
    sendCommand(currentTemp);           // 发送红外开机命令，使用当前温度
    String payload = "{\"status\":\"on\",\"temp\":" + String(currentTemp) + "}";
    publishMessage(mqtt_pub_topic, payload.c_str());
    beepFeedback();                     // 蜂鸣器提示音
    updateDisplay();                    // 更新显示屏内容
  } 
  // 处理关机命令
  else if (message == API_POWER_OFF && isPowerOn) {
    // 关机命令: api/power/off
    isPowerOn = false;                  // 更新开关状态为关机
    sendCommand(currentTemp);           // 发送红外关机命令，使用当前温度
    String payload = "{\"status\":\"off\",\"temp\":" + String(currentTemp) + "}";
    publishMessage(mqtt_pub_topic, payload.c_str());
    beepFeedback();                     // 蜂鸣器提示音
    updateDisplay();                    // 更新显示屏内容
  }
  // 处理温度设置命令
  else if (message.startsWith(API_TEMP_PREFIX)) {
    // 温度设置命令: api/temp/XX (XX为16-30之间的温度值)
    String tempStr = message.substring(strlen(API_TEMP_PREFIX));  // 提取温度值
    int temp = tempStr.toInt();            // 将字符串转换为整数
    if (temp >= 16 && temp <= 30) {        // 检查温度是否在有效范围内（16-30度）
      currentTemp = temp;                   // 更新当前温度值
      sendCommand(currentTemp);             // 发送红外温度设置命令
      String payload = "{\"status\":\"" + String(isPowerOn ? "on" : "off") + "\",\"temp\":" + String(currentTemp) + "}";
      publishMessage(mqtt_pub_topic, payload.c_str());
      beepFeedback();                       // 蜂鸣器提示音
      updateDisplay();                      // 更新显示屏内容
    }
  }
  // 处理状态查询命令
  else if (message == API_STATUS) {
    // 状态查询命令: api/status
    // 返回JSON格式的当前状态
    String payload = "{\"status\":\"" + String(isPowerOn ? "on" : "off") + "\",\"temp\":" + String(currentTemp) + "}";
    publishMessage(mqtt_pub_topic, payload.c_str());
  }
}

// 连接MQTT服务器
void connectMQTT() {
  while (!client.connected()) {                  // 如果未连接到MQTT服务器
    String clientId = "M5StickC-";              // 创建随机客户端ID
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {     // 尝试连接
      client.subscribe(mqtt_sub_topic);         // 订阅主题
      // 发送上线消息，JSON格式
      publishMessage(mqtt_pub_topic, "{\"device\":\"stickc\",\"status\":\"online\"}");
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
  const char* currentSSID = WiFi.SSID().c_str(); // 获取当前连接的SSID
  M5.Lcd.printf("SSID: %s\n", currentSSID);      // 显示当前Wi-Fi名称
  M5.Lcd.printf("RSSI: %ddBm\n", WiFi.RSSI());   // 显示Wi-Fi信号强度
  
  // 显示空调电源状态
  M5.Lcd.printf("Power: %s\n", isPowerOn ? "ON" : "OFF"); // 显示开关机状态
  
  // 显示当前设置的温度
  M5.Lcd.printf("Temp: %dC\n", currentTemp);     // 显示温度值，单位：摄氏度
  
  // 如果有待发送的温度变更，显示预览
  if (tempChanged) {
    M5.Lcd.printf("Set to: %dC\n", tempToSend);   // 显示即将设置的温度
  }
}

// 初始化设置
void setup() {
  // 初始化串口通信
  Serial.begin(115200);                    // 设置串口波特率
  
  // 初始化 M5StickC Plus
  M5.begin();
  
  // 设置显示屏方向和字体
  M5.Lcd.setRotation(3);                   // 设置屏幕旋转方向
  M5.Lcd.fillScreen(BLACK);                // 清空屏幕
  M5.Lcd.setTextSize(2);                   // 设置文字大小
  
  // 初始化红外发射器
  irsend.begin();                          // 初始化红外发射功能
  
  if (debugMode && Serial) {               // 如果调试模式开启且串口可用
    Serial.println("M5StickC Plus Air Conditioner Controller");
    Serial.println("Debug mode enabled");
    Serial.println("Initializing...");
  }
  
  // 连接信号最强的WiFi
  connectToStrongestWiFi();
  
  // 设置MQTT服务器
  client.setServer(mqtt_server, 1883);     // 设置MQTT服务器
  client.setCallback(callback);            // 设置回调函数
  
  // 初始化显示
  updateDisplay();                         // 更新显示屏内容
  
  if (debugMode && Serial) {               // 如果调试模式开启且串口可用
    Serial.println("Initialization complete");
  }
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
  uint8_t tempByte = temperatureToByte(temperature);  // 转换温度值为字节格式
  powerOnCommand[1] = tempByte;                       // 设置第一个命令的温度
  powerOnCommand2[1] = tempByte;                      // 设置第二个命令的温度

  // 计算校验和
  uint8_t checksum1 = calculateChecksum(powerOnCommand, 8);
  powerOnCommand[7] = checksum1 << 4;
  
  uint8_t checksum2 = calculateChecksum(powerOnCommand2, 8);
  powerOnCommand2[7] = checksum2 << 4;

  // 打印调试信息
  if (debugMode && Serial) {
    Serial.printf("Sending IR command - Power: %s, Temp: %d\n", 
                  isPowerOn ? "ON" : "OFF", temperature);
  }

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
                    
  if (debugMode && Serial) {
    Serial.println("IR command sent");
  }
}

// 处理按钮事件
void handleButton() {
  M5.update();  // 更新按钮状态
  
  // 检测按钮A是否按下
  if (M5.BtnA.isPressed()) {
    // 如果按钮A刚刚按下，记录时间
    if (btnAPressTime == 0) {
      btnAPressTime = millis();
    }
    
    // 检查是否长按
    if (!btnALongPressed && (millis() - btnAPressTime >= LONG_PRESS_TIME)) {
      btnALongPressed = true;
      // 长按操作：重启设备
      if (debugMode && Serial) {
        Serial.println("Long press detected, restarting device");
      }
      restartDevice();
    }
  } else {
    // 按钮A释放
    if (btnAPressTime > 0 && !btnALongPressed) {
      // 短按操作：切换电源状态
      isPowerOn = !isPowerOn;

      if (isPowerOn) {
        // 发送开机状态更新
        String payload = "{\"status\":\"on\",\"temp\":" + String(currentTemp) + "}";
        publishMessage(mqtt_pub_topic, payload.c_str());
        sendCommand(currentTemp);  // 开机时发送当前温度设置
      } else {
        // 发送关机状态更新
        String payload = "{\"status\":\"off\",\"temp\":" + String(currentTemp) + "}";
        publishMessage(mqtt_pub_topic, payload.c_str());
        sendCommand(currentTemp);  // 关机时发送当前温度设置
      }
      beepFeedback();           // 蜂鸣器提示音
      updateDisplay();          // 更新显示
    }
    
    // 重置按钮状态
    btnAPressTime = 0;
    btnALongPressed = false;
  }

  // 处理按钮B（温度调节）
  if (M5.BtnB.wasPressed()) {  // 如果按下按钮B
    if (isPowerOn) {           // 只在开机状态下调节温度
      // 增加等待发送的温度
      if (!tempChanged) {      // 如果是第一次按下
        tempToSend = currentTemp; // 初始化为当前温度
      }
      
      tempToSend++;           // 增加温度
      if (tempToSend > 30) tempToSend = 16;  // 温度循环
      
      tempChanged = true;     // 标记温度已改变
      tempSetTime = millis(); // 记录设置时间
      
      beepFeedback();        // 蜂鸣器提示音
      
      // 更新显示，显示即将设置的温度
      updateDisplay();
      
      if (debugMode && Serial) {
        Serial.printf("Temperature change queued: %d\n", tempToSend);
      }
    }
  }
  
  // 检查并发送温度命令
  checkAndSendTemp();
}

// 主循环
void loop() {
  M5.update();  // 更新M5StickC状态
  
  // 检查Wi-Fi连接超时
  if (WiFi.status() != WL_CONNECTED) {
    // 如果连接超时(1分钟)，重启设备
    if (millis() - wifiStartTime > WIFI_TIMEOUT) {
      M5.Lcd.fillScreen(BLACK);
      M5.Lcd.setCursor(0, 0);
      M5.Lcd.println("WiFi connection timeout");
      M5.Lcd.println("Restarting...");
      
      if (debugMode && Serial) {
        Serial.println("WiFi connection timeout, restarting device");
      }
      
      delay(2000);
      restartDevice();
    }
    
    // 尝试重新连接WiFi
    connectToStrongestWiFi();
  }
  
  // 检查MQTT连接
  if (!client.connected()) {
    if (debugMode && Serial) {
      Serial.println("MQTT disconnected, reconnecting");
    }
    connectMQTT();
  }
  client.loop();             // MQTT消息处理
  
  handleButton();            // 处理按钮事件
}