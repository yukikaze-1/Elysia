"""
时间感知模块
"""
from datetime import datetime

class TemporalPerceptionModule:
    def __init__(self) -> None:
        self.current_time: datetime = datetime.now()
        self.time_zone = "UTC8"
        self.season = "春季"
        
    def get_time_info(self):
        return {
            "current_time": self.current_time,
            "time_zone": self.time_zone,
            "season": self.season
        }

    def is_available(self) -> bool:
        return True