"""
定义输出通道的接口和示例实现
"""

import sys
from datetime import datetime
from Demo.Layers.Session import  ChatMessage
from Demo.Logger import setup_logger
from abc import ABC, abstractmethod


class OutputChannel(ABC):
    """输出通道接口"""
    @abstractmethod
    def send_message(self, msg: ChatMessage):
        pass


class ConsoleChannel(OutputChannel):
    """控制台输出通道"""
    def __init__(self):
        self.logger = setup_logger("ConsoleChannel")
        
    def send_message(self, msg: ChatMessage):
        """
        [接口实现] 简单的控制台打印
        """
        # 同时记录日志
        public_reply: str = msg.content
        inner_thought: str = msg.inner_voice if msg.inner_voice else ""
        timestamp: str = datetime.fromtimestamp(msg.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        
        # 使用颜色区分 AI 和用户的发言 (例如：绿色)
        GREEN = "\033[92m"
        YELLOW = "\033[93m"
        RESET = "\033[0m"
        
        # 打印 formatted output
        print(f"\n{GREEN}[{msg.role} @ {timestamp}]: {public_reply}{RESET}")
        self.logger.info(f"{msg.role} Public Reply: {public_reply}")
        
        if msg.role == "Elysia" and inner_thought:
            print(f"{YELLOW}(Inner Thought): {inner_thought}{RESET}\n")
            self.logger.info(f"{msg.role} Inner Thought: {inner_thought}")
        
        # 强制刷新缓冲区，确保字立刻显示出来
        sys.stdout.flush()
        
        
        
class WebSocketChannel(OutputChannel):
    """WebSocket 输出通道"""
    def __init__(self, websocket):
        self.websocket = websocket
    
    def send_message(self, msg: ChatMessage):
        # 假设 websocket 有一个 send 方法
        # TODO 待实现
        self.websocket.push_message(msg)
        
        
