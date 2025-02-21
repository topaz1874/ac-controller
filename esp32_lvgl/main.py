import lvgl as lv
import time
from espidf import VSPI_HOST
from ili9XXX import ili9488
from ft6x36 import ft6x36 
from machine import Pin, I2C
import network
from umqtt.simple import MQTTClient

# ------------------------------ 全局变量 ------------------------------
current_temp = 25                 # 当前温度
is_power_on = False              # 电源状态
wifi_connected = False           # Wi-Fi连接状态

# ------------------------------ Wi-Fi和MQTT设置 ------------------------------
WIFI_SSID = "office"             # Wi-Fi名称
WIFI_PASSWORD = "gdzsam632"      # Wi-Fi密码
MQTT_SERVER = "192.168.1.59"     # MQTT服务器地址
MQTT_TOPIC = b"aircon"           # MQTT主题
mqtt_client = None               # MQTT客户端实例

# ------------------------------ 状态栏类 ------------------------------
class StatusBar:
    def __init__(self, parent):
        # 创建状态栏容器
        self.container = lv.obj(parent)
        self.container.set_size(480, 30)
        self.container.set_pos(0, 0)
        self.container.set_style_bg_color(lv.color_hex(0x000000), 0)  # 黑色背景
        self.container.set_style_pad_all(0, 0)                        # 无内边距
        self.container.set_style_radius(0, 0)                         # 无圆角
        self.container.set_style_border_width(0, 0)                   # 无边框
        
        # 创建Wi-Fi图标和SSID (左侧)
        self.wifi_label = lv.label(self.container)
        self.wifi_label.set_text(f"WiFi: {WIFI_SSID}")
        self.wifi_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)  # 白色文字
        self.wifi_label.align(lv.ALIGN.LEFT_MID, 5, 0)
        
        # 创建信号强度标签 (右侧)
        self.signal_label = lv.label(self.container)
        self.signal_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)  # 白色文字
        self.signal_label.align(lv.ALIGN.RIGHT_MID, -5, 0)
        
        # 创建状态信息标签 (中间)
        self.status_label = lv.label(self.container)
        self.status_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)  # 白色文字
        self.status_label.align(lv.ALIGN.CENTER, 0, 0)
        self.status_label.set_text("Initializing...")
    
    def update_signal(self, rssi):
        # 更新信号强度显示
        if rssi >= -50:
            signal_text = "Signal: Strong"
        elif rssi >= -65:
            signal_text = "Signal: Medium"
        else:
            signal_text = "Signal: Weak"
        self.signal_label.set_text(signal_text)
    
    def set_status(self, text):
        # 直接设置状态文本
        self.status_label.set_text(text)

