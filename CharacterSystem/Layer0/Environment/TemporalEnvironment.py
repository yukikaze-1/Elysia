
from datetime import datetime

class TemporalEnvironment:
    """时间环境"""
    def __init__(self):
        self.current_time: datetime = datetime.now()
        self.time_period: str = "下午"
        self.season: str = "春天"
        
    def get_current_time(self)->datetime:
        return datetime.now()

    def get_current_time_period(self):
        pass
    
    def get_current_season(self):
        pass

    def get_current_state(self):
        """获取当前时间环境状态"""
        return {
            "current_time": self.current_time,
            "time_period": self.time_period,
            "season": self.season
        }
