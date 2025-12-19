
from datetime import datetime
import time
import os
from openai import OpenAI
from Demo.Utils import TimeEnvs, TimeOfDay, Season

class InputEventInfo:
    """输入事件类"""
    def __init__(self):
        self.input_type = "keyboard"  # 假设是键盘输入
        self.typing_duration_ms = 0  # 假设没有打字时间
        self.delete_count = 0  # 假设没有删除操作

    def to_dict(self) -> dict:
        """将输入事件转换为字典格式"""
        return {
                "input_type": self.input_type,
                "typing_duration_ms": self.typing_duration_ms,
                "delete_count": self.delete_count
        }
        
    def __str__(self):
        return f"InputEventInfo(type={self.input_type}, duration={self.typing_duration_ms}ms, deletes={self.delete_count})"

class UserMessage:
    """用户消息类"""
    def __init__(self, content: str):
        self.user_id: str = os.getenv("USER_ID", "default_user")
        self.content: str = content
        self.client_timestamp: float = time.time()
        self.input_event = InputEventInfo()

    def to_dict(self) -> dict:
        """将用户消息转换为字典格式"""
        return {
            "role": "user",
            "content": self.content,
            "client_timestamp": self.client_timestamp,
            "input_event": self.input_event.to_dict()
        }
        
    def __str__(self) -> str:
        return f"UserMessage(user_id={self.user_id}, content={self.content}, timestamp={self.client_timestamp}, input_event={self.input_event})"
        
class EnvironmentInformation:
    def __init__(self, current_time: float, 
                 time_of_day: str,
                 day_of_week: str,
                 season: str,
                 user_latency: float):
        self.current_time: float = current_time
        self.time_of_day: str = time_of_day
        self.day_of_week: str = day_of_week
        self.season: str = season
        self.user_latency: float = user_latency
    
    def to_dict(self):
        return {
            "current_time": self.current_time,
            "day_of_week":self.day_of_week,
            "user_latency": self.user_latency
        }            
        
class L0_Sensory_Processor:
    """
    处理传感器数据的类
    目前非常简陋
    """
    # TODO init中的的-1000需要删掉
    def __init__(self, last_message_timestamp: float = time.time()-1000):
        self.last_timestamp = last_message_timestamp
        self.time_envs = TimeEnvs()
        
    def get_envs(self) -> EnvironmentInformation:
        """主动获取传感器数据"""
        
        # TODO 待扩展
        current_time = time.time()
        dt = datetime.fromtimestamp(current_time)
        weekday: str = dt.strftime("%A")
        time_of_day: TimeOfDay = self.time_envs.get_time_of_day_from_timestamp(current_time)
        season: Season = self.time_envs.get_season_from_timestamp(current_time)
        return EnvironmentInformation(current_time, time_of_day.value, weekday, season, current_time - self.last_timestamp)


class L0_Output:
    """ L0 输出类，包含 Sensory Data"""
    def __init__(self, perception: str, envs: EnvironmentInformation):
        self.perception: str = perception
        self.envs: EnvironmentInformation = envs
        
    def to_dict(self) -> dict:
        """将 L0 输出转换为字典格式"""
        return {
            "perception": self.perception,
            "envs": self.envs
        }
        
    def debug(self):
        print(f"perception: {self.perception} \n facts:{self.envs.to_dict()}")

from Demo.Prompt import L0_SubConscious_System_Prompt, L0_SubConscious_User_Prompt

class L0_Module:
    def __init__(self, openai_client: OpenAI):
        self.openai_client = openai_client
        self.sensory_processor = L0_Sensory_Processor()
        self.time_envs = TimeEnvs()

    def run(self) -> L0_Output:
        # 1. 获取传感器数据
        current_env: EnvironmentInformation = self.sensory_processor.get_envs()
        
        # 2. 处理传感器数据
        
        # 3. 生成描述
        sensory_description: str = self.generate_sensory_description(current_env)
        
        # 4. 更新最后交互时间
        self.sensory_processor.last_timestamp = current_env.current_time

        return L0_Output(sensory_description, current_env)
    
    
    def get_latency_desc(self, latency: float)->str:
        """获取延迟描述"""
        latency_desc = ""

        if latency < 10: # 小于5秒
            latency_desc = "Instant_Reply (秒回/极快)"
        elif latency < 60: # 小于1分钟
            latency_desc = "Normal_Flow (正常节奏)"
        elif latency < 300: # 小于5分钟
            latency_desc = "Short_Wait (轻微等待)"
        else:
            latency_desc = "Long_Silence (漫长沉默)"
            
        return latency_desc
    
    
    def generate_sensory_description(self, envs: EnvironmentInformation)-> str:
        """生成环境描述"""
        
        latency_desc = self.get_latency_desc(envs.user_latency)
        dt = datetime.fromtimestamp(envs.current_time)
        
        system_prompt = L0_SubConscious_System_Prompt
        user_prompt = L0_SubConscious_User_Prompt.format(
            current_time=dt.isoformat(),
            day_of_week=dt.strftime("%A"),
            time_of_day=self.time_envs.get_time_of_day_from_timestamp(envs.current_time),
            season=self.time_envs.get_season_from_timestamp(envs.current_time),
            latency=envs.user_latency,
            latency_description=latency_desc
        )
        
        print("User Prompt:")
        print(user_prompt)
        
        response = self.openai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=False
        )
        
        if not response.choices[0].message.content:
            print("Error! Get empty response content.")
            return ""
            
        raw_content = response.choices[0].message.content
        
        return raw_content
    

def test():
    from dotenv import load_dotenv
    load_dotenv()
    url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=url)
    l0 = L0_Module(client)
    print("----- Testing L0 Module -----")
    print("User Message Input: 我睡不着。")
    user_message = UserMessage("我睡不着。")
    x = l0.run()
    sensory_description, envs = x.perception, x.envs
    print("Sensory Processor Output(Envs):")
    print(envs.to_dict())
    print("Sensory description:")
    print(sensory_description)


if __name__ == "__main__":
    test()
    
    