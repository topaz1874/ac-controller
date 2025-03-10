import json
import time
from datetime import datetime
from flask import Flask, render_template, jsonify
import paho.mqtt.client as mqtt
from sensor_parser import parse_mqtt_payload, hex_to_bytes
import os
import argparse
import random

app = Flask(__name__)

# 存储最近接收到的数据
sensor_data_history = []
MAX_HISTORY_SIZE = 50  # 最多保存50条历史记录

# MQTT配置
MQTT_BROKER = "192.168.1.59"  # MQTT服务器地址
MQTT_PORT = 1883  # MQTT服务器端口
MQTT_TOPIC = "qingping/up"  # 订阅的主题

# 添加命令行参数解析
parser = argparse.ArgumentParser(description='青萍传感器数据监控应用')
parser.add_argument('--port', type=int, default=os.environ.get('PORT', 5001), 
                    help='Web服务器端口号 (默认: 5001)')
args = parser.parse_args()

# MQTT回调函数
def on_connect(client, userdata, flags, rc):
    print(f"已连接到MQTT服务器，返回码: {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"已订阅主题: {MQTT_TOPIC}")

def on_message(client, userdata, msg):
    try:
        # 解析MQTT消息
        payload = msg.payload
        parsed_data, hex_data = parse_mqtt_payload(payload)
        
        # 添加时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 创建记录
        record = {
            "timestamp": timestamp,
            "topic": msg.topic,
            "hex_data": hex_data,
            "parsed_data": parsed_data
        }
        
        # 添加到历史记录
        global sensor_data_history
        sensor_data_history.insert(0, record)  # 新数据插入到列表开头
        
        # 限制历史记录大小
        if len(sensor_data_history) > MAX_HISTORY_SIZE:
            sensor_data_history = sensor_data_history[:MAX_HISTORY_SIZE]
            
        print(f"收到新数据: {json.dumps(record, ensure_ascii=False)}")
    except Exception as e:
        print(f"处理消息时出错: {e}")

# 初始化MQTT客户端
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

# Flask路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    return jsonify(sensor_data_history)

@app.route('/api/latest')
def get_latest():
    if sensor_data_history:
        return jsonify(sensor_data_history[0])
    return jsonify({})

# 测试数据生成函数（仅用于开发测试）
def generate_test_data():
    """
    生成测试数据，模拟青萍传感器的数据包格式
    参考: https://github.com/niklasarnitz/qingping-co2-temp-rh-sensor-mqtt-parser/blob/master/src/utils/parseKeys.ts
    
    数据包格式:
    - 前3个字节是协议头 (固定为 0x01, 0x10, 0x01)
    - 第4-5个字节是负载长度 (小端序)
    - 从第6个字节开始，每个数据项由三部分组成:
      - 键（1字节）
      - 长度（2字节，小端序）
      - 值（长度由前面指定）
    """
    # 随机选择一个测试场景
    scenario = random.choice([1, 2, 3])
    
    if scenario == 1:
        # 场景1: 温度25.5°C, 湿度45.0%
        temp_raw = 755  # (25.5 * 10) + 500
        humi_raw = 450  # 45.0 * 10
        
        # 组合值 (温度高12位，湿度低12位)
        combined_value = (temp_raw << 12) | (humi_raw & 0xFFF)
        
        # 小端序表示 (低字节在前)
        byte1 = combined_value & 0xFF
        byte2 = (combined_value >> 8) & 0xFF
        byte3 = (combined_value >> 16) & 0xFF
        
        # 温湿度数据 (键0x01)
        key_01_data = bytes([byte1, byte2, byte3])
        
        # 气压数据 (键0x02) - 1013.2 hPa
        pressure_raw = int(1013.2 * 100)  # 101320
        pressure_byte1 = pressure_raw & 0xFF
        pressure_byte2 = (pressure_raw >> 8) & 0xFF
        key_02_data = bytes([pressure_byte1, pressure_byte2])
        
        # 电池电量 (键0x0A) - 85%
        key_0A_data = bytes([85])
    elif scenario == 2:
        # 场景2: 温度21.0°C, 湿度55.0%
        temp_raw = 710  # (21.0 * 10) + 500
        humi_raw = 550  # 55.0 * 10
        
        # 组合值 (温度高12位，湿度低12位)
        combined_value = (temp_raw << 12) | (humi_raw & 0xFFF)
        
        # 小端序表示 (低字节在前)
        byte1 = combined_value & 0xFF
        byte2 = (combined_value >> 8) & 0xFF
        byte3 = (combined_value >> 16) & 0xFF
        
        # 温湿度数据 (键0x01)
        key_01_data = bytes([byte1, byte2, byte3])
        
        # 气压数据 (键0x02) - 1008.5 hPa
        pressure_raw = int(1008.5 * 100)  # 100850
        pressure_byte1 = pressure_raw & 0xFF
        pressure_byte2 = (pressure_raw >> 8) & 0xFF
        key_02_data = bytes([pressure_byte1, pressure_byte2])
        
        # 电池电量 (键0x0A) - 92%
        key_0A_data = bytes([92])
    else:
        # 场景3: 使用键0x14包含完整数据
        # 温度23.8°C, 湿度62.5%
        temp_raw = 738  # (23.8 * 10) + 500
        humi_raw = 625  # 62.5 * 10
        
        # 组合值 (温度高12位，湿度低12位)
        combined_value = (temp_raw << 12) | (humi_raw & 0xFFF)
        
        # 小端序表示 (低字节在前)
        byte1 = combined_value & 0xFF
        byte2 = (combined_value >> 8) & 0xFF
        byte3 = (combined_value >> 16) & 0xFF
        
        # 温湿度数据 (键0x01)
        key_01_data = bytes([byte1, byte2, byte3])
        
        # 气压数据 (键0x02) - 1010.3 hPa
        pressure_raw = int(1010.3 * 100)  # 101030
        pressure_byte1 = pressure_raw & 0xFF
        pressure_byte2 = (pressure_raw >> 8) & 0xFF
        key_02_data = bytes([pressure_byte1, pressure_byte2])
        
        # 电池电量 (键0x0A) - 78%
        key_0A_data = bytes([78])
        
        # 键0x14数据 (时间戳1字节 + 传感器6字节 + 信号强度1字节 + 保留1字节)
        # 时间戳
        timestamp_byte = bytes([random.randint(0, 255)])
        
        # 传感器数据 (前3字节温湿度，第4-5字节气压，第6字节电量)
        sensor_data = bytes([byte1, byte2, byte3, pressure_byte1, pressure_byte2, key_0A_data[0]])
        
        # 信号强度 (-75 dBm)
        rssi_byte = bytes([0xB5])  # -75 的补码表示
        
        # 保留字节
        reserved_byte = bytes([0x00])
        
        # 组合键0x14的数据
        key_14_data = timestamp_byte + sensor_data + rssi_byte + reserved_byte
    
    # 构建键值对部分
    keys_data = b''
    
    # 添加键0x01 (温湿度)
    keys_data += bytes([0x01])  # 键
    keys_data += bytes([len(key_01_data), 0])  # 长度 (小端序)
    keys_data += key_01_data  # 值
    
    # 添加键0x02 (气压)
    keys_data += bytes([0x02])  # 键
    keys_data += bytes([len(key_02_data), 0])  # 长度 (小端序)
    keys_data += key_02_data  # 值
    
    # 添加键0x0A (电池)
    keys_data += bytes([0x0A])  # 键
    keys_data += bytes([len(key_0A_data), 0])  # 长度 (小端序)
    keys_data += key_0A_data  # 值
    
    # 如果是场景3，添加键0x14
    if scenario == 3:
        keys_data += bytes([0x14])  # 键
        keys_data += bytes([len(key_14_data), 0])  # 长度 (小端序)
        keys_data += key_14_data  # 值
    
    # 计算负载长度 (键值对部分的长度 + 2)
    payload_length = len(keys_data) + 2
    
    # 构建完整的数据包
    packet = bytes([0x01, 0x10, 0x01])  # 协议头
    packet += bytes([payload_length & 0xFF, (payload_length >> 8) & 0xFF])  # 负载长度 (小端序)
    packet += keys_data  # 键值对部分
    packet += bytes([0x00, 0x00])  # 结尾
    
    print(f"生成测试数据: {packet.hex()}")
    return packet

if __name__ == '__main__':
    try:
        # 连接到MQTT服务器
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        # 在后台线程中启动MQTT循环
        mqtt_client.loop_start()
        print(f"已连接到MQTT服务器 {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"连接MQTT服务器失败: {e}")
        print("将使用测试数据模式...")
        
        # 定义测试数据生成函数
        def generate_test_data_record():
            """生成测试数据记录并添加到历史记录中"""
            try:
                # 生成测试数据包
                payload = generate_test_data()
                
                # 解析测试数据
                parsed_data, hex_data = parse_mqtt_payload(payload)
                
                # 添加时间戳
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 创建记录
                record = {
                    "timestamp": timestamp,
                    "topic": MQTT_TOPIC,
                    "hex_data": hex_data,
                    "parsed_data": parsed_data
                }
                
                # 添加到历史记录
                global sensor_data_history
                sensor_data_history.insert(0, record)
                if len(sensor_data_history) > MAX_HISTORY_SIZE:
                    sensor_data_history = sensor_data_history[:MAX_HISTORY_SIZE]
                    
                print(f"生成测试数据记录: 温度={parsed_data.get('temperature')}°C, 湿度={parsed_data.get('humidity')}%")
            except Exception as e:
                print(f"生成测试数据时出错: {e}")
                import traceback
                print(traceback.format_exc())
        
        # 定时生成测试数据
        def schedule_test_data_generation():
            """定时生成测试数据"""
            import threading
            generate_test_data_record()
            # 每30秒生成一次测试数据
            threading.Timer(30, schedule_test_data_generation).start()
        
        # 立即生成一些初始测试数据
        for _ in range(3):
            generate_test_data_record()
            time.sleep(1)
        
        # 启动定时生成测试数据
        schedule_test_data_generation()
    
    # 启动Flask应用，使用命令行参数或环境变量指定的端口
    print(f"启动Web服务器，端口: {args.port}")
    app.run(host='0.0.0.0', port=args.port, debug=True) 