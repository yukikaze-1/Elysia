import uvicorn
import httpx
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from openai.types.chat import ChatCompletionMessageParam
from typing import Dict, List, Any, Tuple

from langchain.memory import ConversationBufferMemory, ConversationTokenBufferMemory, ConversationSummaryMemory, ConversationSummaryBufferMemory
from langchain_core.runnables import RunnableWithMessageHistory, RunnableConfig
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from HistoryManager import HistoryManager
from ServiceConfig import ServiceConfig
from RAG import RAG

from TokenHandler import TokenHandler
from ChatHandler import ChatHandler


    
class Service:
    """
    Elysia 聊天服务主类
    """
    def __init__(self):
        print("=== Service 初始化开始 ===")
        
        self.app = FastAPI()
        self.config = ServiceConfig()
        
        print("=== RAG初始化开始 ===")
        # self.rag = RAG()
        print("✓ RAG 初始化跳过")
        
        print("=== ChatHandler 初始化开始 ===")
        self.chat_handler = ChatHandler(self.config)
        print("✓ ChatHandler 初始化完成")

        print("=== TokenHandler 初始化开始 ===")
        self.token_handler = TokenHandler()
        print("✓ TokenHandler 初始化完成")
        
        self._global_history = self.chat_handler.global_history  # 引用同一个实例
        self.history_manager = HistoryManager(self._global_history)
        
        # 6. 预热检查
        print("正在进行预热检查...")
        self._warmup_check()

        print("=== Service 初始化完成 ===")
           
    
    def _warmup_check(self):
        """预热检查 - 确保所有组件正常工作"""
        try:
            # 检查聊天历史
            message_count = len(self._global_history.messages)
            print(f"  - 聊天历史: {message_count} 条消息")
            
            # 检查 Token 管理器
            stats = self.token_handler.token_manager.get_current_stats()
            print(f"  - Token 统计: 总计 {stats['total_stats']['total_tokens']} tokens")
            
            print("✓ 预热检查完成")
            
        except Exception as e:
            print(f"✗ 预热检查失败: {e}")    
            
    
    async def check_memory_status(self, session_id=None)->List[str]:
        """检查记忆状态 - session_id 参数被忽略"""
        return await self.history_manager.get_formatted_history()
          

    # =========================
    # Token 管理相关处理方法 - 已迁移到 TokenHandler
    # =========================
    # 所有 Token 管理相关的方法已经迁移到 TokenHandler 类中
    # 使用 self.token_handler 进行调用
    
    # =========================
    # 历史记录管理相关处理方法 - 已迁移到 HistoryManager
    # =========================
    # 所有历史记录相关的方法已经迁移到 HistoryManager 类中
    # 使用 self.history_manager 进行调用
    
    def setup_routes(self):
        """设置 API 路由"""
        
        # =========================
        # 基础服务路由
        # =========================
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy"}

        # =========================
        # 聊天功能路由
        # =========================
        @self.app.post("/chat/stream_text")
        async def chat_stream_local(request: Request):
            data = await request.json()
            message = data.get("message", "")
            if not message:
                raise HTTPException(status_code=400, detail="Message is required")
            return await self.chat_handler.handle_local_chat_stream(message)
        
        @self.app.post("/chat/stream_text_cloud")
        async def chat_stream_cloud(request: Request):
            data = await request.json()
            message = data.get("message", "")
            if not message:
                raise HTTPException(status_code=400, detail="Message is required")
            return await self.chat_handler.handle_cloud_chat_stream(message)
        
        
        # =========================
        # Token 管理路由
        # =========================
        @self.app.get("/chat/token_stats")
        async def get_token_stats():
            return self.token_handler.token_manager.get_current_stats()
        
        @self.app.get("/chat/token_stats/simple")
        async def get_simple_token_stats():
            return await self.token_handler.get_simple_token_stats()

        @self.app.post("/chat/reset_session_tokens")
        async def reset_session_tokens():
            return await self.token_handler.reset_session_tokens()
        
        @self.app.post("/chat/reset_all_tokens")
        async def reset_all_tokens():
            return await self.token_handler.reset_all_tokens()
        
        @self.app.post("/chat/save_token_stats")
        async def save_token_stats():
            return await self.token_handler.save_token_stats()
        
        @self.app.post("/chat/export_token_stats")
        async def export_token_stats(export_name: str):
            return await self.token_handler.export_token_stats(export_name)
        
        # =========================
        # 历史记录管理路由 
        # =========================
        @self.app.get("/chat/show_history")
        async def show_history(request: Request):
            session_id = request.query_params.get("session_id", "default")
            return await self.check_memory_status(session_id)
        
        @self.app.post("/chat/clear_history")
        async def clear_chat_history():
            return await self.history_manager.clear_history()
        
        @self.app.get("/chat/history_stats")
        async def get_history_stats():
            return await self.history_manager.get_stats()
        
        @self.app.post("/chat/backup_history")
        async def backup_chat_history():
            return await self.history_manager.backup_history()
        
        @self.app.post("/chat/reload_history")
        async def reload_chat_history():
            return await self.history_manager.reload_history()
              
   
    def run(self):
        """运行 FastAPI 应用"""
        self.setup_routes()
        uvicorn.run(self.app, host=self.config.host, port=self.config.port)
        print(f"Service is running on http://{self.config.host}:{self.config.port}")
        
        
        
if __name__ == "__main__":
    service = Service()
    service.run()

