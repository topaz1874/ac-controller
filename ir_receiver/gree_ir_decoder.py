import sys
import re

class GreeIRDecoder:
    def __init__(self):
        # 时序阈值（微秒单位）
        self.MARK_THRESHOLDS = {
            'start_mark': (8900, 9100),     # 起始高电平，放宽范围
            'start_space': (4300, 4600),    # 起始低电平，放宽范围
            'short_mark': (480, 700),       # 短高电平
            'short_space': (480, 700),      # 短低电平
            'long_space': (1500, 1800)      # 长低电平
        }
        
        # 协议字段定义
        self.MODE_MAP = {
            0: '自动',
            1: '制冷',
            2: '除湿',
            3: '送风',
            4: '制热'
        }
        
        self.FAN_MAP = {
            0: '自动',
            1: '低速',
            2: '中速',
            3: '高速'
        }

    def _is_in_range(self, value, threshold_range):
        """检查值是否在指定范围内"""
        return threshold_range[0] <= abs(value) <= threshold_range[1]

    def decode_raw_data(self, raw_data):
        """解码原始数据，使用LSB解码，忽略B010分隔符"""
        # 验证数据长度
        if len(raw_data) < 4:
            raise ValueError("数据长度不足")
        
        # 验证起始码
        start_mark = raw_data[0]
        start_space = raw_data[1]
        
        print("原始数据长度:", len(raw_data))
        print(f"起始高电平: {start_mark}")
        print(f"起始低电平: {start_space}")
        
        if not (self._is_in_range(start_mark, self.MARK_THRESHOLDS['start_mark']) and 
                self._is_in_range(start_space, self.MARK_THRESHOLDS['start_space'])):
            raise ValueError("无效的起始码")
        
        # 解码数据位
        binary_result = ""
        bit_count = 0
        
        i = 2
        while i < len(raw_data) - 1:
            mark = raw_data[i]
            space = raw_data[i+1]
            
            # 跳过连接码（480-700 us, 19000-21000 us）
            if (480 <= mark <= 700 and 19000 <= space <= 21000):
                i += 2
                continue
            
            # 检查是否到达32位并检查B010分隔符
            if bit_count == 32:
                # 检查接下来的3位是否为B010
                next_three_bits = ""
                next_i = i
                for _ in range(3):
                    if next_i + 1 >= len(raw_data):
                        break
                    next_mark = raw_data[next_i]
                    next_space = raw_data[next_i + 1]
                    
                    if 480 <= next_mark <= 700:
                        if 1500 <= next_space <= 1800:
                            next_three_bits += "1"
                        elif 480 <= next_space <= 700:
                            next_three_bits += "0"
                    next_i += 2
                
                if next_three_bits == "010":
                    print("\n检测到块分隔符B010，跳过3位")
                    i = next_i  # 跳过B010
                    bit_count = 0  # 重置位计数
                    continue
            
            # 解码位（LSB优先）
            if 480 <= mark <= 700:
                if 1500 <= space <= 1800:
                    # 长空白为1
                    binary_result += "1"
                    print(f"位 {bit_count}: mark={mark}, space={space} -> 1")
                elif 480 <= space <= 700:
                    # 短空白为0
                    binary_result += "0"
                    print(f"位 {bit_count}: mark={mark}, space={space} -> 0")
                else:
                    print(f"未知的数据位模式: mark={mark}, space={space}")
                
                bit_count += 1
            
            i += 2
        
        # 打印完整的二进制序列
        print("\n完整二进制序列:")
        print(binary_result)
        
        return binary_result

    def parse_protocol(self, binary_str):
        """解析格力协议字段"""
        # 确保输入是字符串
        if not isinstance(binary_str, str):
            binary_str = str(binary_str)
        
        # 移除可能的空白字符
        binary_str = binary_str.replace(' ', '')
        
        if len(binary_str) < 64:  # 至少需要8字节
            raise ValueError(f"协议数据长度不足，当前长度: {len(binary_str)}")
        
        # 按字节解析（LSB）
        bytes_data = []
        for i in range(0, min(len(binary_str), 64), 8):
            byte = binary_str[i:i+8][::-1]  # LSB反转
            bytes_data.append(int(byte, 2))
        
        result = {}
        
        # Byte 0
        result['模式'] = self.MODE_MAP.get(bytes_data[0] & 0x07, '未知')
        result['电源'] = '开' if (bytes_data[0] >> 3) & 0x01 else '关'
        result['风速'] = self.FAN_MAP.get((bytes_data[0] >> 4) & 0x03, '未知')
        result['自动摆风'] = '开' if (bytes_data[0] >> 6) & 0x01 else '关'
        result['睡眠模式'] = '开' if (bytes_data[0] >> 7) & 0x01 else '关'
        
        # Byte 1
        temp_raw = bytes_data[1] & 0x0F
        result['温度'] = f"{16 + temp_raw}°C"
        
        # Byte 2
        result['强力模式'] = '开' if (bytes_data[2] >> 4) & 0x01 else '关'
        result['灯光'] = '开' if (bytes_data[2] >> 5) & 0x01 else '关'
        
        # Byte 4
        result['垂直摆风'] = (bytes_data[4] & 0x0F)
        result['水平摆风'] = (bytes_data[4] >> 4) & 0x07
        
        # Byte 5
        result['体感'] = '开' if (bytes_data[5] >> 2) & 0x01 else '关'
        result['WiFi'] = '开' if (bytes_data[5] >> 6) & 0x01 else '关'
        
        # Byte 7
        if len(bytes_data) > 7:
            result['节能'] = '开' if (bytes_data[7] >> 2) & 0x01 else '关'
        
        return result

    def format_binary_output(self, binary_str):
        """格式化二进制输出，每8位换行，并在同一行显示对应的16进制值"""
        # 确保输入是字符串
        if not isinstance(binary_str, str):
            binary_str = str(binary_str)
        
        # 移除可能的空白字符
        binary_str = binary_str.replace(' ', '')
        
        # 补齐到8的倍数
        padded_binary = binary_str.ljust((len(binary_str) + 7) // 8 * 8, '0')
        
        print("\n数据解析 (每行: 二进制[LSB] -> 十六进制):")
        print("-" * 50)
        print("Binary(LSB)      Hex")
        print("-" * 50)
        
        # 分组并转换
        for i in range(0, len(padded_binary), 8):
            group = padded_binary[i:i+8]
            # LSB解码：反转每8位
            group_lsb = group[::-1]
            
            # 转换16进制
            hex_value = int(group_lsb, 2)
            
            # 打印格式化的行
            print(f"{group_lsb}  ->  0x{hex_value:02X}")
        
        print("-" * 50)

def input_raw_data():
    """交互式输入原始红外数据"""
    while True:
        try:
            raw_input = input("请输入原始红外信号数据（逗号分隔）:\n")
            raw_parts = [part.strip() for part in raw_input.replace(' ', ',').split(',') if part.strip()]
            raw_data = [int(part) for part in raw_parts]
            return raw_data
        except ValueError:
            print("输入无效！请使用正确的整数格式")
        except Exception as e:
            print(f"发生错误：{e}")

def main():
    decoder = GreeIRDecoder()
    
    while True:
        try:
            # 获取用户输入
            raw_data = input_raw_data()
            
            # 解码原始数据
            binary_result = decoder.decode_raw_data(raw_data)
            
            # 格式化输出
            decoder.format_binary_output(binary_result)
            
            # 解析协议
            try:
                protocol_info = decoder.parse_protocol(binary_result)
                print("\n协议解析:")
                for key, value in protocol_info.items():
                    print(f"{key}: {value}")
            except ValueError as e:
                print(f"\n协议解析错误: {e}")
            
            # 询问是否继续
            choice = input("\n是否继续解析？(y/n): ").lower()
            if choice != 'y':
                break
        
        except Exception as e:
            print(f"解析错误: {e}")

    print("程序已退出。")

if __name__ == "__main__":
    main()
