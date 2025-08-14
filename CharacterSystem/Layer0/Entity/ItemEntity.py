from dataclasses import dataclass
from turtle import speed
from CharacterSystem.Layer0.Entity import Location


@dataclass
class Item:
    """物品"""
    itemd_id: int | None = 1
    name: str = "书"
    category: str = "文具" # 类别
    owner_id: int | None = 1  # 所有者
    motion_states: str | None = "静止"  # 静止、移动
    speed: float | None = 0.0  # 物品移动速度
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