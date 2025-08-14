"""
物理实体，会被物理环境层和社交场景层所引用
"""
from typing import List
from dataclasses import dataclass

from sqlalchemy import desc
from CharacterSystem.Layer0.Entity import Direction, Location

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
    
    @dataclass
    class AudioFeature:
        """声音特征"""
        feature_vector: List[float] | None = None  # 声音特征向量
        
    # @dataclass
    # class Personality:
    #     """性格特征"""
    #     description: str | None = "开朗、乐观、善良"
    
    # TODO 这两个不是物理特征。应该放在其他的地方
        
    # @dataclass
    # class BehavioralHabits:
    #     """行为习惯"""
    #     description: str | None = "喜欢阅读、爱好音乐"
        
        
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
    
    # 声音特征
    audio_feature: AudioFeature | None = None
    
    # 性格特征
    # personality: Personality | None = None
    
    # 行为习惯
    # behavioral_habits: BehavioralHabits | None = None

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
        
