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
power_on_time = 0                # 开机时间戳

# ------------------------------ Wi-Fi和MQTT设置 ------------------------------
# Wi-Fi配置列表
WIFI_CONFIGS = [
    {"ssid": "office", "password": "gdzsam632"},
    {"ssid": "office_2.4", "password": "gdzsam632"}
]
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
        
        # 创建时间标签 (左侧)
        self.time_label = lv.label(self.container)
        self.time_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)  # 白色文字
        self.time_label.align(lv.ALIGN.LEFT_MID, 5, 0)
        self.update_time()  # 初始化时间显示
        
        # 创建信号强度标签 (右侧)
        self.signal_label = lv.label(self.container)
        self.signal_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)  # 白色文字
        self.signal_label.align(lv.ALIGN.RIGHT_MID, -5, 0)
        
        # 创建状态信息标签 (中间)
        self.status_label = lv.label(self.container)
        self.status_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)  # 白色文字
        self.status_label.align(lv.ALIGN.CENTER, 0, 0)
        self.status_label.set_text("Initializing...")
        
        # 创建时间更新定时器
        self.time_timer = lv.timer_create(self.timer_cb, 1000, None)  # 每秒更新一次
    
    def timer_cb(self, timer):
        # 更新时间显示
        self.update_time()
    
    def update_time(self):
        # 获取当前时间并格式化
        current_time = time.localtime()
        time_str = "{:02d}:{:02d}:{:02d}".format(current_time[3], current_time[4], current_time[5])
        self.time_label.set_text(time_str)
    
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

# ------------------------------ 主界面类 ------------------------------
class MainScreen:
    def __init__(self):
        # 创建主屏幕
        self.scr = lv.obj()
        self.scr = lv.scr_act()
        self.scr.clean()
        
        # 创建状态栏
        self.status_bar = StatusBar(self.scr)
        
        # 创建控制面板容器
        self.main_cont = lv.obj(self.scr)
        self.main_cont.set_size(480, 290)  # 留出状态栏空间
        self.main_cont.set_pos(0, 30)      # 位于状态栏下方
        self.main_cont.set_style_pad_all(0, 0)
        self.main_cont.set_style_border_width(0, 0)
        self.main_cont.set_style_radius(0, 0)
        
        # 创建控制面板
        self.control_panel = ControlPanel(self.main_cont, mqtt_client)
        
        # 显示屏幕
        lv.scr_load(self.scr)