# ------------------------------ 控制面板类 ------------------------------
class ControlPanel:
    def __init__(self, parent, mqtt_client):
        # 创建主容器，使用网格布局
        self.cont = lv.obj(parent)
        self.cont.set_size(440, 280)
        self.cont.center()
        self.cont.set_style_pad_all(10, 0)  # 设置内边距
        self.cont.set_grid_dsc_array(lv.GRID_TEMPLATE.CONTENT, lv.GRID_TEMPLATE.CONTENT)
        
        # 保存MQTT客户端引用
        self.mqtt_client = mqtt_client
        
        # 创建电源控制区域
        power_cont = lv.obj(self.cont)
        power_cont.set_size(400, 60)
        power_cont.set_style_pad_all(5, 0)
        
        # 创建开关按钮，使用新的switch组件
        self.power_btn = lv.switch(power_cont)
        self.power_btn.set_size(60, 30)
        self.power_btn.add_event_cb(self.on_power_clicked, lv.EVENT.VALUE_CHANGED, None)
        
        # 创建电源标签，使用新的样式
        self.power_label = lv.label(power_cont)
        self.power_label.set_text("Power")
        self.power_label.set_style_text_font(lv.font_montserrat_16, 0)  # 设置字体
        self.power_label.align_to(self.power_btn, lv.ALIGN.OUT_RIGHT_MID, 10, 0)
        
        # 创建状态显示标签，添加背景样式
        self.status_label = lv.label(power_cont)
        self.status_label.set_text("")
        self.status_label.set_style_bg_opa(lv.OPA._20, 0)  # 半透明背景
        self.status_label.set_style_bg_color(lv.palette_main(lv.PALETTE.BLUE), 0)
        self.status_label.set_style_radius(5, 0)  # 圆角
        self.status_label.set_style_pad_all(5, 0)  # 内边距
        self.status_label.align_to(self.power_label, lv.ALIGN.OUT_RIGHT_MID, 10, 0)
        
        # 创建温度控制区域
        temp_cont = lv.obj(self.cont)
        temp_cont.set_size(400, 100)
        temp_cont.set_style_pad_all(5, 0)
        temp_cont.align_to(power_cont, lv.ALIGN.OUT_BOTTOM_MID, 0, 20)
        
        # 创建温度滑块，使用新的样式
        self.temp_slider = lv.slider(temp_cont)
        self.temp_slider.set_size(280, 20)
        self.temp_slider.set_range(16, 30)
        self.temp_slider.set_value(current_temp, lv.ANIM.OFF)
        self.temp_slider.add_event_cb(self.on_temp_changed, lv.EVENT.VALUE_CHANGED, None)
        # 添加滑块样式
        self.temp_slider.set_style_bg_color(lv.palette_main(lv.PALETTE.GREY), lv.PART.MAIN)
        self.temp_slider.set_style_bg_color(lv.palette_main(lv.PALETTE.BLUE), lv.PART.INDICATOR)
        self.temp_slider.set_style_bg_color(lv.palette_main(lv.PALETTE.BLUE), lv.PART.KNOB)
        
        # 创建温度显示标签，使用新的样式
        self.temp_label = lv.label(temp_cont)
        self.temp_label.set_text(f"{current_temp}°C")
        self.temp_label.set_style_text_font(lv.font_montserrat_20, 0)
        self.temp_label.align_to(self.temp_slider, lv.ALIGN.OUT_BOTTOM_MID, 0, 10)
        
        # 创建设置温度按钮，使用新的按钮样式
        self.set_temp_btn = lv.btn(temp_cont)
        self.set_temp_btn.set_size(80, 40)
        self.set_temp_btn.align_to(self.temp_slider, lv.ALIGN.OUT_RIGHT_MID, 20, 0)
        self.set_temp_btn.add_event_cb(self.on_set_temp_clicked, lv.EVENT.CLICKED, None)
        # 添加按钮样式
        self.set_temp_btn.set_style_bg_color(lv.palette_main(lv.PALETTE.BLUE), 0)
        self.set_temp_btn.set_style_bg_color(lv.palette_darken(lv.PALETTE.BLUE, 2), lv.STATE.PRESSED)
        
        # 创建设置按钮标签
        self.set_temp_label = lv.label(self.set_temp_btn)
        self.set_temp_label.set_text("SET")
        self.set_temp_label.center()
        self.set_temp_label.set_style_text_color(lv.color_white(), 0)
        
        # 状态显示相关变量
        self.status_timer = None
        self.last_status_time = 0
    
    def on_power_clicked(self, evt):
        # 声明使用全局变量
        global is_power_on, mqtt_client
        
        # 获取触发事件的按钮对象
        btn = evt.get_target()
        
        # 检查是否是值改变事件
        if evt.get_code() == lv.EVENT.VALUE_CHANGED:
            # 更新电源状态为按钮的当前状态
            is_power_on = btn.has_state(lv.STATE.CHECKED)
            
            # 尝试发送MQTT消息
            if mqtt_client:
                try:
                    # 根据开关状态发送"on"或"off"
                    message = b"on" if is_power_on else b"off"
                    mqtt_client.publish(MQTT_TOPIC, message)
                    # 显示发送状态
                    self.show_status("Sent: " + message.decode())
                except Exception as e:
                    # 如果发送失败，显示错误
                    self.show_status("Send failed")
    
    def on_temp_changed(self, evt):
        # 声明使用全局变量
        global current_temp
        
        # 获取触发事件的滑块对象
        slider = evt.get_target()
        
        # 检查是否是值改变事件
        if evt.get_code() == lv.EVENT.VALUE_CHANGED:
            # 更新当前温度值
            current_temp = slider.get_value()
            # 更新温度显示标签
            self.temp_label.set_text(f"{current_temp}°C")
    
    def on_set_temp_clicked(self, evt):
        # 声明使用全局变量
        global current_temp, mqtt_client
        
        # 检查是否是点击事件
        if evt.get_code() == lv.EVENT.CLICKED:
            # 尝试发送MQTT消息
            if mqtt_client:
                try:
                    # 发送温度设置命令
                    message = f"set {current_temp}".encode()
                    mqtt_client.publish(MQTT_TOPIC, message)
                    # 显示发送状态
                    self.show_status(f"Sent: set {current_temp}")
                except Exception as e:
                    # 如果发送失败，显示错误
                    self.show_status("Send failed")
    
    def set_power_state(self, state):
        if state:
            self.power_btn.add_state(lv.STATE.CHECKED)
        else:
            self.power_btn.clear_state(lv.STATE.CHECKED)
    
    def show_status(self, text):
        # 显示状态文本
        self.status_label.set_text(text)
        # 记录显示时间
        self.last_status_time = time.time()
    
    def check_status_timeout(self):
        # 检查是否需要清除状态显示
        if self.status_label.get_text() != "":
            if time.time() - self.last_status_time > 10:  # 增加到10秒
                self.status_label.set_text("")

