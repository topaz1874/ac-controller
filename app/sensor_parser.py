import struct
import binascii
from typing import Dict, List, Optional, Any, Tuple


class SensorData:
    def __init__(self):
        self.temperature: float = 0.0
        self.humidity: float = 0.0
        self.pressure: Optional[float] = None
        self.prob_temperature: Optional[float] = None
        self.prob_humidity: Optional[float] = None
        self.battery: int = 0
        self.co2: Optional[float] = None
        self.pm25: Optional[float] = None
        self.pm10: Optional[float] = None
        self.tvoc: Optional[float] = None
        self.noise: Optional[float] = None
        self.lumen: Optional[float] = None
        self.rssi: Optional[int] = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "prob_temperature": self.prob_temperature,
            "prob_humidity": self.prob_humidity,
            "battery": self.battery,
            "co2": self.co2,
            "pm25": self.pm25,
            "pm10": self.pm10,
            "tvoc": self.tvoc,
            "noise": self.noise,
            "lumen": self.lumen,
            "rssi": self.rssi
        }


class MessagePod:
    def __init__(self):
        self.product_id: str = ""
        self.device_id: str = ""
        self.mac: str = ""
        self.history: List[SensorData] = []
        self.realtime: Optional[SensorData] = None
        self.other: Dict[str, str] = {}


def parse_sensor_data(data: bytes) -> SensorData:
    """
    解析传感器数据（简化版本）
    """
    # 创建一个空的SensorData对象
    out = SensorData()
    # 注意：解析逻辑已被删除，现在只返回空对象
    print(f"传感器数据解析函数已简化，不再解析数据: {data.hex()}")
    
    return out


def parse_robb_sensor_data(data: bytes) -> SensorData:
    """
    解析Robb传感器数据（简化版本）
    """
    # 创建一个空的SensorData对象
    out = SensorData()
    # 注意：解析逻辑已被删除，现在只返回空对象
    print(f"Robb传感器数据解析函数已简化，不再解析数据: {data.hex()}")
    
    return out


def hex_to_bytes(hex_str: str) -> bytes:
    """
    将十六进制字符串转换为字节数组
    """
    return binascii.unhexlify(hex_str.replace(" ", ""))


def bytes_to_hex(data: bytes) -> str:
    """
    将字节数组转换为十六进制字符串
    """
    return binascii.hexlify(data).decode('utf-8')


def parse_keys(data: bytes) -> dict:
    """
    解析青萍传感器数据包中的键值对
    参考: https://github.com/niklasarnitz/qingping-co2-temp-rh-sensor-mqtt-parser/blob/master/src/utils/parseKeys.ts
    
    数据包格式:
    - 前5个字节是协议头和负载长度
    - 从第5个字节开始，每个数据项由三部分组成:
      - 键（1字节）
      - 长度（2字节，小端序）
      - 值（长度由前面指定）
    """
    # 检查数据包长度是否足够，至少需要5个字节
    if len(data) < 5:
        print("数据包太短，无法解析")
        return {}  # 返回空字典而不是None
    
    # 检查数据是否以434734开头
    if data[0] == 0x43 and data[1] == 0x47 and data[2] == 0x34:
        # 434734格式的数据
        print("检测到434734格式的数据")
    
    # 获取负载长度（第3和第4个字节，小端序）
    # 第3个字节是低位，第4个字节是高位，使用位运算组合
    payload_length = data[3] | (data[4] << 8)
    print(f"负载长度: {payload_length}")
    
    # 初始化结果字典，用于存储解析出的键值对
    result = {}
    
    # 从第5个字节开始解析
    # i是当前处理的字节位置
    i = 5
    # 循环直到处理完所有数据或达到负载长度
    # payload_length + 3是因为前3个字节是协议头
    while i < len(data) and i < payload_length + 3:
        try:
            # 获取键（1字节）
            key = data[i]
            # 检查是否有足够的字节来读取长度
            if i + 2 >= len(data):
                break
                
            # 获取值的长度（2字节，小端序）
            # 第一个字节是低位，第二个字节是高位
            length = data[i + 1] | (data[i + 2] << 8)
            
            # 检查是否有足够的字节来读取值
            if i + 3 + length > len(data):
                print(f"数据长度超出范围: 键={hex(key)}, 长度={length}, 当前位置={i}, 数据总长={len(data)}")
                break
                
            # 获取值（长度由前面指定）
            value = data[i + 3:i + 3 + length]
            
            # 使用十六进制格式的键作为字典的键
            # 格式为0x后跟两位十六进制数
            hex_key = f"0x{key:02x}"
            result[hex_key] = value
            
            # 打印调试信息
            print(f"解析到键值对: {hex_key} = {bytes_to_hex(value)} (长度: {length})")
            
            # 移动到下一个键值对
            # 当前位置 + 3(键和长度) + 值的长度
            i += 3 + length
        except Exception as e:
            # 捕获并打印解析过程中的任何错误
            print(f"解析键值对时出错: {e}")
            break
    
    # 返回解析结果
    return result


