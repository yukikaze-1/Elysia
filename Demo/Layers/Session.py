"""
存放会话相关的数据结构和类
包括用户消息、聊天消息、会话状态等
    - ChatMessage 类表示单条聊天消息
    - SessionState 类表示当前会话的状态和历史
    - UserMessage 类表示用户输入的消息
    - InputEventInfo 类表示用户输入事件的相关信息
    - ConversationSegment 类表示一段对话片段
"""

import time
from datetime import datetime
import logging
from Demo.Logger import setup_logger

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
    def __init__(self, role: str, content: str, timestamp: float | None = None):
        self.role: str= role
        self.content: str = content
        self.client_timestamp: float = timestamp if timestamp else time.time()
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
        return f"UserMessage(role={self.role}, content={self.content}, timestamp={self.client_timestamp}, input_event={self.input_event})"


from openai.types.chat import ChatCompletionMessage
import time

class ChatMessage:
    """聊天消息类，包含角色、内容、内心独白、时间戳等信息"""
    def __init__(self, role: str, content , inner_voice: str , timestamp: float | None = None):
        self.role: str = role
        self.content = content
        self.inner_voice: str = inner_voice
        self.timestamp: float = timestamp if timestamp else time.time()
    
    @classmethod
    def from_ChatCompletionMessage(cls, message: ChatCompletionMessage, timestamp: int):
        return cls(role=message.role, 
                   content=message.content, 
                   inner_voice="",
                   timestamp=float(timestamp))
    
    @classmethod
    def from_UserMessage(cls, user_message: UserMessage):
        return cls(role=user_message.role,
                   content=user_message.content,
                   inner_voice="",
                   timestamp=user_message.client_timestamp)
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "inner_voice":self.inner_voice,
            "timestamp": self.timestamp
        }
    
    @classmethod    
    def from_dict(cls, data: dict):
        """ 从字典加载数据 """
        return cls(
            role=data.get("role", ""),
            content=data.get("content", ""),
            inner_voice=data.get("inner_voice", ""),
            timestamp=data.get("timestamp", time.time())
        )
        
        
    def debug(self, logger: logging.Logger):
        logger.info(self.to_dict())


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
    
    def debug(self, logger: logging.Logger):
        logger.info("Conversaton Segement:")
        logger.info(f"During:{self.start_time} to {self.end_time}.Contains {len(self.messages)} messages")
        logger.info("Conversaton Segement:" + self.format_messages_to_line())
        


from datetime import datetime
import time
import threading
import os
import json

