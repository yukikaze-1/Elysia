"""
物理环境负责  “外在、客观、可感知”  的一切
"""
from typing import Dict, List

from CharacterSystem.Layer0.GlobalClass import GlobalPersonManager, get_global_person_manager
from CharacterSystem.Layer0.Entity import *

class PhysicalEnvironment:
    """物理环境"""
    # TODO 待修改
    def __init__(self):
        self.persons_manager: GlobalPersonManager = get_global_person_manager() # 全局人员管理

        self.map = "<3D地图数据>"
        self.temperature_map = "<温度地图数据>"

        self.temperature: Temperature = Temperature()  # 默认温度
        self.humidity: Humidity = Humidity()  # 默认湿度
        self.air_pressure: AirPressure = AirPressure()  # 默认气压
        self.wind_speed: Speed = Speed()  # 默认风速


    def get_current_state(self):
        """获取当前物理环境状态"""
        pass
