
import json
from datetime import datetime
import os
from openai import OpenAI

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
        self.client_timestamp: float = datetime.now().timestamp()
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
        

class L0_Sensory_Processor:
    def __init__(self, last_message_timestamp: float = 0.0):
        self.last_timestamp = last_message_timestamp

    def analyze_time_context(self, current_timestamp):
        # 将时间戳转换为小时 (0-23)
        dt = datetime.fromtimestamp(current_timestamp)
        hour = dt.hour
        
        # 拟人化的时间感知逻辑
        if 0 <= hour < 5:
            return "Late_Night", "深夜时刻，通常意味着脆弱、寂寞或失眠。"
        elif 5 <= hour < 9:
            return "Early_Morning", "清晨，一天的开始，能量通常较低或刚苏醒。"
        elif 9 <= hour < 18:
            return "Work_Hours", "工作时间，可能比较忙碌，回复由于理性。"
        else:
            return "Evening", "私人时间，比较放松。"

    def analyze_latency(self, current_timestamp):
        if  self.last_timestamp == 0.0:
            return "First_Contact", "这是第一次对话。"
        
        gap_seconds = current_timestamp - self.last_timestamp
        
        # 拟人化的延迟感知逻辑
        if gap_seconds < 10:
            return "Instant_Reply", "秒回。用户非常关注这段对话，或者很急。"
        elif gap_seconds < 300: # 5分钟内
            return "Normal_Flow", "正常的对话节奏。"
        elif gap_seconds < 3600 * 6: # 6小时内
            return "Short_Break", "间隔了一小段时间。"
        elif gap_seconds < 3600 * 24 * 3: # 3天内
            return "Long_Break", "用户离开了较长时间。"
        else:
            return "Ghosting_Return", "用户消失了很久突然出现 (Ghosting)。"
        

# ------ L0 Tagger  ------

L0_Tagger_Prompt =   f"""
Task: Analyze the user's incoming message purely on 'Vibe' and 'Urgency'.
Input: "{{user_message}}"
Context: {{time_context}} {{latency_context}} 

Output format: JSON
{{
  "sentiment": "Anxious/Lonely", (One word summary)
  "urgency": "High", (Low/Medium/High)
  "intention_guess": "Seeking comfort", (Guess what they want before thinking deep)
  "safety_flag": false (Is this self-harm or toxic?)
}}
"""

class L0_Tagger:
    """ L0 Tagger 类，用于对用户消息进行标签化 """
    def __init__(self, client: OpenAI):
        self.client = client
        self.tagger_prompt_template = L0_Tagger_Prompt
    
    def construct_l0_tagger_prompt(self, user_message: str, time_context: str, latency_context: str) -> str:
        """ 构建 L0 Tagger 的完整 prompt """
        prompt = self.tagger_prompt_template.replace("{{user_message}}", user_message)
        prompt = prompt.replace("{{time_context}}", time_context)
        prompt = prompt.replace("{{latency_context}}", latency_context)
        return prompt    

    def tag_message(self, user_message: UserMessage, time_context: str, latency_context: str) -> dict:
        """ 调用 LLM 对用户消息进行标签化 """
        prompt = self.construct_l0_tagger_prompt(user_message.content, time_context, latency_context)
        
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are an expert L0 Tagger."},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        
        tag_output = response.choices[0].message.content
        
        if tag_output:
            tags = json.loads(tag_output)
        else:
            tags = {}
        
        return tags

# ------ L0 Instruction Generator ------

class TimeContext:
    LateNight: str = "当前是深夜，请保持语气柔和，避免过于激动的措辞。"
    Morning: str = "现在是清晨，语气可以轻松愉快一些。"
    WorkHours: str = "现在是工作时间，回复应简洁明了，专业。"
    Evening: str = "现在是晚上，可以稍微放松一些，语气友好。"
    
    def to_dict(self) -> dict:
        return {
            "LateNight": self.LateNight,
            "Morning": self.Morning,
            "WorkHours": self.WorkHours,
            "Evening": self.Evening
        }
    
class SentimentContext:
    Angry: str = "检测到用户有攻击性。请启动防御机制：不要回击，先尝试降温处理 (De-escalation)。"
    Sad: str = "检测到用户情绪低落。请表现出同理心，给予安慰和支持。"
    Happy: str = "检测到用户情绪高兴。请以积极和热情的语气回应，分享他们的喜悦。"
    
    def to_dict(self) -> dict:
        return {
            "Angry": self.Angry,
            "Sad": self.Sad,
            "Happy": self.Happy
        }

class UrgencyContext:
    High: str = "用户很着急，请直接给出简短的回应，不要废话。"
    Medium: str = "用户有一定的紧迫感，请尽量快速回应。"
    Low: str = "用户不急，请保持正常的回复节奏。"
    
    def to_dict(self) -> dict:
        return {
            "High": self.High,
            "Medium": self.Medium,
            "Low": self.Low
        }

