# M5StickC-Plus 红外信号接收器

这是一个基于 M5StickC-Plus 的红外信号接收和解码器项目。可以用来识别各种遥控器的信号类型和编码，对开发红外控制项目很有帮助。

## 硬件要求

- M5StickC-Plus
- 红外接收模块（如 VS1838B, TSOP38238 等）
- 连接线

## 硬件连接

红外接收模块与 M5StickC-Plus 的连接方式：
- 信号引脚 (OUT) -> G26
- 电源引脚 (VCC) -> 3.3V
- 地线 (GND) -> GND

## 依赖库

- M5StickCPlus
- IRremoteESP8266

## 功能特点

- 实时接收和解码红外信号
- 显示信号详细信息：
  - 时间戳
  - 协议类型
  - 接收到的代码（十六进制）
  - 数据位数
  - 原始数据长度（仅限未知协议）
- 支持多种红外协议
- 大容量缓冲区，可接收空调等复杂信号
- 按键清屏功能

## 安装说明

1. 安装 Arduino IDE
2. 安装必要的库：
   - 在 Arduino IDE 中打开库管理器（工具 > 管理库）
   - 搜索并安装 "M5StickC-Plus"
   - 搜索并安装 "IRremoteESP8266"
3. 选择正确的开发板：
   - 开发板："M5Stick-C"
   - 上传速度：115200

## 使用方法

1. 上电后，屏幕显示 "IR Receiver Ready"
2. 将遥控器对准红外接收模块
3. 按下遥控器按键，屏幕将显示接收到的信号信息
4. 按下 M5StickC-Plus 的按钮 A 可以清除显示内容

## 显示信息说明

- Time: 接收到信号的时间戳
- Protocol: 识别出的红外协议类型
- Code: 接收到的编码（十六进制格式）
- Bits: 接收到的数据位数
- Raw Length: 原始数据长度（仅对未知协议显示）

## 常见问题解决

1. 无法接收信号：
   - 检查接线是否正确
   - 确认遥控器电池电量
   - 调整遥控器与接收器的距离和角度

2. 信号识别不准确：
   - 保持环境光线适中，避免强光干扰
   - 确保接收器与遥控器之间没有遮挡
   - 尝试多次按键以获得稳定结果

## 开发建议

1. 记录下需要的遥控器信号数据
2. 注意区分不同按键的编码
3. 对于空调等复杂设备，建议保存完整的原始数据

## 技术参数

- 接收引脚：G26
- 缓冲区大小：1024 字节
- 超时时间：50ms
- 最小未知信号长度：12

## 未来计划

- [ ] 添加信号数据保存功能
- [ ] 支持更多红外协议
- [ ] 添加信号波形显示
- [ ] 添加 WiFi 数据传输功能

## 参考资料

- [M5StickC-Plus 文档](https://docs.m5stack.com/en/core/m5stickc_plus)
- [IRremoteESP8266 库文档](https://github.com/crankyoldgit/IRremoteESP8266)
- [红外通信协议说明](https://github.com/crankyoldgit/IRremoteESP8266/wiki)

## 版本控制

本项目使用Git进行版本管理，以下是基本的版本控制操作：

### 初始化仓库

```bash
# 初始化Git仓库
git init

# 添加所有文件到暂存区
git add .

# 提交初始版本
git commit -m "初始化项目：红外信号接收解码器"
```

### 常用Git命令

```bash
# 查看仓库状态
git status

# 查看提交历史
git log --oneline --graph

# 创建并切换到新分支
git checkout -b feature/new-feature

# 合并分支
git checkout main
git merge feature/new-feature

# 推送到远程仓库
git remote add origin https://github.com/yourusername/ir-receiver.git
git push -u origin main
```

### 提交规范

为保持代码库的整洁和可读性，提交信息应遵循以下格式：

- `feat:` 新功能
- `fix:` 修复问题
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建过程或辅助工具变动

## ESP32 LVGL空调控制界面

本项目还包含一个基于ESP32和LVGL库开发的空调控制界面，位于`esp32_lvgl`目录下。

### 功能特点

- 美观的图形用户界面
- 电源开关控制
- 温度调节滑块
- 温度设置按钮
- WiFi连接状态显示
- MQTT通信功能
- 动画效果（淡入淡出、折叠展开）

### 硬件要求

- ESP32开发板
- ILI9488 LCD显示屏
- FT6X36触摸控制器

### 软件依赖

- MicroPython固件
- LVGL库
- umqtt.simple库

### 使用方法

1. 将MicroPython固件烧录到ESP32
2. 上传`main.py`和所需库文件
3. 配置WiFi和MQTT连接参数
4. 重启ESP32即可运行界面

### 界面操作说明

- 点击电源开关按钮开启/关闭空调
- 开机状态下可以滑动温度滑块调节温度
- 点击SET按钮发送温度设置命令
- 界面底部会显示操作状态信息

## 许可证

MIT License

## 作者

[您的名字]

# 格力空调红外信号解码器

## 项目简介

这是一个专门用于解码格力空调红外信号的 Python 工具，支持详细的信号解析和协议识别。

## 功能特点

- 精确的 LSB（最低有效位）解码
- 自动识别并跳过连接码
- 块分隔符（B010）自动处理
- 详细的红外信号解析
- 支持多种空调控制参数解析