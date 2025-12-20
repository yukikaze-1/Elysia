"""
存放会话相关的数据结构和类
包括用户消息、聊天消息、会话状态等
    - ChatMessage 类表示单条聊天消息
    - SessionState 类表示当前会话的状态和历史
    - UserMessage 类表示用户输入的消息
    - InputEventInfo 类表示用户输入事件的相关信息
    - ConversationSegment 类表示一段对话片段
"""

import os

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
        # TODO user id 目前从环境变量读取，后续可能需要改为传参
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
        
    def to_str(self) -> str:
        return f"UserMessage(user_id={self.user_id}, content={self.content}, timestamp={self.client_timestamp}, input_event={self.input_event})"


from openai.types.chat import ChatCompletionMessage
import time

class ChatMessage:
    """聊天消息类，包含角色、内容、内心独白、时间戳等信息"""
    def __init__(self, role: str, content , inner_voice: str = "", timestamp: float = time.time()):
        self.role: str = role
        self.content = content
        self.inner_voice: str = inner_voice
        self.timestamp: float = timestamp
    
    @classmethod
    def from_ChatCompletionMessage(cls, message: ChatCompletionMessage, timestamp: int):
        return cls(role=message.role, 
                   content=message.content, 
                   inner_voice="",
                   timestamp=float(timestamp))
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "inner_voice":self.inner_voice,
            "timestamp": self.timestamp
        }
        
    def debug(self):
        print(self.to_dict())


class ConversationSegment:
    """对话片段类，表示一段时间内的对话消息集合"""
    def __init__(self, start_time: float, end_time: float, messages: list[ChatMessage]):
        self.messages: list[ChatMessage] = messages
        self.start_time: float = start_time
        self.end_time: float = end_time
        
    def format_messages_to_line(self):
        """ 格式化消息为行文本 """
        lines = []
        for msg in self.messages:
            lines.append(f'  {msg.role}: {msg.content}: {msg.timestamp}： {datetime.fromtimestamp(msg.timestamp)}')
        return "[\n" + "\n".join(lines) + "\n]"
    
    def debug(self):
        print("Conversaton Segement:")
        print(f"During:{self.start_time} to {self.end_time}.Contains {len(self.messages)} messages")
        print(self.format_messages_to_line())
        print()


from datetime import datetime
import time

class SessionState:
    """会话状态（包含当前聊天的部分上下文）"""
    def __init__(self, user_name: str, role: str, max_messages_limit: int = 20, max_inner_limit = 3):
        self.user_name: str = user_name     # 用户的名字
        self.role: str = role               # AI的名字
        
        self.max_messages_limit: int = max_messages_limit    # 最大对话数(含inner voice + 不含inner voice)
        self.max_inner_limit: int = max_inner_limit     # 最大包含inner voice的对话数
        
        self.conversations: list[ChatMessage] = []
        self.last_interaction_time: float = time.time()
        
        # TODO 下面这两项是否需要到单独拿出来作为一个“当前状态”的信息类？需要更新
        self.short_term_goals: str = "Just chatting"
        self.current_mood: str = "Neutral"


    def add_messages(self, messages: list[ChatMessage]):
        """ 添加消息到会话历史 """
        if messages is not None and len(messages) == 0:
            return
        for msg in messages:
            self.conversations.append(msg)
            
        self.update_last_interaction_time()
        
        if self.check_message_overflow():
            self.prune_history()
        
    def update_goal(self, goal: str):
        if not goal:
            print("Error! New goal is invalid!")
        self.short_term_goals = goal
        
    def update_mood(self, mood: str):
        if not mood:
            print("Error! New mood is invalid!")
        self.current_mood = mood
        
    def update_last_interaction_time(self)->float:
        """更新最后交互时间（以最后一条消息为准）"""
        if len(self.conversations) == 0 :
            print("Error, SessionSate has empty conversations!")
            return 0.0
        self.last_interaction_time = self.conversations[-1].timestamp
        return self.last_interaction_time
    
    def check_message_overflow(self)-> bool:
        """检查消息是否超出限制"""
        return len(self.conversations) > self.max_messages_limit
    
    def prune_history(self):
        """ 修剪历史消息，保留最近的消息，去掉较早的inner thought """
        # 假设 history 结构是 [msg1, msg2, msg3, ...]
        # 我们保留最近 max_messages_limit 条消息 (max_messages_limit/2 轮) 的完整内容
        # 对于更早的消息，只保留回复部分，去掉 Inner Thought
        # 对于非常老的消息，直接丢弃，保持总长度不超过 max_limits
        # TODO 待配套完善
        
        if len(self.conversations) <= self.max_messages_limit:
            return  # 不需要修剪
        
        # 丢弃老消息
        if len(self.conversations) > self.max_messages_limit:
            history = self.conversations[-self.max_messages_limit:]
        
        # 清洗inner thought
        threshold_index = len(history) - 2 * self.max_inner_limit
        if threshold_index > 0:
            for i in range(threshold_index):
                if history[i].role == self.role:
                    # 清洗掉 Inner Thought，只留 Reply
                    history[i].inner_voice = ""
                    
        self.conversations.clear()
        self.conversations = history
    
    
    def debug(self):
        print("-------------------- SessionState Debug Info --------------------")
        print(f"Time: {datetime.fromtimestamp(time.time())}")
        print(f"  Last Interaction Time: {self.last_interaction_time}")
        print(f"  Short Term Goals: {self.short_term_goals}")
        print(f"  Current Mood: {self.current_mood}")
        print("  Conversation History:")
        for msg in self.conversations:
            if msg.inner_voice == "":
                print(f"    {msg.role} at {msg.timestamp}: {msg.content}")
            else:
                print(f"    {msg.role} at {msg.timestamp}: {msg.content} \n \t \t(inner_voice): {msg.inner_voice}")

        print("-------------------- End of Debug Info --------------------")
