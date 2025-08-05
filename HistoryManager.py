import json
import os
from datetime import datetime
from typing import List, Dict, Any
from PersistentChatHistory import GlobalChatMessageHistory
from fastapi import HTTPException


class HistoryManager:
    """历史记录管理器 - 统一管理聊天历史的各种操作"""
    
    def __init__(self, global_history: GlobalChatMessageHistory):
        self.global_history = global_history
        self.backup_dir = "/home/yomu/Elysia/chat_history_backup"
        
        # 确保备份目录存在
        os.makedirs(self.backup_dir, exist_ok=True)
    
    async def clear_history(self) -> Dict[str, Any]:
        """清除所有聊天历史记录"""
        try:
            current_count = len(self.global_history.messages)
            self.global_history.clear()
            remaining_count = len(self.global_history.messages)
            
            return {
                "message": "Chat history cleared successfully",
                "details": {
                    "cleared_messages": current_count,
                    "remaining_messages": remaining_count,
                    "memory_cleared": True,
                    "milvus_cleared": True
                }
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to clear chat history: {str(e)}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取历史记录统计信息"""
        try:
            message_count = len(self.global_history.messages)
            human_count = sum(1 for msg in self.global_history.messages if msg.type == "human")
            ai_count = sum(1 for msg in self.global_history.messages if msg.type == "ai")
            
            return {
                "total_messages": message_count,
                "human_messages": human_count,
                "ai_messages": ai_count,
                "session_id": self.global_history.session_id,
                "collection_name": self.global_history.collection_name
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get history stats: {str(e)}")
    
    async def backup_history(self) -> Dict[str, Any]:
        """备份当前聊天历史到文件"""
        try:
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.global_history.session_id,
                "message_count": len(self.global_history.messages),
                "messages": []
            }
            
            for i, msg in enumerate(self.global_history.messages):
                backup_data["messages"].append({
                    "index": i + 1,
                    "type": msg.type,
                    "content": str(msg.content),
                    "timestamp": datetime.now().isoformat()
                })
            
            backup_filename = f"chat_history_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            return {
                "message": "Chat history backed up successfully",
                "backup_file": backup_path,
                "message_count": backup_data["message_count"]
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to backup chat history: {str(e)}")
    
    async def reload_history(self) -> Dict[str, Any]:
        """重新从Milvus加载聊天历史到内存"""
        try:
            old_count = len(self.global_history.messages)
            new_count = self.global_history.reload_from_db()
            
            return {
                "message": "Chat history reloaded successfully",
                "old_count": old_count,
                "new_count": new_count
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to reload chat history: {str(e)}")
    
    async def get_formatted_history(self) -> List[str]:
        """获取格式化的历史记录列表"""
        messages = self.global_history.messages
        res = []
        
        type_mapping = {
            "human": "魂魄妖梦",
            "ai": "爱莉希雅", 
            "system": "系统",
            "AIMessageChunk": "爱莉希雅",
        }
        
        for i, msg in enumerate(messages):
            display_type = type_mapping.get(msg.type, msg.type)
            formatted_msg = f"{i+1}. {display_type}: {msg.content}"
            res.append(formatted_msg)
        
        return res
