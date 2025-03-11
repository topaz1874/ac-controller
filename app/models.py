from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json

db = SQLAlchemy()

class SensorData(db.Model):
    """传感器数据模型"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    pressure = db.Column(db.Float, nullable=True)
    battery = db.Column(db.Integer, nullable=True)
    rssi = db.Column(db.Integer, nullable=True)
    raw_data = db.Column(db.Text)  # 原始十六进制数据
    topic = db.Column(db.String(100))
    data_format = db.Column(db.String(10))  # 记录数据格式（434734或434731）
    
    def __repr__(self):
        return f'<SensorData {self.timestamp}: {self.temperature}°C, {self.humidity}%>'
    
    def to_dict(self):
        """将数据转换为字典"""
        return {
            'id': self.id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp_unix': int(self.timestamp.timestamp()),
            'temperature': self.temperature,
            'humidity': self.humidity,
            'pressure': self.pressure,
            'battery': self.battery,
            'rssi': self.rssi,
            'raw_data': self.raw_data,
            'topic': self.topic,
            'data_format': self.data_format
        }
    
    @staticmethod
    def from_mqtt_data(mqtt_data):
        """从MQTT数据创建SensorData对象"""
        parsed_data = mqtt_data['parsed_data']
        
        # 检查数据格式
        data_format = None
        raw_hex = parsed_data.get('_raw_hex', '')
        if raw_hex.startswith('434734'):
            data_format = '434734'
        elif raw_hex.startswith('434731'):
            data_format = '434731'
        
        # 创建新记录
        timestamp_str = mqtt_data.get('timestamp')
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            timestamp = datetime.utcnow()
        
        return SensorData(
            timestamp=timestamp,
            temperature=parsed_data.get('temperature', 0.0),
            humidity=parsed_data.get('humidity', 0.0),
            pressure=parsed_data.get('pressure'),
            battery=parsed_data.get('battery'),
            rssi=parsed_data.get('rssi'),
            raw_data=parsed_data.get('_raw_hex', ''),
            topic=mqtt_data.get('topic', ''),
            data_format=data_format
        )

def init_db(app):
    """初始化数据库"""
    db.init_app(app)
    with app.app_context():
        db.create_all()

def save_sensor_data(mqtt_data):
    """保存传感器数据到数据库"""
    sensor_data = SensorData.from_mqtt_data(mqtt_data)
    db.session.add(sensor_data)
    db.session.commit()
    return sensor_data

def get_recent_data(hours=24):
    """获取最近n小时的数据"""
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    return SensorData.query.filter(SensorData.timestamp >= cutoff_time).order_by(SensorData.timestamp).all()

def get_data_by_range(start_time, end_time):
    """获取指定时间范围内的数据"""
    return SensorData.query.filter(
        SensorData.timestamp >= start_time,
        SensorData.timestamp <= end_time
    ).order_by(SensorData.timestamp).all()

def cleanup_old_data(months=6):
    """清理旧数据（默认6个月前的数据）"""
    cutoff_time = datetime.utcnow() - timedelta(days=30*months)
    old_records = SensorData.query.filter(SensorData.timestamp < cutoff_time).all()
    count = len(old_records)
    
    for record in old_records:
        db.session.delete(record)
    
    db.session.commit()
    return count 