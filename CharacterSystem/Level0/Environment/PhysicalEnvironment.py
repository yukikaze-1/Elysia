"""
物理环境负责  “外在、客观、可感知”  的一切
"""
from typing import Dict, List

class PhysicalEnvironment:
    """物理环境"""
    # TODO 待修改
    def __init__(self):
        self.persons_manager = GlobalPersonManager() # 全局人员管理
        self.lighting: str = "自然光"
        self.noise_level: str = "安静"
        self.temperature: str = "舒适"
        self.location_type: str = "室内"

    def get_current_lighting_state_from_sensor(self):
        """从传感器获取自然光参数"""
        pass

    def get_current_noise_level_from_sensor(self):
        """从传感器获取噪音水平参数"""
        pass

    def get_current_temperature_from_sensor(self):
        """从传感器获取温度参数"""
        pass
    
    def get_location_type_from_sensor(self):
        """从传感器获取位置类型参数"""
        pass

    def get_current_state(self):
        """获取当前物理环境状态"""
        return {
            "lighting": self.lighting,
            "noise_level": self.noise_level,
            "temperature": self.temperature,
            "location_type": self.location_type
        }