# ------------------------------ 控制面板类 ------------------------------
class ControlPanel:
    def __init__(self, parent, mqtt_client):
        # 保存MQTT客户端引用
        self.mqtt_client = mqtt_client
        
        # 创建控制区域（直接在父容器中）
        self.control_cont = lv.obj(parent)
        self.control_cont.set_size(460, 270)
        self.control_cont.set_style_pad_all(5, 0)
        self.control_cont.set_style_border_width(0, 0)  # 移除边框
        self.control_cont.center()  # 居中显示

        # 创建电源开关按钮（移到图标右侧）
        self.power_btn = lv.switch(self.control_cont)
        self.power_btn.set_size(80, 40)
        self.power_btn.set_pos(100, 20)  # 设置在图标右侧
        self.power_btn.add_event_cb(self.on_power_clicked, lv.EVENT.VALUE_CHANGED, None)        
        
        # 创建遥控器图标 - 使用文件
        self.icon_img = lv.img(self.control_cont)
        
        # 从文件加载图像
        try:
            # 直接从文件加载图像
            with open("./aircon.png", "rb") as f:
                png_data = f.read()
            img = lv.img_dsc_t({
                "data_size": len(png_data),
                "data": png_data
            })
            self.icon_img.set_src(img)
            
            # 设置图标位置
            btn_center_y = 20 + (40 / 2)  # 按钮y坐标 + 按钮高度的一半
            # 设置图标位置，使其垂直中心与按钮垂直中心对齐
            self.icon_img.set_pos(10, int(btn_center_y - 40))  # 假设图标高度约为80像素            
            # 可选：设置图像大小（如果需要调整大小）
            self.icon_img.set_zoom(256)  # 256 = 100%，可以调整缩放比例

        except Exception as e:
            print("图标加载失败:", str(e))
        
        # 创建电源标签
        self.power_label = lv.label(self.control_cont)
        self.power_label.set_text("Power")
        self.power_label.align_to(self.power_btn, lv.ALIGN.OUT_RIGHT_MID, 10, 0)
        
        # 创建开机时间标签
        self.power_time_label = lv.label(self.control_cont)
        self.power_time_label.set_style_text_color(lv.color_make(0, 200, 0), 0)  # 绿色文字
        self.power_time_label.align_to(self.power_label, lv.ALIGN.OUT_RIGHT_MID, 10, 0)
        self.power_time_label.add_flag(lv.obj.FLAG.HIDDEN)  # 初始状态隐藏
        
        # 创建开机时间更新定时器
        self.power_timer = lv.timer_create(self.update_power_time, 1000, None)  # 每秒更新一次
        
        # 创建温度控制容器（可折叠）
        self.temp_cont = lv.obj(self.control_cont)
        self.temp_cont.set_size(280, 160)
        self.temp_cont.set_pos(100, 80)  # 位于电源按钮下方
        self.temp_cont.set_style_border_width(0, 0)  # 无边框
        self.temp_cont.set_style_pad_all(5, 0)
        
        # 创建温度滑块（放在温度容器中）
        self.temp_slider = lv.slider(self.temp_cont)
        self.temp_slider.set_size(250, 20)
        self.temp_slider.set_range(16, 30)
        self.temp_slider.set_value(current_temp, lv.ANIM.OFF)
        self.temp_slider.add_event_cb(self.on_temp_changed, lv.EVENT.VALUE_CHANGED, None)
        self.temp_slider.set_pos(0, 10)  # 在容器内的位置
        
        # 设置滑块样式
        self.temp_slider.set_style_bg_color(lv.color_make(128, 128, 128), lv.PART.MAIN)
        self.temp_slider.set_style_bg_color(lv.color_make(0, 0, 255), lv.PART.INDICATOR)
        self.temp_slider.set_style_bg_color(lv.color_make(0, 0, 255), lv.PART.KNOB)
        
        # 创建温度显示标签
        self.temp_label = lv.label(self.temp_cont)
        self.temp_label.set_text(f"{current_temp}°C")  # 设置初始温度文本
        self.temp_label.align_to(self.temp_slider, lv.ALIGN.OUT_BOTTOM_MID, 0, 10)  # 放在滑块下方居中
        
        # 创建设置温度按钮 - 放在温度标签下方
        self.set_temp_btn = lv.btn(self.temp_cont)  # 创建按钮对象
        self.set_temp_btn.set_size(100, 40)  # 设置按钮大小
        self.set_temp_btn.align_to(self.temp_label, lv.ALIGN.OUT_BOTTOM_MID, 0, 15)  # 放在温度标签下方居中
        self.set_temp_btn.add_event_cb(self.on_set_temp_clicked, lv.EVENT.CLICKED, None)  # 添加点击事件回调
        
        # 设置按钮样式
        self.set_temp_btn.set_style_bg_color(lv.color_make(0, 0, 255), 0)  # 正常状态为蓝色
        self.set_temp_btn.set_style_bg_color(lv.color_make(0, 0, 200), lv.STATE.PRESSED)  # 按下状态为深蓝色
        
        # 创建设置按钮标签
        self.set_temp_label = lv.label(self.set_temp_btn)  # 创建标签对象
        self.set_temp_label.set_text("SET")  # 设置标签文本
        self.set_temp_label.center()  # 标签居中
        self.set_temp_label.set_style_text_color(lv.color_make(255, 255, 255), 0)  # 设置文字颜色为白色
        
        # 添加按钮冷却时间变量
        self.btn_cooldown_time = 0  # 按钮冷却时间戳
        
        # 创建状态显示标签（简化样式）
        self.status_label = lv.label(self.control_cont)
        self.status_label.set_text("")
        self.status_label.set_style_text_color(lv.color_make(0, 0, 255), 0)  # 蓝色文字
        self.status_label.align(lv.ALIGN.BOTTOM_MID, 0, -10)  # 底部居中对齐
        
        # 状态显示相关变量
        self.status_timer = None
        self.last_status_time = 0
        
        # 初始状态设置
        if not is_power_on:
            # 初始状态为关闭时，隐藏温度控制容器
            self.temp_cont.add_flag(lv.obj.FLAG.HIDDEN)
        
    def on_power_clicked(self, evt):
        # 声明使用全局变量
        global is_power_on, mqtt_client, power_on_time
        
        # 获取触发事件的按钮对象
        btn = evt.get_target()
        
        # 检查是否是值改变事件
        if evt.get_code() == lv.EVENT.VALUE_CHANGED:
            # 更新电源状态为按钮的当前状态
            is_power_on = btn.has_state(lv.STATE.CHECKED)
            
            # 根据电源状态显示或隐藏温度控制容器
            if is_power_on:
                # 记录开机时间
                power_on_time = time.time()
                # 显示开机时间标签
                self.power_time_label.clear_flag(lv.obj.FLAG.HIDDEN)
                self.update_power_time(None)  # 立即更新显示
                
                # 创建展开动画
                self.temp_cont.clear_flag(lv.obj.FLAG.HIDDEN)  # 先显示容器
                
                # 创建高度动画
                anim = lv.anim_t()
                anim.init()
                anim.set_var(self.temp_cont)
                anim.set_values(0, 160)  # 从0到160的高度
                anim.set_time(300)  # 300ms
                anim.set_path_cb(lv.anim_t.path_ease_out)
                
                # 设置动画属性回调
                def cb_set_height(obj, height):
                    obj.set_height(height)
                anim.set_custom_exec_cb(lambda a, val: cb_set_height(self.temp_cont, val))
                
                # 启动动画
                lv.anim_t.start(anim)
            else:
                # 隐藏开机时间标签
                self.power_time_label.add_flag(lv.obj.FLAG.HIDDEN)
                
                # 创建折叠动画
                anim = lv.anim_t()
                anim.init()
                anim.set_var(self.temp_cont)
                anim.set_values(160, 0)  # 从160到0的高度
                anim.set_time(300)  # 300ms
                anim.set_path_cb(lv.anim_t.path_ease_in)
                
                # 设置动画属性回调和结束回调
                def cb_set_height(obj, height):
                    obj.set_height(height)
                    if height == 0:
                        obj.add_flag(lv.obj.FLAG.HIDDEN)  # 动画结束后隐藏
                anim.set_custom_exec_cb(lambda a, val: cb_set_height(self.temp_cont, val))
                
                # 启动动画
                lv.anim_t.start(anim)
            
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
        global current_temp, mqtt_client, is_power_on
        
        # 检查是否是点击事件
        if evt.get_code() == lv.EVENT.CLICKED:
            # 尝试发送MQTT消息
            if mqtt_client:
                try:
                    # 只有在开机状态下才发送温度设置命令
                    if is_power_on:
                        # 发送温度设置命令
                        message = f"set {current_temp}".encode()
                        mqtt_client.publish(MQTT_TOPIC, message)
                        self.show_status(f"Sent: set {current_temp}")
                        
                        # 禁用按钮3秒
                        self.set_temp_btn.add_state(lv.STATE.DISABLED)  # 禁用按钮
                        
                        # 创建定时器，3秒后恢复按钮状态
                        def enable_button(timer):
                            self.set_temp_btn.clear_state(lv.STATE.DISABLED)  # 恢复按钮状态
                        
                        # 使用定时器延迟恢复按钮状态
                        lv.timer_create(enable_button, 3000, None)  # 3000ms后执行
                except Exception as e:
                    self.show_status("Send failed")
    
    def update_power_time(self, timer):
        global is_power_on, power_on_time
        
        # 只在开机状态下更新时间
        if is_power_on:
            # 计算已开机时间（秒）
            elapsed = int(time.time() - power_on_time)
            
            # 转换为时:分:秒格式
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60
            
            # 更新标签文本
            if hours > 0:
                time_text = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
            else:
                time_text = "{:02d}:{:02d}".format(minutes, seconds)
                
            self.power_time_label.set_text(time_text)
    
    def set_power_state(self, state):
        global power_on_time
        
        if state:
            self.power_btn.add_state(lv.STATE.CHECKED)
            # 记录开机时间
            power_on_time = time.time()
            # 显示开机时间标签
            self.power_time_label.clear_flag(lv.obj.FLAG.HIDDEN)
            self.update_power_time(None)  # 立即更新显示
            # 显示温度控制容器
            self.temp_cont.clear_flag(lv.obj.FLAG.HIDDEN)
            self.temp_cont.set_height(160)  # 恢复高度
        else:
            self.power_btn.clear_state(lv.STATE.CHECKED)
            # 隐藏开机时间标签
            self.power_time_label.add_flag(lv.obj.FLAG.HIDDEN)
            # 隐藏温度控制容器
            self.temp_cont.add_flag(lv.obj.FLAG.HIDDEN)
            self.temp_cont.set_height(0)  # 设置高度为0
    
    def show_status(self, text):
        # 显示状态文本
        self.status_label.set_text(text)
        
        # 先设置透明度为0，避免闪烁
        self.status_label.set_style_text_opa(lv.OPA._0, 0)
        
        # 创建淡入动画
        anim_in = lv.anim_t()
        anim_in.init()
        anim_in.set_var(self.status_label)
        anim_in.set_values(lv.OPA._0, lv.OPA._100)  # 从完全透明到不透明
        anim_in.set_time(300)  # 300ms
        anim_in.set_path_cb(lv.anim_t.path_ease_in)
        
        # 设置动画属性回调
        def cb_set_opacity(label, val):
            label.set_style_text_opa(val, 0)  # 只改变文字透明度
        anim_in.set_custom_exec_cb(lambda a, val: cb_set_opacity(self.status_label, val))
        
        # 启动动画
        lv.anim_t.start(anim_in)
        
        # 记录显示时间
        self.last_status_time = time.time()
    
    def check_status_timeout(self):
        # 检查是否需要清除状态显示
        if self.status_label.get_text() != "":  # 如果状态标签有文本
            if time.time() - self.last_status_time > 3:  # 3秒后开始淡出
                # 防止重复触发动画
                if self.last_status_time == 0:
                    return
                    
                # 创建淡出动画
                anim_out = lv.anim_t()  # 创建动画对象
                anim_out.init()  # 初始化动画
                anim_out.set_var(self.status_label)  # 设置动画目标
                anim_out.set_values(lv.OPA._100, lv.OPA._0)  # 从不透明到完全透明
                anim_out.set_time(500)  # 500ms动画时间
                anim_out.set_path_cb(lv.anim_t.path_ease_out)  # 设置动画路径
                
                # 设置动画属性回调和结束回调
                def cb_set_opacity(label, val):
                    label.set_style_text_opa(val, 0)  # 只改变文字透明度
                
                # 设置动画结束回调
                def anim_ready_cb(anim):
                    self.status_label.set_text("")  # 动画完成后清空文本
                
                # 设置回调函数
                anim_out.set_custom_exec_cb(lambda a, val: cb_set_opacity(self.status_label, val))
                anim_out.set_ready_cb(lambda a: anim_ready_cb(a))
                
                # 启动动画
                lv.anim_t.start(anim_out)
                self.last_status_time = 0  # 重置状态显示时间

