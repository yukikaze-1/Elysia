"""
L0 模块：
    1. 处理传感器数据 ---> 输出Raw Data
    
eg.
    L0 (潜意识/边缘系统/杏仁核)：
        职责：处理原始信号。它不负责社交，不负责语言，只负责**“产生情绪化学反应”**。
        特点：它很快，很原始，无法控制。
        输入：时间、心跳、沉默时长。
        输出：状态 (State) —— 如“焦虑”、“饥饿”、“兴奋”。
        例子：“我在发抖，我心跳很快。”（这不需要逻辑，这是生理反应）。

    L1 (主意识/前额叶皮层)：
        职责：处理社会行为。它负责把 L0 产生的情绪包装成语言。
        特点：它是理性的，它会撒谎，会伪装。
        输入：用户的话 + L0 传来的状态。
        输出：行为 (Behavior) —— 如“假装不在意”、“撒娇”、“阴阳怪气”。
        例子：“虽然我很慌（L0），但我决定深呼吸，回一句‘没事’（L1）。”
        
    模拟“口是心非” (Internal Conflict)
        这是拟人化最高级的地方。 只有当 L0 和 L1 分离时，你才能制造出完美的“口是心非”。
        L0 输出：State: Vulnerable, Lonely (我很脆弱，很想他)。
        L1 思考：潜意识告诉我我很想他，但我不能表现得太廉价（Elysia 的自尊心）。
        L1 最终表现：冷淡地回一句“哦，你来了。”（但内心独白是“太好了他终于来了”）。
        如果只有 L1，它很难同时hold住“原始欲望”和“社会面具”两个维度的计算，往往会顾此失彼。

ps:
    L0（潜意识/身体）
    L1（主意识/大脑皮层）
    专门的“情绪预处理器
    如果只有 L1，它很难同时hold住“原始欲望”和“社会面具”两个维度的计算，往往会顾此失彼。
    如果你想要 Elysia 偶尔“理智控制不住情绪”，或者“嘴硬心软”，那么保留 L0 是必须的，因为它代表了那个“无法控制的身体本能”
"""


import time
import logging 
from enum import Enum


# =============================================================================
# L0 数据结构定义
# =============================================================================
class Season(str, Enum):
    SPRING = "Spring"
    SUMMER = "Summer"
    AUTUMN = "Autumn"
    WINTER = "Winter"
    
class TimeOfDay(str, Enum):
    MIDNIGHT = "Midnight"        
    EARLY_MORNING = "Early_morning"  
    MORNING = "Morning"          
    NOON = "Noon"                
    AFTERNOON = "Afternoon"      
    EVENING = "Evening"          
    NIGHT = "Night"           
  
from datetime import datetime
    
class TimeInfo:
    """时间信息输出类"""
    # TODO 此处的默认全部设为0只是为了Dispatcher中的_handle_user_input函数中调用generate_reply时类型检查通过，实际使用时必须传入正确的值
    def __init__(self, current_time: float = 0, 
                #  user_latency: float = 0,
                #  last_message_timestamp: float = 0
                 ):
        self.current_time: float = current_time
        self.time_of_day: str = self._get_time_of_day_from_timestamp(self.current_time).value
        self.day_of_week: str = self._get_day_of_week(self.current_time)
        self.season: str = self._get_season_from_timestamp(current_time).value
        # self.user_latency: float = user_latency
        # self.last_message_timestamp: float = last_message_timestamp
        
    def to_dict(self):
        return {
            "current_time": self.current_time,
            "time_of_day": self.time_of_day,
            "day_of_week": self.day_of_week,
            "season": self.season,
            # "user_latency": self.user_latency,
            # "last_message_timestamp": self.last_message_timestamp
        }
        
    def to_l1_decide_to_act_dict(self):
        """L1 decide_to_act函数专用，用于主动感知"""
        return {
            "current_time": self.current_time,
            "time_of_day": self.time_of_day,
            "day_of_week": self.day_of_week,
            "season": self.season,
        }
    
    
    def _get_time_of_day_from_timestamp(self, timestamp: float) -> TimeOfDay:
        """通过timstamp获取时间段，如早中晚"""
        dt = datetime.fromtimestamp(timestamp)
        hour = dt.hour
        
        if 0 <= hour < 5:
            return TimeOfDay.MIDNIGHT
        elif 5 <= hour < 8:
            return TimeOfDay.EARLY_MORNING
        elif 8 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 13:
            return TimeOfDay.NOON
        elif 13 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 21:
            return TimeOfDay.EVENING
        else:  # 21 <= hour < 24
            return TimeOfDay.NIGHT
    
    def _get_season_from_timestamp(self, timestamp: float) -> Season:
        """通过timestamp获取季节"""
        dt = datetime.fromtimestamp(timestamp)
        month = dt.month

        if month in (3, 4, 5):
            return Season.SPRING
        elif month in (6, 7, 8):
            return Season.SUMMER
        elif month in (9, 10, 11):
            return Season.AUTUMN
        else:
            return Season.WINTER
        
    def _get_day_of_week(self, timestamp: float)-> str:
        """通过timestamp获取星期"""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%A")


class EnvironmentInformation:
    """L0 a 输出类"""
    def __init__(self, time_envs: TimeInfo):
        self.time_envs = time_envs
    
    def to_dict(self):
        return {
            "time envs": self.time_envs.to_dict() 
        }  

# =============================================================================
# L0 业务组件（各种传感器）
# =============================================================================           
from datetime import datetime 
 
class TimeSensor:
    def __init__(self, logger: logging.Logger):
        self.logger: logging.Logger = logger
        # self.last_message_timestamp = 0.0  # 上次消息时间戳
    
    def get_time(self)->TimeInfo:
        """获取时间信息"""
        self.logger.info("TimeSensor: Getting current time information...")
        current_time  = time.time()
        # # TODO 只是为了测试加上的-100，待修改
        # if self.last_message_timestamp == 0.0:
        #     self.last_message_timestamp = current_time - 100  
        # user_latency = current_time - self.last_message_timestamp
        res = TimeInfo(current_time=current_time, 
                    #    user_latency=user_latency, 
                    #    last_message_timestamp=self.last_message_timestamp
        )
        self.logger.info(f"TimeSensor: Current time information: {res.to_dict()}")
        return res
    
          

# =============================================================================
# L0 业务组件集成
# =============================================================================
       
class SensoryProcessor:
    """
    处理传感器数据的类
    目前非常简陋
    """
    def __init__(self, logger: logging.Logger):
        self.logger: logging.Logger = logger
        self.time_sensor: TimeSensor = TimeSensor(self.logger)
        
    def active_perception_envs(self) -> EnvironmentInformation:
        """主动获取传感器数据"""
        self.logger.info("Active perception: Gathering environment information...")
        # TODO 待扩展
        # 获取时间信息
        time_envs = self.time_sensor.get_time()
        
        self.logger.info("Environment information perception completed.")
        return EnvironmentInformation(time_envs=time_envs)

    
