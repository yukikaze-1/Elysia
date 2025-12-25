import asyncio
import json
from typing import List
from fastapi import WebSocket
from Core.OutputChannel import OutputChannel
from Layers.Session import  ChatMessage

class ConnectionManager(OutputChannel):
    """
    既是 WebSocket 管理器，也是 L0 的一个 OutputChannel。
    负责解决 Sync (L0) -> Async (FastAPI) 的调用问题。
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.loop = None # 将在 FastAPI 启动时获取主事件循环

    def set_loop(self, loop):
        """捕获 FastAPI 的事件循环"""
        self.loop = loop

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[Server] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print("[Server] Client disconnected.")

    # === 实现 OutputChannel 接口 (被 L0 线程调用) ===
    def send_message(self, msg: ChatMessage):
        """
        这是从 Agent 线程调用的。
        必须使用 run_coroutine_threadsafe 将任务扔回 FastAPI 的主循环。
        """
        if self.loop and self.active_connections:
            # 这里的 _broadcast_async 是协程，不能直接调用
            asyncio.run_coroutine_threadsafe(
                self._broadcast_async(msg), 
                self.loop
            )

    async def _broadcast_async(self, message: ChatMessage):
        """实际的异步发送逻辑"""
        # 复制一份列表防止发送时连接断开导致的迭代错误
        for connection in self.active_connections[:]:
            try:
                json_str = json.dumps(message.to_dict(), ensure_ascii=False)
                await connection.send_text(json_str)
            except Exception as e:
                print(f"Send error: {e}")
                self.disconnect(connection)