"""
物理实体，会被物理环境层和社交场景层所引用
"""
from dataclasses import dataclass
from enum import StrEnum
import math
from turtle import pos

from sympy import posify

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

@dataclass
class Person:
    """
    人，只描述人的物理实体信息
    (人的社会存在则在社交环境层进行描述)
    """
    @dataclass
    class Clothing:
        """衣物"""
        # 头部
        hair_description: str | None = "黑色直发"
        # 面部
        face_description: str | None = "黑框眼镜"
        # 上装
        top_description: str | None = "蓝色休闲装"
        # 下装
        bottoms_description: str | None = "黑色休闲裤"       
        # 脚部
        shoes_description: str | None = "白色运动鞋"  
        # 手部
        other_description: str | None = "手表"
        
        
    # 基本信息    
    person_id: int = 1
    name: str | None = "elysia"
    age: int | None = 18
    gender: str | None = "女"
    
    # 物理特征
    skin_color: str | None = "白皙"
    height: float | None = 1.60  # 身高，单位米
    weight: float | None = 45  # 体重，单位kg
    build: str | None = "标准"     # 体型：瘦弱/标准/健壮/肥胖
    
    # 位置和朝向
    sight_direction: Direction | None = None  # 视线方向，单位向量
    location: Location | None = None  # 位置

    # 状态
    posture: str | None = "站立"  # 站立/坐着/躺着/行走等
    expression : str | None = "微笑"  # 面部表情
    
    # 服装
    clothing: Clothing | None = None
    
    # 整体描述
    description: str | None = "这是一个人"

    def update_location(self, new_location: Location):
        """更新位置"""
        self.location = new_location

    def update_sight_direction(self, new_direction: Direction):
        """更新视线方向"""
        self.sight_direction = new_direction

    def update_clothing(self, new_clothing: Clothing):
        """更新服装"""
        self.clothing = new_clothing

    def update_posture(self, new_posture: str):
        """更新姿势"""
        self.posture = new_posture

    def update_expression(self, new_expression: str):
        """更新表情"""
        self.expression = new_expression
        
    def update_description(self, new_description: str):
        """更新描述"""
        self.description = new_description
        


@dataclass
class Item:
    """物品"""
    itemd_id: int | None = 1
    name: str = "书"
    category: str = "文具" # 类别
    owner_id: int | None = 1  # 所有者
    motion_states: str | None = "静止"  # 静止、移动
    location: Location | None = None # 位置
    # 总的描述
    description: str | None = "这是一本书"

    def update_location(self, new_location: Location):
        """更新位置"""
        self.location = new_location

    def update_owner_id(self, new_owner_id: int):
        """更新所有者"""
        self.owner_id = new_owner_id
        
    def update_motion_states(self, new_motion_states: str):
        """更新运动状态"""
        self.motion_states = new_motion_states

    def update_description(self, new_description: str):
        """更新描述"""
        self.description = new_description
        

class Entity:
    """物理实体"""
    def __init__(self, name: str):
        pass