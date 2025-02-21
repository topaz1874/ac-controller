# ESP32 空调控制器

基于 ESP32 和 M5StickC Plus 的智能空调控制系统，支持 MQTT 远程控制和本地触摸屏操作。

## 功能特点

- 📱 3.5寸触摸屏界面
- 🌡️ 温度控制 (16-30°C)
- 💡 电源开关控制
- 📡 MQTT 远程控制
- 📶 WiFi 连接状态显示
- 🔄 自动重连机制
- 🎯 红外发射精确控制
- 🚦 LED状态指示

## 硬件要求

- ESP32 开发板（带触摸屏）
- M5StickC Plus
- 红外发射模块
- 红外接收模块（用于学习遥控器编码）

## 软件依赖

- MicroPython 1.19.1+
- **LVGL 9.0**
- MQTT 客户端库
- ili9488 显示驱动
- ft6x36 触摸驱动

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

## 版本控制

### Git 仓库结构

- `main`: 稳定发布版本
- `develop`: 日常开发分支
- `feature/*`: 新功能开发分支
  - feature/touch-control: 触摸屏控制功能
  - feature/ir-control: 红外控制功能
  - feature/mqtt: MQTT通信功能
- `hotfix/*`: 紧急问题修复分支

### 开发工作流

1. 克隆仓库
```bash
git clone https://github.com/topaz1874/ac-controller.git
cd ac-controller
```

2. 创建功能分支
```bash
git checkout -b feature/new-feature develop
```

3. 提交更改
```bash
git add .
git commit -m "feat: add new feature"
```

4. 合并到开发分支
```bash
git checkout develop
git merge --no-ff feature/new-feature
```

5. 发布版本
```bash
git checkout main
git merge --no-ff develop
git tag -a v1.0.0 -m "version 1.0.0"
```

## 使用说明

1. 开机后自动连接 WiFi 和 MQTT 服务器
2. 等待连接成功，控件自动启用
3. 使用触摸屏进行控制：
   - 左上角开关按钮控制电源
   - 滑块调节温度
   - SET 按钮确认设置
4. 观察LED指示：
   - 开机/温度调节：呼吸渐变效果
   - 关机：快速双闪


## 故障排除

1. WiFi 连接问题
   - 检查 SSID 和密码
   - 确认 WiFi 信号强度
   - 查看状态栏连接提示

2. MQTT 连接问题
   - 验证服务器地址
   - 检查网络连接
   - 观察状态提示信息

3. 红外控制问题
   - 确认发射器位置
   - 检查空调接收角度
   - 验证红外编码正确性

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
