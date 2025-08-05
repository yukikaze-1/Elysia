from fastapi import HTTPException

from TokenManager import TokenManager

class TokenHandler:
    """Token管理处理器"""
    
    def __init__(self):
        self.token_manager = TokenManager()
    
    async def get_simple_token_stats(self):
        """获取简化的 token 统计信息"""
        stats = self.token_manager.get_current_stats()
        return {
            "local_tokens": stats["local_stats"]["total_tokens"],
            "cloud_tokens": stats["cloud_stats"]["total_tokens"],
            "total_tokens": stats["total_stats"]["total_tokens"],
            "session_local": stats["session_stats"]["local"]["total_tokens"],
            "session_cloud": stats["session_stats"]["cloud"]["total_tokens"],
            "session_total": stats["session_stats"]["total"]["total_tokens"],
        }
    
    async def reset_session_tokens(self):
        """重置会话 token 统计"""
        self.token_manager.reset_session_stats()
        return {"message": "Session token statistics reset successfully"}
    
    async def reset_all_tokens(self):
        """重置所有 token 统计"""
        self.token_manager.reset_all_stats()
        return {"message": "All token statistics reset successfully"}
    
    async def save_token_stats(self):
        """手动保存 token 统计数据"""
        self.token_manager.force_save()
        return {"message": "Token statistics saved successfully"}
    
    async def export_token_stats(self, export_name: str):
        """导出 token 统计数据"""
        if not export_name:
            raise HTTPException(status_code=400, detail="Export name is required")
        
        try:
            file_path = self.token_manager.export_stats(export_name)
            return {"message": f"Statistics exported to {file_path}", "file_path": file_path}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
