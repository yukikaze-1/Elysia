from typing import Dict, Any, Optional, List
from enum import Enum, StrEnum
from dataclasses import dataclass, field, asdict
import time

class MessageType(StrEnum):
    TEXT = "text"
    AUDIO = "audio"      # 纯音频输入 (STT源)
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    MIXED = "mixed"      # 混合内容
    
    
@dataclass
class AudioData:
    """音频数据封装 (用于 TTS 输出或 STT 输入)"""
    file_path: str           # 本地路径或 S3 key
    url: Optional[str] = None # 用于前端播放的 HTTP URL
    duration: Optional[float] = None # 时长(秒)
    format: str = "wav"      # mp3, wav, pcm
    transcript: str = ""     # 如果是 STT，这里存识别出的原文；如果是 TTS，这里存朗读的文本
    voice_id: str = ""       # 使用的音色 ID
    
    
@dataclass
class VideoData:
    """视频数据封装"""
    file_path: str           # 本地路径或 S3 key
    url: Optional[str] = None # 用于前端播放的 HTTP URL
    duration: Optional[float] = None # 时长(秒)
    format: str = "mp4"      # mp4, avi, mov
    width: Optional[int] = None
    height: Optional[int] = None
    
    
@dataclass
class ImageData:
    """图片数据封装"""
    source: str              # URL 或 Base64 或 本地路径
    detail: str = "auto"     # low, high, auto (OpenAI 格式专用)
    width: Optional[int] = None
    height: Optional[int] = None
    mime_type: str = "image/png"  # image/png, image/jpeg 等
    
    
@dataclass
class FileData:
    """通用文件封装 (PDF, Docx 等)"""
    file_name: str
    file_path: str
    file_size: int
    mime_type: str

from openai.types.chat import ChatCompletionMessage    
from core.Schema import UserMessage
import logging

@dataclass
class ChatMessage:
    role: str   # 角色名字,如"Elysia", "妖梦"
    content: str  # 核心文本内容 (STT的结果、TTS的输入、LLM的回复)
    inner_voice: str = ""      
    timestamp: float = field(default_factory=time.time)
    
    type: MessageType = MessageType.TEXT    # 消息类型
    
    images: List[ImageData] = field(default_factory=list)   # 图片列表
    files: List[FileData] = field(default_factory=list)     # 文件列表
    
    audio: Optional[AudioData] = None      # 音频数据
    video: Optional[VideoData] = None      # 视频数据
    
    metadata: Dict[str, Any] = field(default_factory=dict)      # --- 元数据 (扩展用，比如 token 消耗、模型名称) ---


    @property
    def is_multimodal(self) -> bool:
        return bool(self.images or self.files or self.audio or self.video)

    def to_dict(self) -> dict:
        return asdict(self)
    
    def debug(self, logger: logging.Logger):
        logger.info(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: dict):
        # 这里需要手写反序列化逻辑，或者使用 dacite/pydantic 自动处理
        # 为保持简洁，这里仅展示逻辑思路
        instance = cls(
            role=data.get("role", ""),
            content=data.get("content", ""),
            inner_voice=data.get("inner_voice", ""),
            timestamp=data.get("timestamp", time.time()),
            type=MessageType(data.get("type", "text"))
        )
        # TODO 需补充 images/audio 的对象重建逻辑...
        return instance

    
    @classmethod
    def from_ChatCompletionMessage(cls, message: ChatCompletionMessage, timestamp: int):
        """TODO 待完善"""
        return cls(role=message.role, 
                   content=message.content if message.content else "", 
                   inner_voice="",
                   timestamp=float(timestamp),
                   type=MessageType.TEXT)
        
        
    @classmethod
    def from_UserMessage(cls, user_message: UserMessage):
        """TODO 待完善"""
        return cls(role=user_message.role,
                   content=user_message.content,
                   inner_voice="",
                   timestamp=user_message.client_timestamp)
        
        
    # --- 针对 LLM API 的适配方法 ---
    # def to_openai_format(self):
    #     """转换为 OpenAI API 需要的格式"""
    #     if not self.images:
    #         return {"role": self.role, "content": self.content}
        
    #     # 多模态格式构造
    #     content_list: list = [{"type": "text", "text": self.content}]
    #     for img in self.images:
    #         content_list.append({
    #             "type": "image_url",
    #             "image_url": {"url": img.source, "detail": img.detail}
    #         })
    #     return {"role": self.role, "content": content_list}