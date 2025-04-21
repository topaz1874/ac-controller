# ESP32 空调控制器

基于 ESP32 和 M5StickC Plus 的智能空调控制系统，支持 MQTT 远程控制和本地触摸屏操作。

## 功能特点

- 📱 3.5寸触摸屏界面
- 🌡️ 温度控制 (16-30°C)
- 💡 电源开关控制
- 📡 MQTT 远程控制
- 📶 智能Wi-Fi选择（自动连接信号最强的网络）
- 🔄 自动重连和重启机制
- 🎯 红外发射精确控制
- 📊 温度延迟发送功能
- 🔍 调试模式支持
- 🔋 长按重启功能

## 硬件要求

- ESP32 开发板（带触摸屏）
- M5StickC Plus
- 红外发射模块
- 红外接收模块（用于学习遥控器编码）

## 软件依赖

- Arduino IDE 1.8.13+
- ESP32 Arduino 核心库
- M5StickC Plus 库
- IRremoteESP8266 库
- PubSubClient MQTT 客户端库
- WiFi 库

## 目录结构

```
.
├── esp32_lvgl/              # ESP32 触摸屏控制端
│   ├── main.py             # 主程序
│   ├── ili9XXX.py         # 显示屏驱动
│   └── ft6x36.py          # 触摸屏驱动
├── stickc_ac_con/          # M5StickC Plus 红外发射端
│   ├── stickc_ac_con.ino  # Arduino 主程序
│   └── README.md          # 项目说明
└── ir_receiver/            # 红外信号接收器
    └── README.md          # 接收器说明
```

## 新增功能说明

### 智能Wi-Fi选择
- 开机自动扫描可用网络
- 检测 "office" 和 "office_2.4" 的信号强度
- 自动连接信号最强的网络
- 如果连接失败，会尝试连接另一个网络

### 温度延迟发送
- 按下按钮B增加温度设置
- 屏幕实时显示将要设置的温度
- 按键操作后等待1秒
- 若1秒内无新操作，发送设置命令
- 避免频繁发送指令，提高用户体验

### 调试模式
- 默认开启，可在代码中修改
- 连接串口后，所有操作会输出到串口
- 包括MQTT消息、红外指令、错误信息等
- 波特率为115200
- 便于问题排查和开发调试

### 长按重启
- 长按按钮A 2秒以上会重启设备
- 短按按钮A 正常切换电源开关
- Wi-Fi连接超时1分钟后自动重启
- 提供简单的恢复方式，无需重新烧录

## 使用说明

1. 开机后自动连接信号最强的WiFi网络
2. 等待连接成功，控件自动启用
3. 按键操作：
   - 短按按钮A：切换空调开关
   - 长按按钮A (2秒以上)：重启设备
   - 按钮B：增加温度，1秒后发送命令
4. 温度控制：
   - 按下按钮B增加温度(16-30°C循环)
   - 屏幕实时显示"Set to: XX°C"
   - 1秒后发送到空调
5. MQTT状态反馈：
   - 每次操作后都会发送当前状态
   - 上电后自动发送上线消息
   - 调试模式下串口会显示所有消息

## API 指令集使用说明

### MQTT 主题
- 控制指令发送到: `stickc/aircon`
- 状态反馈接收自: `stickc/up`

### 控制指令
| 指令 | 说明 | 示例 |
|------|------|------|
| `api/power/on` | 开机 | `mosquitto_pub -t stickc/aircon -m "api/power/on"` |
| `api/power/off` | 关机 | `mosquitto_pub -t stickc/aircon -m "api/power/off"` |
| `api/temp/XX` | 设置温度(16-30) | `mosquitto_pub -t stickc/aircon -m "api/temp/25"` |
| `api/status` | 查询当前状态 | `mosquitto_pub -t stickc/aircon -m "api/status"` |

### 状态反馈
设备会通过 `stickc/up` 主题发送 JSON 格式的状态信息：

1. 设备上线消息:
```json
{"device":"stickc","status":"online"}
```