class InstructionGenerator:
    """ 根据标签生成指令的类 """
    def __init__(self, time_context: TimeContext = TimeContext(), 
                 sentiment_context: SentimentContext = SentimentContext(), 
                 urgency_context: UrgencyContext = UrgencyContext()):
        self.time_context = time_context
        self.sentiment_context = sentiment_context
        self.urgency_context = urgency_context

    def get_instruction_from_tags(self, tags, time_context):
        """根据标签和时间上下文生成指令列表"""
        instructions = []

        # 1. 基于时间的硬规则
        if time_context == "Late_Night":
            instructions.append(self.time_context.LateNight)
        elif time_context == "Early_Morning":
            instructions.append(self.time_context.Morning)
        elif time_context == "Work_Hours":
            instructions.append(self.time_context.WorkHours)
        elif time_context == "Evening":
            instructions.append(self.time_context.Evening)
        # 2. 基于情绪标签的映射
        if tags.get("sentiment") == "Angry":
            instructions.append(self.sentiment_context.Angry)
        elif tags.get("sentiment") == "Sad":
            instructions.append(self.sentiment_context.Sad)
        elif tags.get("sentiment") == "Happy":
            instructions.append(self.sentiment_context.Happy)

        # 3. 基于紧迫感的映射
        if tags.get("urgency") == "High":
            instructions.append(self.urgency_context.High)
        elif tags.get("urgency") == "Medium":
            instructions.append(self.urgency_context.Medium)
        elif tags.get("urgency") == "Low":
            instructions.append(self.urgency_context.Low)
        return " ".join(instructions)

    def get_contexts_info(self) -> dict:
        return {
            "time_context": self.time_context.to_dict(),
            "sentiment_context": self.sentiment_context.to_dict(),
            "urgency_context": self.urgency_context.to_dict()
        }
    

#   发送给L1 的大概的 prompt 模板
#     prompt = f"""
#     [System]
#     ... (L3 核心人格设定) ...

#     [Conversation History]
#     ...

#     [Current Turn Input - L0 Sensory Data]
#     ------------------------------------------------
#     【物理感知】
#     - 当前时间: 02:15 (深夜 - 易感时刻)
#     - 回复节奏: 秒回 (间隔 5秒) - 用户似乎很渴望对话。

#     【直觉标签】(由 L0 Tagger 生成)
#     - 情绪色彩: 焦虑/孤独
#     - 预判意图: 寻求安慰
#     ------------------------------------------------
#     User Said: "我睡不着。"
#     ------------------------------------------------
#     (Instruction: 请结合上方的感知数据进行内心独白。注意：因为是深夜且秒回，你的反应应该更柔和且及时。)
# """

class L0_Output:
    """ L0 输出类，包含 Sensory Data、Tags 和 Instructions """
    def __init__(self, sensory_data: str, tags: dict, instructions: str):
        self.sensory_data = sensory_data
        self.tags = tags
        self.instructions = instructions
        
    def to_dict(self) -> dict:
        """将 L0 输出转换为字典格式"""
        return {
            "sensory_data": self.sensory_data,
            "tags": self.tags,
            "instructions": self.instructions
        }

class L0_Module:
    def __init__(self, client: OpenAI):
        self.user_messages = []
        
        # L0 Sensory Processor
        self.sensory_processor = L0_Sensory_Processor()
        
        # L0 Tagger
        self.tagger = L0_Tagger(client)
        
        # Instruction Generator
        self.instruction_generator = InstructionGenerator()

    def process_user_message(self, user_message: UserMessage) -> L0_Output:
        # 1. L0 Sensory Processing
        current_timestamp = datetime.now().timestamp()
        time_context, time_description = self.sensory_processor.analyze_time_context(current_timestamp)
        latency_context, latency_description = self.sensory_processor.analyze_latency(current_timestamp)
        sensory_prompt = (
            f"时间感知: {time_context} - {time_description}\n"
            f"延迟感知: {latency_context} - {latency_description}\n"
            "请基于以上感知调整你的回复风格和内容，使其更符合当前的时间和对话节奏。"
        )
        # 2. L0 Tagging
        tags = self.tagger.tag_message(user_message, time_context, latency_context)
        
        # 3. Instruction Generation
        instructions = self.instruction_generator.get_instruction_from_tags(tags, time_context)
        
        # 更新最后消息时间戳
        self.sensory_processor.last_timestamp = current_timestamp

        l0_output = L0_Output(sensory_prompt, tags, instructions)

        return l0_output

def test():
    from dotenv import load_dotenv
    load_dotenv()
    url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=url)
    l0 = L0_Module(client)
    print("----- Testing L0 Module -----")
    print("User Message Input: 我睡不着。")
    user_message = UserMessage("我睡不着。")
    x = l0.process_user_message(user_message)
    sensory_prompt, tags, instructions = x.sensory_data, x.tags, x.instructions
    print("Sensory Processor Output:")
    print(sensory_prompt)
    print("Tagger Output:")
    print(tags)
    print("Instruction Output:")
    print(instructions)


if __name__ == "__main__":
    test()
    