# ------------------------------ 网络管理器类 ------------------------------
class NetworkManager:
    def __init__(self, status_bar):
        # 保存状态栏引用
        self.status_bar = status_bar
        self.wlan = network.WLAN(network.STA_IF)
        self.mqtt_client = None
        self.connected_ssid = None  # 记录已连接的SSID
        self.connection_attempts = 0  # 连接尝试次数
        self.last_connection_time = 0  # 上次连接尝试时间
    
    def connect_wifi(self):
        # 记录当前时间
        current_time = time.time()
        
        # 如果短时间内尝试次数过多，延迟重试
        if self.connection_attempts > 5 and current_time - self.last_connection_time < 60:
            if self.status_bar:
                self.status_bar.set_status("WiFi retry in 60s...")
            return False
        
        # 更新连接尝试记录
        self.connection_attempts += 1
        self.last_connection_time = current_time
        
        # 确保WiFi接口已激活
        if not self.wlan.active():
            self.wlan.active(True)
            time.sleep(1)  # 等待接口激活
        
        # 如果已连接，先断开
        if self.wlan.isconnected():
            self.wlan.disconnect()
            time.sleep(1)  # 等待断开连接
        
        # 更新状态栏
        if self.status_bar:
            self.status_bar.set_status("Scanning WiFi...")
        
        # 扫描可用网络
        try:
            networks = self.wlan.scan()
            print(f"扫描到 {len(networks)} 个WiFi网络")
        except Exception as e:
            print("WiFi扫描失败:", str(e))
            if self.status_bar:
                self.status_bar.set_status("WiFi scan failed")
            networks = []
        
        # 创建SSID到信号强度的映射
        available_networks = {}
        for net in networks:
            try:
                ssid = net[0].decode('utf-8')
                rssi = net[3]
                available_networks[ssid] = rssi
                print(f"找到网络: {ssid}, 信号强度: {rssi} dBm")
            except:
                pass  # 忽略无法解码的SSID
        
        # 按信号强度排序我们的配置网络
        sorted_configs = []
        for config in WIFI_CONFIGS:
            ssid = config["ssid"]
            if ssid in available_networks:
                sorted_configs.append({
                    "ssid": ssid,
                    "password": config["password"],
                    "rssi": available_networks[ssid]
                })
        
        # 如果没有找到任何已知网络
        if not sorted_configs:
            print("未找到任何已配置的WiFi网络")
            if self.status_bar:
                self.status_bar.set_status("No known WiFi found")
            return False
        
        # 按信号强度从高到低排序
        sorted_configs.sort(key=lambda x: x["rssi"], reverse=True)
        
        # 尝试连接信号最强的网络
        connected = False
        for config in sorted_configs:
            ssid = config["ssid"]
            password = config["password"]
            rssi = config["rssi"]
            
            if self.status_bar:
                self.status_bar.set_status(f"Connecting to {ssid}...")
            
            print(f"尝试连接到 {ssid} (信号强度: {rssi} dBm)")
            try:
                # 连接WiFi
                self.wlan.connect(ssid, password)
                
                # 等待连接或超时
                max_wait = 15  # 增加等待时间
                while max_wait > 0:
                    if self.wlan.isconnected():
                        connected = True
                        self.connected_ssid = ssid
                        break
                    max_wait -= 1
                    if self.status_bar:
                        self.status_bar.set_status(f"Connecting to {ssid}... {max_wait}s")
                    time.sleep(1)
                
                if connected:
                    # 获取IP地址
                    ip = self.wlan.ifconfig()[0]
                    print(f"已连接到 {ssid}, IP: {ip}")
                    
                    # 更新全局WiFi连接状态
                    global wifi_connected
                    wifi_connected = True
                    
                    # 重置连接尝试计数
                    self.connection_attempts = 0
                    
                    if self.status_bar:
                        self.status_bar.set_status(f"Connected: {ssid}")
                        # 更新信号强度显示
                        self.status_bar.update_signal(rssi)
                    break
                else:
                    print(f"连接到 {ssid} 超时")
                    # 确保断开连接
                    self.wlan.disconnect()
                    time.sleep(1)
            except Exception as e:
                print(f"连接到 {ssid} 失败: {str(e)}")
                # 确保断开连接
                try:
                    self.wlan.disconnect()
                except:
                    pass
                time.sleep(1)
        
        # 如果所有网络都连接失败
        if not connected:
            print("无法连接到任何已知网络")
            # 更新全局WiFi连接状态
            global wifi_connected
            wifi_connected = False
            if self.status_bar:
                self.status_bar.set_status("No WiFi Connection")
        
        return connected
    
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
                    self.control_panel.set_power_state(True)
                    self.mqtt_client.publish(MQTT_TOPIC, b"ONON")
                elif message == "off" and is_power_on:
                    is_power_on = False
                    self.control_panel.set_power_state(False)
                    self.mqtt_client.publish(MQTT_TOPIC, b"OFFOFF")
        except Exception as e:
            print("MQTT Message Error:", str(e))
    
    def check_connections(self):
        # 检查WiFi连接
        if not self.wlan.isconnected():
            # 如果WiFi断开，尝试重新连接
            if self.status_bar:
                self.status_bar.set_status("WiFi Reconnecting...")
            
            # 更新全局WiFi连接状态
            global wifi_connected
            wifi_connected = False
            
            # 尝试重新连接WiFi
            wifi_connected = self.connect_wifi()
            
            # 如果WiFi重新连接成功，尝试重新连接MQTT
            if wifi_connected and not self.mqtt_client:
                self.connect_mqtt()
            elif not wifi_connected:
                # 清除MQTT客户端
                self.mqtt_client = None
        else:
            # 更新全局WiFi连接状态
            global wifi_connected
            wifi_connected = True
            
            # WiFi已连接，检查信号强度
            try:
                # 获取当前连接的信号强度
                current_rssi = self.wlan.status('rssi')
                
                # 更新状态栏信号强度显示
                if self.status_bar:
                    # 确保状态栏显示连接状态
                    if self.connected_ssid:
                        self.status_bar.set_status(f"Connected: {self.connected_ssid}")
                    else:
                        self.status_bar.set_status("WiFi Connected")
                    # 更新信号强度
                    self.status_bar.update_signal(current_rssi)
                
                # 检查MQTT连接
                if not self.mqtt_client:
                    self.connect_mqtt()
            except Exception as e:
                print("获取WiFi状态失败:", str(e))
                