2. 状态更新消息:
```json
{"status":"on","temp":25}
```
或
```json
{"status":"off","temp":25}
```

### 调试模式使用
1. 确保 `debugMode` 变量设置为 `true`
2. 通过 USB 连接到电脑
3. 打开串口监视器，设置波特率为 115200
4. 所有操作都会输出到串口监视器

## 故障排除

1. 设备无响应
   - 长按按钮A 2秒以上重启设备
   - 检查电源连接

2. WiFi 连接问题
   - 检查 SSID 和密码是否正确
   - 确认两个Wi-Fi网络至少有一个可用
   - 若超过1分钟未连接，设备会自动重启

3. MQTT 连接问题
   - 验证服务器地址和端口
   - 检查网络连接
   - 查看串口调试信息

4. 温度控制问题
   - 确认红外发射器位置正确
   - 检查空调接收器是否有遮挡
   - 通过串口查看发送的命令细节

## 许可证

MIT License

## 联系方式

- GitHub：https://github.com/topaz1874/ac-controller

### 分支说明

- `main`: 稳定发布版本
- `develop`: 日常开发分支
- `feature/*`: 新功能开发
- `hotfix/*`: 紧急问题修复

### 开发工作流

1. 克隆仓库

## 安装说明

1. ESP32 触摸屏控制端
- 使用 esptool 和 adafruit-ampy 工具刷入 MicroPython
- 上传 esp32_lvgl/main.py, esp32_lvgl/ili9XXX.py, esp32_lvgl/ft6x36.py 到 ESP32

2. M5StickC Plus 红外发射端
- 使用 Arduino IDE 打开 `stickc_ac_con.ino`
- 选择开发板为 "M5Stick-C"
- 编译并上传

## 配置说明

1. WiFi 设置（esp32_lvgl/main.py）

## API 指令集使用说明

### MQTT 主题
- 控制指令发送到: `stickc/aircon`
- 状态反馈接收自: `stickc/up`

### 控制指令
| 指令 | 说明 | 示例 |
|------|------|------|
| `api/power/on` | 开机 | `mosquitto_pub -t stickc/aircon -m "api/power/on"` |
| `api/power/off` | 关机 | `mosquitto_pub -t stickc/aircon -m "api/power/off"` |
| `api/temp/XX` | 设置温度(16-30) | `mosquitto_pub -t stickc/aircon -m "api/temp/25"` |
| `api/status` | 查询当前状态 | `mosquitto_pub -t stickc/aircon -m "api/status"` |

### 状态反馈
设备会通过 `stickc/up` 主题发送 JSON 格式的状态信息：

1. 设备上线消息:
```json
{"device":"stickc","status":"online"}
```

2. 状态更新消息:
```json
{"status":"on","temp":25}
```
或
```json
{"status":"off","temp":25}
```

### 网页集成示例
```javascript
// 连接MQTT服务器
const client = mqtt.connect('ws://your-mqtt-broker:9001');

// 订阅状态反馈主题
client.subscribe('stickc/up');

// 监听状态更新
client.on('message', (topic, message) => {
  if (topic === 'stickc/up') {
    const status = JSON.parse(message.toString());
    updateUI(status);
  }
});

// 发送控制命令
function powerOn() {
  client.publish('stickc/aircon', 'api/power/on');
}

function powerOff() {
  client.publish('stickc/aircon', 'api/power/off');
}

function setTemperature(temp) {
  client.publish('stickc/aircon', `api/temp/${temp}`);
}

function queryStatus() {
  client.publish('stickc/aircon', 'api/status');
}
```
```

主要改进：

1. 使用常量定义 API 指令，便于维护和修改
2. 为每个 API 指令添加详细注释
3. 添加了 README 部分，详细说明 API 使用方法
4. 提供了 MQTT 命令行示例
5. 提供了网页集成示例代码
6. 详细说明了 JSON 格式的状态反馈

这样的文档和代码注释使得 API 更易于理解和使用，特别是对于网页开发者来说。
