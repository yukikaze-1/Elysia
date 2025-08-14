"""

"""
from dataclasses import dataclass

@dataclass
class Temperature:
    """温度信息"""
    value: float = 0.0  # 温度值
    unit: str = "C"  # 温度单位，默认为摄氏度

@dataclass
class Humidity:
    """湿度信息"""
    value: float = 0.0  # 湿度值
    unit: str = "%"  # 湿度单位，默认为百分比
    
@dataclass
class AirPressure:
    """气压信息"""
    value: float = 1013.25  # 气压值，单位百帕
    unit: str = "hPa"  # 气压单位，默认为百帕

@dataclass
class Speed:
    """速度信息"""
    value: float = 0.0  # 速度值
    unit: str = "m/s"  # 速度单位，默认为米每秒

@dataclass
class Weather:
    """天气信息"""
    temperature: Temperature | None = None
    humidity: Humidity | None = None
    wind_speed: Speed | None = None  # 风速信息


"""
    方向、位置、距离等定义
"""

from dataclasses import dataclass
import math

@dataclass
class Direction:
    """方向 - 使用单位向量表示"""
    x: float = 1
    y: float = 1
    z: float = 1
    
    def __post_init__(self):
        """确保是单位向量"""
        magnitude = math.sqrt(self.x**2 + self.y**2 + self.z**2)
        if magnitude > 0:
            self.x /= magnitude
            self.y /= magnitude
            self.z /= magnitude
    
@dataclass
class Position:
    """绝对位置坐标"""
    x: float = 0
    y: float = 0
    z: float = 0

@dataclass
class Location:
    """位置信息（可以是相对位置或绝对位置）"""
    # 如果是相对位置，需要参考点
    reference_entity_position: Position | None = None
    direction: Direction | None = None  # 方向
    distance: float | None = None  # 距离，单位米

    position: Position | None = None#绝对位置

    def __post_init__(self):
        """确保有一个坐标"""
        if not self.position:
            self.position = Position()
        elif not self.reference_entity_position and not self.direction and not self.distance:
            self.reference_entity_position = Position()
            self.direction = Direction()
            self.distance = 0.0