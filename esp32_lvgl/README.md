# ESP32 Air Conditioner Controller

基于 ESP32 和 LVGL 的空调控制器，支持 MQTT 远程控制。

## 功能特点

- 状态栏显示
  - WiFi 连接状态
  - MQTT 连接状态
  - 信号强度指示
- 控制面板
  - 电源开关控制
  - 温度调节（16-30℃）
  - 设置确认按钮
- 操作状态反馈（10秒）
- 自动重连机制

## 硬件要求

- ESP32-S3
- 显示屏：ILI9488 (480x320)
- 触摸屏：FT6X36

## 软件环境

- MicroPython v1.19.1
- LVGL 9.0
- umqtt.simple

## 文件结构

```
esp32_lvgl/
├── main.py          # 主程序
├── ili9XXX.py       # 显示屏驱动
└── ft6x36.py        # 触摸屏驱动
```

## 安装步骤

1. 烧录 MicroPython
```bash
esptool.py --chip esp32s3 --port /dev/ttyACM0 erase_flash
esptool.py --chip esp32s3 --port /dev/ttyACM0 write_flash -z 0x0 esp32s3-20230426-v1.20.0.bin
```

2. 安装 MQTT 库
```bash
mpremote mip install umqtt.simple
```

3. 上传代码文件
```bash
mpremote cp main.py :main.py
mpremote cp ili9XXX.py :ili9XXX.py
mpremote cp ft6x36.py :ft6x36.py
```

## 配置说明

在 main.py 中配置网络参数：
```python
WIFI_SSID = "your_wifi_ssid"
WIFI_PASSWORD = "your_wifi_password"
MQTT_SERVER = "your_mqtt_server_ip"
MQTT_TOPIC = b"aircon"
```

## MQTT 协议

### 发布消息格式
- 开机：`on`
- 关机：`off`
- 设置温度：`set {temperature}`
  - 例如：`set 25`

### 订阅消息格式
- 开机：`on`
- 关机：`off`
- 设备上线：`device online`

## 使用说明

1. 开机自动连接 WiFi 和 MQTT 服务器
2. 状态栏显示连接状态和信号强度
3. 使用开关按钮控制电源
4. 使用滑块选择温度（16-30℃）
5. 点击 Set 按钮发送温度设置
6. 操作状态显示10秒后自动消失

## 故障排除

1. 显示问题
   - 检查显示屏和触摸屏连接
   - 确认 GPIO 引脚配置正确

2. 网络连接
   - 确认 WiFi 配置正确
   - 检查 MQTT 服务器地址

3. MQTT 通信
   - 检查 MQTT 服务器状态
   - 确认主题配置正确

## 开发计划

- [ ] 添加温度曲线显示
- [ ] 支持多设备控制
- [ ] 添加场景模式
- [ ] OTA 更新支持

## 许可证

MIT License 