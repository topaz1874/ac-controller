# M5StickC Plus 格力空调控制器

这是一个使用M5StickC Plus开发的智能空调控制器，支持Wi-Fi连接和MQTT控制。

## 功能特点

- 支持空调开关机控制
- Wi-Fi连接显示（SSID和信号强度）
- MQTT远程控制
- 温度控制范围：16-30度
- 红外发送控制
- LCD状态显示
- 蜂鸣器操作反馈

## 硬件要求

- M5StickC Plus
- 红外LED（连接到GPIO9）
- Wi-Fi网络环境
- MQTT服务器（运行在192.168.1.59）

## 网络配置

- Wi-Fi SSID: office
- Wi-Fi 密码: gdzsam632
- MQTT服务器: 192.168.1.59
- MQTT端口: 1883
- MQTT主题: aircon

## MQTT命令

- 开机命令: "on"
- 关机命令: "off"
- 状态反馈: "已开机"/"已关机"

## 使用方法

1. 设备开机后自动连接Wi-Fi
2. LCD显示Wi-Fi连接状态和信号强度
3. 可通过按钮A或MQTT命令控制开关机
4. 每次状态改变都会通过MQTT发送反馈

## 引脚定义

- IR LED: GPIO9
- 内置按钮A：本地开关机控制
- 内置LCD：状态显示
- 内置蜂鸣器：操作反馈

## 依赖库

- M5StickCPlus
- IRremoteESP8266
- WiFi
- PubSubClient

## 安装步骤

1. 安装Arduino IDE
2. 安装所需库文件
3. 配置开发板为M5StickC Plus
4. 编译并上传代码

## 代码结构

- `stickc_ac_con.ino`：主程序文件
- 包含Wi-Fi连接、MQTT通信、红外控制等功能

## 调试信息

- 串口波特率：115200
- LCD显示：Wi-Fi SSID、信号强度、电源状态

## 注意事项

1. 确保Wi-Fi网络可用
2. MQTT服务器必须正常运行
3. 红外LED需正确连接
4. 保持与空调接收器的适当距离

## 许可证

MIT License