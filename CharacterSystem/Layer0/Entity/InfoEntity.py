"""
    方向、位置、距离等信息
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