# ------------------------------ 主程序 ------------------------------
def main():
    # 初始化GPIO16引脚为输出模式
    p16 = Pin(16, Pin.OUT)
    # 设置GPIO16引脚为高电平，用于控制屏幕电源
    p16.value(1)

    # 初始化ILI9488显示屏
    disp = ili9488(
        miso=13,           # MISO引脚连接到GPIO13
        mosi=11,           # MOSI引脚连接到GPIO11
        clk=12,            # 时钟引脚连接到GPIO12
        cs=10,             # 片选引脚连接到GPIO10
        dc=17,             # 数据/命令引脚连接到GPIO17
        rst=18,            # 复位引脚连接到GPIO18
        spihost=VSPI_HOST, # 使用VSPI总线
        mhz=20,            # SPI时钟频率20MHz
        power=-1,          # 不使用电源控制引脚
        backlight=-1,      # 不使用背光控制引脚
        factor=16,         # 颜色因子
        hybrid=True,       # 使用混合模式
        width=480,         # 屏幕宽度480像素
        height=320,        # 屏幕高度320像素
        invert=False,      # 不反转颜色
        double_buffer=True, # 使用双缓冲
        half_duplex=False, # 不使用半双工模式
        rot=-2             # 屏幕旋转角度
    )

    # 初始化FT6X36触摸控制器
    touch = ft6x36(
        sda=6,             # I2C数据线连接到GPIO6
        scl=7,             # I2C时钟线连接到GPIO7
        width=320,         # 触摸屏宽度
        height=480,        # 触摸屏高度
        inv_x=True,        # X轴反转
        inv_y=False,       # Y轴不反转
        swap_xy=True       # 交换X和Y坐标
    )

    # 创建主界面
    main_screen = MainScreen()
    
    # 创建网络管理器实例，传入状态栏引用
    network_manager = NetworkManager(main_screen.status_bar)
    
    # 连接WiFi网络 - 增加重试逻辑
    wifi_connected = False
    retry_count = 0
    
    while not wifi_connected and retry_count < 3:
        wifi_connected = network_manager.connect_wifi()
        if not wifi_connected:
            retry_count += 1
            time.sleep(2)  # 短暂延时后重试
    
    # 如果WiFi连接成功，尝试连接MQTT
    if wifi_connected:
        network_manager.connect_mqtt()

    # 初始化主循环计时器
    last_wifi_check = 0    # 上次WiFi检查时间
    last_mqtt_ping = 0     # 上次MQTT ping时间
    
    # 主循环
    while True:
        # 短暂延时，避免CPU占用过高
        time.sleep(0.1)
        
        # 获取当前时间戳
        current_time = time.time()
        
        # 每5秒检查一次WiFi和MQTT连接状态
        if current_time - last_wifi_check > 5:
            # 调用连接检查函数
            network_manager.check_connections()
            # 更新上次检查时间
            last_wifi_check = current_time
        
        # 每60秒发送一次MQTT ping，保持连接活跃
        if current_time - last_mqtt_ping > 60:
            # 检查MQTT客户端是否存在
            if network_manager.mqtt_client:
                try:
                    # 发送ping命令
                    network_manager.mqtt_client.ping()
                    # 更新上次ping时间
                    last_mqtt_ping = current_time
                except:
                    # 如果ping失败，重置MQTT客户端
                    network_manager.mqtt_client = None
                    # 更新状态栏显示连接丢失信息
                    network_manager.status_bar.set_status("MQTT Connection Lost")
        
        # 检查MQTT消息
        if network_manager.mqtt_client:
            try:
                # 检查是否有新消息
                network_manager.mqtt_client.check_msg()
            except Exception as e:
                # 忽略常见的-1错误（无消息可读）
                if str(e) != "-1":
                    # 其他错误则重置MQTT客户端
                    network_manager.mqtt_client = None
                    # 更新状态栏显示连接丢失信息
                    network_manager.status_bar.set_status("MQTT Connection Lost")
        
        # 检查状态显示超时，处理状态文本的淡出效果
        main_screen.control_panel.check_status_timeout()

# 程序入口点
if __name__ == '__main__':
    # 调用主函数
    main() 