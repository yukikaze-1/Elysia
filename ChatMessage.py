from datetime import datetime
from pathlib import Path
from typing import List
from unittest.util import strclass

"""
    对话消息类，最简单的形式，待扩充
"""

class AttachmentFile:
    """ ChatMessage 附件类，表示单个文件附件 """
    def __init__(self, file_path: Path, file_type: str, file_size: int):
        self.file_path: Path = file_path
        self.file_type: str = file_type
        self.file_size: int = file_size
        
    def __repr__(self):
        return f"AttachmentFile(file_path={self.file_path}, file_type={self.file_type}, file_size={self.file_size})"
    
    def __dict__(self):
        return {
            "file_path": str(self.file_path),
            "file_type": self.file_type,
            "file_size": self.file_size
        }

    def is_valid(self) -> bool:
        return self.file_path.exists() and self.file_path.is_file() and self.file_size > 0
    
    def get_file_info(self) -> str:
        return f"File: {self.file_path.name}, Type: {self.file_type}, Size: {self.file_size} bytes"

    def size(self) -> int:
        return self.file_size
    
    def type(self) -> str:
        return self.file_type
    
    def path(self) -> str:
        return str(self.file_path)
    


class MessageAttachment:
    """ ChatMessage 附件集合类，表示多个文件附件 """
    def __init__(self):
        self.files: List[AttachmentFile] = []

    def __repr__(self):
        return f"MessageAttachment(files={self.files})"
    
    def len(self) -> int:
        return len(self.files)

    def add_file(self, filepath: str):
        file_path: Path = Path(filepath)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"File does not exist: {file_path}")
        
        file_attachment = AttachmentFile(file_path, file_path.suffix, file_path.stat().st_size)
        
        if file_attachment.is_valid():
            self.files.append(file_attachment)
        else:
            raise ValueError(f"Invalid file attachment: {file_path}")
        
    def get_files(self) -> List[AttachmentFile]:
        return self.files
    
    def remove_file(self, file_path: str):
        """逻辑删除"""
        self.files = [f for f in self.files if f.file_path != Path(file_path)]
        
    def clear(self):
        self.files.clear()        
        

class ChatMessage:
    def __init__(self, role: str, content: str, 
                 message_id: int,
                 timestamp: str = datetime.now().strftime("%Y_%m_%d %H:%M:%S"),
                 attachments: MessageAttachment | None = None):
        """
        :param role: 消息角色
        :param content: 消息内容
        :param timestamp: 消息发送时间
        """
        self.role: str = role
        self.content: str = content
        self.timestamp: str = timestamp
        self.message_id: int = message_id
        self.attachments: MessageAttachment | None = attachments  # 附件列表

    def __repr__(self):
        return self.to_dict().__repr__()

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id
        }
        