def parse_mqtt_payload(payload: bytes) -> Tuple[Dict[str, Any], str]:
    """
    解析MQTT消息负载
    返回解析后的数据和原始十六进制字符串
    """
    # 将二进制数据转换为十六进制字符串，方便调试和显示
    hex_str = bytes_to_hex(payload)
    print(f"收到MQTT消息: {hex_str}")
    
    # 检查数据是否以434734开头，只解析这种格式的数据
    if not (hex_str.startswith("434734") or hex_str.startswith("434731")):
        print(f"数据不是434734或434731开头，跳过解析: {hex_str}")
        return {"error": "数据格式不匹配，只解析434734或434731开头的数据", "_raw_hex": hex_str}, hex_str
    
    # 记录数据格式
    data_format = "434734" if hex_str.startswith("434734") else "434731"
    print(f"检测到{data_format}格式的数据")
    
    try:
        # 直接使用原始数据，不进行转义处理
        data = payload
        print(f"原始数据: {bytes_to_hex(data)}")
        
        # 解析数据包中的键值对结构
        keys_data = parse_keys(data)
        # 确保keys_data不是None
        if keys_data is None:
            keys_data = {}
        
        print(f"解析到 {len(keys_data)} 个键值对")
        
        # 创建结果字典
        result = {}
        
        # 添加原始数据到结果中，方便调试
        result["_raw_hex"] = hex_str
        # 添加解析出的键值对到结果中
        result["_keys"] = {k: bytes_to_hex(v) for k, v in keys_data.items()}
        
        # 如果是434731格式的数据，解析0x03键
        if data_format == "434731" and "0x03" in keys_data:
            # 获取0x03键的数据
            data_0x03 = keys_data["0x03"]
            print(f"解析键0x03: {bytes_to_hex(data_0x03)}")
            
            # 解析时间戳（前4个字节，小端序）
            if len(data_0x03) >= 4:
                timestamp = int.from_bytes(data_0x03[0:4], byteorder='little')
                print(f"时间戳: {timestamp}")
                result["_timestamp"] = timestamp
            
            # 解析数据存储间隔（第5-6字节，小端序）
            if len(data_0x03) >= 6:
                interval = int.from_bytes(data_0x03[4:6], byteorder='little')
                print(f"数据存储间隔: {interval}秒")
                result["_interval"] = interval
            
            # 解析传感器数据（第7-12字节）
            if len(data_0x03) >= 12:
                # 获取传感器数据
                sensor_bytes = data_0x03[6:12]
                print(f"键0x03中的传感器数据: {bytes_to_hex(sensor_bytes)}")
                
                # 如果有足够的字节，解析温湿度
                if len(sensor_bytes) >= 3:
                    # 使用小端序读取前3个字节组合成一个整数
                    combined_data = sensor_bytes[0] | (sensor_bytes[1] << 8) | (sensor_bytes[2] << 16)
                    
                    # 高12位是温度，低12位是湿度
                    temp_raw = combined_data >> 12
                    humi_raw = combined_data & 0xFFF
                    
                    # 温度公式: (raw_value - 500) / 10
                    temperature = (temp_raw - 500.0) / 10.0
                    # 湿度公式: raw_value / 10
                    humidity = humi_raw / 10.0
                    
                    # 更新结果中的温湿度值
                    result["temperature"] = temperature
                    result["humidity"] = humidity
                    
                    print(f"从键0x03解析: 温度={temperature}°C, 湿度={humidity}%")
                
                # 如果有足够的字节，解析气压
                if len(sensor_bytes) >= 5:
                    pressure_raw = sensor_bytes[3] | (sensor_bytes[4] << 8)
                    pressure = pressure_raw / 100.0
                    
                    # 更新结果中的气压值
                    result["pressure"] = pressure
                    
                    print(f"从键0x03解析: 气压={pressure} hPa")
                
                # 如果有足够的字节，解析电池电量
                if len(sensor_bytes) >= 6:
                    battery = sensor_bytes[5]
                    
                    # 更新结果中的电池电量
                    result["battery"] = battery
                    
                    print(f"从键0x03解析: 电池电量={battery}%")
                
                # 添加原始数据到结果中
                result["_0x03_sensor_data"] = bytes_to_hex(sensor_bytes)
                
                print(f"解析结果: 温度={result.get('temperature')}°C, 湿度={result.get('humidity')}%")
        
        # 如果是434734格式的数据，解析0x14键
        if data_format == "434734" and "0x14" in keys_data:
            # 获取0x14键的数据
            data_0x14 = keys_data["0x14"]
            print(f"解析键0x14: {bytes_to_hex(data_0x14)}")
            
            # 解析时间戳（前4个字节，小端序）
            if len(data_0x14) >= 4:
                timestamp = int.from_bytes(data_0x14[0:4], byteorder='little')
                print(f"时间戳: {timestamp}")
                result["_timestamp"] = timestamp
            
            # 解析传感器数据（时间戳后的数据）
            if len(data_0x14) >= 5:  # 至少有一个字节的传感器数据
                # 获取传感器数据
                sensor_bytes = data_0x14[4:]
                print(f"键0x14中的传感器数据: {bytes_to_hex(sensor_bytes)}")
                
                # 如果有足够的字节，解析温湿度
                if len(sensor_bytes) >= 3:
                    # 使用小端序读取前3个字节组合成一个整数
                    combined_data = sensor_bytes[0] | (sensor_bytes[1] << 8) | (sensor_bytes[2] << 16)
                    
                    # 高12位是温度，低12位是湿度
                    temp_raw = combined_data >> 12
                    humi_raw = combined_data & 0xFFF
                    
                    # 温度公式: (raw_value - 500) / 10
                    temperature = (temp_raw - 500.0) / 10.0
                    # 湿度公式: raw_value / 10
                    humidity = humi_raw / 10.0
                    
                    # 更新结果中的温湿度值
                    if "temperature" not in result or result["temperature"] == 0:
                        result["temperature"] = temperature
                    if "humidity" not in result or result["humidity"] == 0:
                        result["humidity"] = humidity
                    
                    print(f"从键0x14解析: 温度={temperature}°C, 湿度={humidity}%")
                
                print(f"解析结果: 温度={result.get('temperature')}°C, 湿度={result.get('humidity')}%")
                
                # 如果有足够的字节，解析气压
                if len(sensor_bytes) >= 5:
                    pressure_raw = sensor_bytes[3] | (sensor_bytes[4] << 8)
                    pressure = pressure_raw / 100.0
                    
                    # 更新结果中的气压值
                    result["pressure"] = pressure
                    
                    print(f"从键0x14解析: 气压={pressure} hPa")
                
                # 如果有足够的字节，解析电池电量
                if len(sensor_bytes) >= 6:
                    battery = sensor_bytes[5]
                    
                    # 更新结果中的电池电量
                    result["battery"] = battery
                    
                    print(f"从键0x14解析: 电池电量={battery}%")
                
                # 如果有足够的字节，解析信号强度
                if len(sensor_bytes) >= 7:
                    rssi = int.from_bytes([sensor_bytes[6]], byteorder='little', signed=True)
                    
                    # 更新结果中的信号强度
                    result["rssi"] = rssi
                    
                    print(f"从键0x14解析: 信号强度={rssi} dBm")
                
                # 添加原始数据到结果中
                result["_0x14_sensor_data"] = bytes_to_hex(sensor_bytes)
        
        # 返回解析结果和原始十六进制字符串
        return result, hex_str
        
    except Exception as e:
        # 如果解析过程中出现任何错误，捕获并返回错误信息
        import traceback
        # 生成详细的错误信息，包括堆栈跟踪
        error_msg = f"解析MQTT消息时出错: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        # 返回错误信息和原始十六进制字符串
        return {"error": error_msg, "_raw_hex": hex_str}, hex_str

