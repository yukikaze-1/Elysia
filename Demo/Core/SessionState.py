"""
会话状态管理模块
"""

import time
from datetime import datetime
import logging
import time
import threading
import os
import json
from Logger import setup_logger
from Core.Schema import ChatMessage
from Config import SessionStateConfig

class SessionState:
    """
    [内部辅助类] 会话状态管理
    负责维护 Context Window (上下文窗口)，确保发给 LLM 的 Token 不会溢出。
    """
    def __init__(self, config: SessionStateConfig):
        """
        初始化会话状态
        """
        self.config: SessionStateConfig = config
        
        self.logger: logging.Logger = setup_logger(self.config.logger_name)
        self.user_name: str = self.config.user_name     # 用户的名字
        self.role: str = self.config.role               # AI的名字
        
        if not os.path.exists(self.config.persist_dir):
            os.makedirs(self.config.persist_dir)
        self.file_path = os.path.join(self.config.persist_dir, f"{self.user_name}_{self.role}_history.json")
        
        self.max_messages_limit: int = self.config.session_capacity    # 最大对话数(含inner voice + 不含inner voice)
        self.max_inner_limit: int = self.config.inner_capacity    # 最大包含inner voice的对话数
        
        self.lock = threading.RLock()       # 线程锁，保护会话状态的并发访问
        self.conversations: list[ChatMessage] = []  # 会话历史
        self.last_interaction_time: float = time.time()  # 最后交互时间戳
        
        self._load_session()
        
    
    def get_status(self) -> dict:
        """获取当前会话状态的摘要信息"""
        status = {
            "user_name": self.user_name,
            "role": self.role,
            "max_messages_limit": self.max_messages_limit,
            "max_inner_limit": self.max_inner_limit,
            "total_messages": len(self.conversations),
            "last_interaction_time": self.last_interaction_time,
            "last_few_messages": [msg.to_dict() for msg in self.conversations[-10:]]  # 最近10条消息
        }
        return status

    
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
    
    
    def get_full_history(self)-> list[ChatMessage]:
        """ 返回完整的会话历史 """
        return self.conversations
    
    
    def get_recent_history(self, limit: int = 6) -> list[ChatMessage]:
        """获取最近几条"""
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