class SessionState:
    """
    [内部辅助类] 会话状态管理
    负责维护 Context Window (上下文窗口)，确保发给 LLM 的 Token 不会溢出。
    """
    def __init__(self, 
                 user_name: str, 
                 role: str, 
                 max_messages_limit: int = 20, 
                 max_inner_limit = 3,
                 persist_dir: str = "./storage/sessions"):
        """
        初始化会话状态
        Args:
            user_name (str): 用户名称
            role (str): AI 角色名称
            max_messages_limit (int): 最大消息数限制
            max_inner_limit (int): 最大包含内心独白的消息数限制
            persist_dir (str): 会话持久化存储目录
        """

        self.logger: logging.Logger = setup_logger("SessionState")
        self.user_name: str = user_name     # 用户的名字
        self.role: str = role               # AI的名字
        
        if not os.path.exists(persist_dir):
            os.makedirs(persist_dir)
        self.file_path = os.path.join(persist_dir, f"{user_name}_{role}_history.json")
        
        self.max_messages_limit: int = max_messages_limit    # 最大对话数(含inner voice + 不含inner voice)
        self.max_inner_limit: int = max_inner_limit     # 最大包含inner voice的对话数
        
        self.lock = threading.RLock()       # 线程锁，保护会话状态的并发访问
        self.conversations: list[ChatMessage] = []  # 会话历史
        self.last_interaction_time: float = time.time()  # 最后交互时间戳
        
        self._load_session()

    
    def add_messages(self, messages: list[ChatMessage]):
        """ 添加消息到会话历史 """
        if messages is not None and len(messages) == 0:
            self.logger.warning("Attempted to add empty message list to SessionState.")
            return
        
        # 添加消息
        for msg in messages:
            # 仅添加有效消息
            if self.check_message_valid(msg):
                self.conversations.append(msg)
                self.logger.debug(f"Added message to SessionState: {msg.to_dict()}")
            else:
                self.logger.warning(f"Invalid message not added to SessionState: {msg.to_dict()}")
        
        # 更新最后交互时间
        self.update_last_interaction_time()
        self.logger.info(f"Added {len(messages)} messages to SessionState. Total messages now: {len(self.conversations)}")
        
        # 检查是否超出限制，若超出则修剪
        if self.check_message_overflow():
            self.logger.info("Message overflow detected. Pruning history.")
            self.prune_history()
    
    
    def get_history(self)-> list[ChatMessage]:
        return self.conversations
    
    
    def get_recent_items(self, limit: int = 6) -> list[ChatMessage]:
        """获取最近几条，用于主动性判断"""
        subset = self.conversations[-limit:]
        return subset
    
        
    def update_last_interaction_time(self)->float:
        """更新最后交互时间（以最后一条消息为准）"""
        if len(self.conversations) == 0 :
            self.logger.error("No conversations in SessionState when updating last interaction time.")
            return 0.0
        
        self.last_interaction_time = self.conversations[-1].timestamp
        return self.last_interaction_time
    
    
    def check_message_overflow(self)-> bool:
        """检查消息是否超出限制"""
        return len(self.conversations) > self.max_messages_limit
    
    
    def check_message_valid(self, message: ChatMessage) -> bool:
        """检查消息是否有效"""
        # 检查内容非空
        if not message.content or message.content.strip() == "":
            self.logger.warning("Invalid message content.")
            return False
        # 检查角色是否和预期一致
        if message.role not in [self.user_name, self.role]:
            self.logger.warning(f"Invalid message role: {message.role}. Expected: {self.user_name} or {self.role}.")
            return False
        return True
    
    
    def prune_history(self):
        """ 修剪历史消息，保留最近的消息，去掉较早的inner thought """
        # 假设 history 结构是 [msg1, msg2, msg3, ...]
        # 我们保留最近 max_messages_limit 条消息 (max_messages_limit/2 轮) 的完整内容
        # 对于更早的消息，只保留回复部分，去掉 Inner Thought
        # 对于非常老的消息，直接丢弃，保持总长度不超过 max_limits
        # TODO 待配套完善
        
        if len(self.conversations) <= self.max_messages_limit:
            self.logger.info("No need to prune history.")
            return  # 不需要修剪
        
        # 丢弃老消息
        if len(self.conversations) > self.max_messages_limit:
            history = self.conversations[-self.max_messages_limit:]
            self.logger.info(f"Pruned history to last {self.max_messages_limit} messages.")
        
        # 清洗inner thought
        threshold_index = len(history) - 2 * self.max_inner_limit
        if threshold_index > 0:
            for i in range(threshold_index):
                if history[i].role == self.role:
                    # 清洗掉 Inner Thought，只留 Reply
                    history[i].inner_voice = ""
                    
        self.conversations.clear()
        self.conversations = history
        self.logger.info("Cleaned inner thoughts from older messages.")
        
    
    def _load_session(self):
        """从文件加载会话历史"""
        if not os.path.exists(self.file_path):
            self.logger.info(f"No history file found at {self.file_path}, starting new session.")
            return

        try:
            with self.lock: # 读锁
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 恢复时间戳
                self.last_interaction_time = data.get("last_interaction_time", 0.0)
                
                # 恢复消息列表
                raw_msgs = data.get("conversations", [])
                self.conversations = [ChatMessage.from_dict(msg) for msg in raw_msgs]
                
            self.logger.info(f"Loaded {len(self.conversations)} messages from history.")
            
        except Exception as e:
            self.logger.error(f"Failed to load session: {e}")
            # 如果加载失败（文件损坏），选择重置还是保留空列表视业务而定
            self.conversations = []
    
    
    def _save_session(self):
        """将当前会话保存到文件"""
        try:
            # 准备数据
            serialized_msgs = [msg.to_dict() for msg in self.conversations] 
            
            data = {
                "last_interaction_time": self.last_interaction_time,
                "conversations": serialized_msgs
            }

            with self.lock: # 写锁
                # 使用临时文件写入再重命名的方式（Atomic Write），防止写入中途断电导致文件损坏
                temp_file = self.file_path + ".tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # 覆盖原文件
                if os.path.exists(self.file_path):
                    os.replace(temp_file, self.file_path)
                else:
                    os.rename(temp_file, self.file_path)
                    
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
    
    
    def debug(self):
        self.logger.info("-------------------- SessionState Debug Info --------------------")
        self.logger.info(f"Time: {datetime.fromtimestamp(time.time())}")
        self.logger.info(f"  Last Interaction Time: {self.last_interaction_time}")
        self.logger.info("  Conversation History:")
        for msg in self.conversations:
            if msg.inner_voice == "":
                self.logger.info(f"    {msg.role} at {msg.timestamp}: {msg.content}")
            else:
                self.logger.info(f"    {msg.role} at {msg.timestamp}: {msg.content} \n \t \t(inner_voice): {msg.inner_voice}")

        self.logger.info("-------------------- End of Debug Info --------------------")