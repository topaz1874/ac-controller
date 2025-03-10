# 青萍传感器数据监控

这是一个基于Flask的Web应用，用于显示从MQTT主题"qingping/up"接收到的青萍传感器数据。应用会解析传感器数据并以友好的方式显示，同时也会显示原始数据以便调试。

## 功能特点

- 实时显示传感器数据（温度、湿度、气压等）
- 显示原始十六进制数据
- 保存历史数据记录
- 自动刷新数据
- 响应式设计，适配不同设备

## 安装与运行

### 方法一：使用虚拟环境（推荐）

1. 确保已安装Python 3.7或更高版本
2. 克隆或下载此仓库
3. 进入项目目录

```bash
cd app
```

4. 创建虚拟环境

```bash
python3 -m venv venv
```

5. 激活虚拟环境并安装依赖

```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

6. 运行应用

```bash
python app.py
```

### 方法二：使用提供的脚本（仅限macOS/Linux）

```bash
# 添加执行权限
chmod +x run.sh

# 直接运行
./run.sh
```

### 方法三：直接运行（不推荐）

```bash
pip install -r requirements.txt
python app.py
```

## 配置

在`app.py`文件中，您可以修改以下配置：

- `MQTT_BROKER`: MQTT服务器地址（默认为"localhost"）
- `MQTT_PORT`: MQTT服务器端口（默认为1883）
- `MQTT_TOPIC`: 订阅的主题（默认为"qingping/up"）
- `MAX_HISTORY_SIZE`: 保存的历史记录数量（默认为50）

### 端口配置

您可以通过以下方式自定义Web服务器端口：

1. 使用命令行参数
```bash
python app.py --port 8080
```

2. 使用环境变量
```bash
PORT=8080 python app.py
```

默认端口为5001。

## 使用说明

1. 打开浏览器访问 http://localhost:5001
2. 页面将自动显示最新接收到的传感器数据
3. 数据每5秒自动刷新一次
4. 点击"刷新数据"按钮可手动刷新数据
5. 历史数据表格显示最近接收到的数据记录

## 数据解析

应用基于`tlv_decode.go`文件中的协议解析传感器数据。主要支持以下数据：

- 温度（°C）
- 湿度（%）
- 气压（hPa）
- 电池电量（%）
- 探头温度（如果有）
- 探头湿度（如果有）
- 其他可能的传感器数据（CO₂、PM2.5、PM10、TVOC、噪音、光照、信号强度等）

## 调试

如果无法连接到MQTT服务器，应用会自动生成一些测试数据以便于开发和调试。

## 依赖项

- Flask: Web框架
- paho-mqtt: MQTT客户端
- Bootstrap: 前端UI框架
- Chart.js: 图表库

## 虚拟环境管理

### 激活虚拟环境

```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 退出虚拟环境

```bash
deactivate
```

## 许可证

MIT 