# ------------------------------ 网络管理类 ------------------------------
class NetworkManager:
    def __init__(self, status_bar):
        self.status_bar = status_bar
        self.mqtt_client = None
        self.wlan = network.WLAN(network.STA_IF)
        
    def connect_wifi(self):
        global wifi_connected
        self.wlan.active(True)
        if not self.wlan.isconnected():
            self.status_bar.set_status("Connecting WiFi...")
            self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            
            retry = 0
            while not self.wlan.isconnected() and retry < 20:
                time.sleep(0.5)
                retry += 1
                dots = "." * (retry % 4)
                self.status_bar.set_status(f"Connecting WiFi{dots}")
                
        if self.wlan.isconnected():
            wifi_connected = True
            self.status_bar.set_status("WiFi Connected")
            self.status_bar.update_signal(self.wlan.status('rssi'))
            return True
        else:
            wifi_connected = False
            self.status_bar.set_status("WiFi Connection Failed")
            return False
    
    def connect_mqtt(self):
        global mqtt_client
        if not wifi_connected:
            self.status_bar.set_status("No WiFi Connection")
            return False
            
        try:
            # 如果已经有连接，先断开
            if self.mqtt_client:
                try:
                    self.mqtt_client.disconnect()
                except:
                    pass
                
            # 创建新的MQTT客户端
            client_id = f'esp32_lvgl_{time.ticks_ms()}'
            self.status_bar.set_status("Connecting MQTT...")
            
            # 创建MQTT客户端实例，增加keepalive时间
            self.mqtt_client = MQTTClient(
                client_id=client_id,
                server=MQTT_SERVER,
                port=1883,
                keepalive=120  # 增加到120秒
            )
            
            # 设置回调并连接
            self.mqtt_client.set_callback(self.on_mqtt_message)
            self.mqtt_client.connect()
            time.sleep(0.1)
            
            # 订阅主题
            self.mqtt_client.subscribe(MQTT_TOPIC)
            mqtt_client = self.mqtt_client
            
            # 发送上线消息
            self.mqtt_client.publish(MQTT_TOPIC, b"device online")
            
            self.status_bar.set_status("MQTT Connected")
            return True
            
        except Exception as e:
            print(f"MQTT Error: {str(e)}")
            self.mqtt_client = None
            mqtt_client = None
            self.status_bar.set_status("MQTT Failed")
            return False
    
    def on_mqtt_message(self, topic, msg):
        global is_power_on
        try:
            if topic == MQTT_TOPIC:
                message = msg.decode().lower()  # 转换为小写
                if message == "on" and not is_power_on:
                    is_power_on = True
                    control_panel.set_power_state(True)
                    self.mqtt_client.publish(MQTT_TOPIC, b"ONON")
                elif message == "off" and is_power_on:
                    is_power_on = False
                    control_panel.set_power_state(False)
                    self.mqtt_client.publish(MQTT_TOPIC, b"OFFOFF")
        except Exception as e:
            print("MQTT Message Error:", str(e))
    
    def check_connections(self):
        # 检查WiFi连接
        if not self.wlan.isconnected():
            self.connect_wifi()
            return  # 如果WiFi重连，等待下一次检查再连MQTT
            
        # 检查MQTT连接
        if wifi_connected and (self.mqtt_client is None):
            time.sleep(1)  # 添加短暂延时
            self.connect_mqtt()

# ------------------------------ 主程序 ------------------------------
# 屏幕初始化
p16 = Pin(16, Pin.OUT)
p16.value(1)

disp = ili9488(miso=13, mosi=11, clk=12, cs=10, dc=17, rst=18,
               spihost=VSPI_HOST, mhz=20, power=-1, backlight=-1,
               factor=16, hybrid=True, width=480, height=320,
               invert=False, double_buffer=True, half_duplex=False, rot=-2)

touch = ft6x36(sda=6, scl=7, width=320, height=480, 
               inv_x=True, inv_y=False, swap_xy=True)

# 创建主屏幕
scr = lv.obj()
scr = lv.scr_act()
scr.clean()

# 创建UI组件
status_bar = StatusBar(scr)
network_manager = NetworkManager(status_bar)
control_panel = ControlPanel(scr, mqtt_client)

# 连接网络
network_manager.connect_wifi()
network_manager.connect_mqtt()

# 显示屏幕
lv.scr_load(scr)

# 主循环
def main():
    last_wifi_check = 0
    last_mqtt_ping = 0
    
    while True:
        time.sleep(0.1)
        
        # 定期检查连接状态
        current_time = time.time()
        
        # 每5秒检查一次WiFi
        if current_time - last_wifi_check > 5:
            network_manager.check_connections()
            last_wifi_check = current_time
        
        # 每60秒发送一次MQTT ping
        if current_time - last_mqtt_ping > 60:
            if network_manager.mqtt_client:
                try:
                    network_manager.mqtt_client.ping()
                    last_mqtt_ping = current_time
                except:
                    network_manager.mqtt_client = None
                    network_manager.status_bar.set_status("MQTT Connection Lost")
        
        # 检查MQTT消息
        if network_manager.mqtt_client:
            try:
                network_manager.mqtt_client.check_msg()
            except Exception as e:
                if str(e) != "-1":  # 忽略常见的-1错误
                    network_manager.mqtt_client = None
                    network_manager.status_bar.set_status("MQTT Connection Lost")
        
        # 检查状态显示超时
        control_panel.check_status_timeout()

if __name__ == '__main__':
    main()