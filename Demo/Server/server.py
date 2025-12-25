import asyncio
from math import e
import threading
from contextlib import asynccontextmanager
from typing import Optional
import json

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# === 引入你的 Agent 核心组件 ===
from Demo.Core.EventBus import EventBus, Event, global_event_bus
from Demo.Core.Dispatcher import Dispatcher
from Demo.Core.Schema import EventType, EventContentType, EventSource, UserMessage
from Demo.Layers.L0.L0 import SensorLayer
from Demo.Layers.L1 import BrainLayer
from Demo.Layers.L2 import MemoryLayer
from Demo.Layers.L3 import PersonaLayer
from Demo.Layers.Actuator.ActuatorLayer import ActuatorLayer, ActionType
from Demo.Workers.Reflector.Reflector import Reflector
from Demo.Server.ConnectionManager import ConnectionManager
from Demo.Logger import setup_logger


class ElysiaServer:
    def __init__(self):
        self.logger = setup_logger("ElysiaServer")
        # 1. 初始化核心组件 (但不启动线程)
        self.bus: EventBus = global_event_bus
        self.manager = ConnectionManager()
        
        # 初始化层级
        self.l0 = SensorLayer(event_bus=self.bus)
        self.l1 = BrainLayer()
        self.l2 = MemoryLayer()
        self.l3 = PersonaLayer()
        self.reflector = Reflector(event_bus=self.bus)
        self.actuator = ActuatorLayer(event_bus=self.bus)
        
        # 初始化调度器
        self.dispatcher = Dispatcher(
            self.bus, self.l0, self.l1, self.l2, self.l3, self.actuator, self.reflector, 
        )

        # 线程句柄
        self.dispatcher_thread: Optional[threading.Thread] = None   # Dispatcher 线程句柄

        # 2. 初始化 FastAPI App
        # 注意：这里将 self.lifespan 传递给 FastAPI
        self.app = FastAPI(lifespan=self.lifespan)
        
        # 3. 配置中间件和路由
        self._setup_middleware()
        self._setup_routes()

    def _setup_middleware(self):
        """配置跨域等中间件"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )


    def _setup_routes(self):
        """注册路由"""
        # 注意：这里直接绑定类的方法
        self.app.get("/")(self.root)
        self.app.websocket("/ws")(self.websocket_endpoint)


    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """生命周期管理：处理 Agent 的启动和关闭"""
        # --- Startup ---
        self.logger.info(">>> [System] Elysia Server Starting...")

        # 1. 获取 EventLoop 并注入给 ConnectionManager
        try:
            loop = asyncio.get_running_loop()
            self.manager.set_loop(loop)
        except RuntimeError:
            self.logger.warning(">>> [Warning] No running event loop found for ConnectionManager.")

        # 2. 关键：将 WebSocket 管理器注册为 Actuator 的输出通道 (嘴巴)
        self.actuator.add_channel(self.manager)

        # 3. 启动各个组件的线程
        self.logger.info(">>> [System] Starting Layer Threads...")
        self.l0.start_threads()  # L0 心跳/监听
        self.reflector.start()   # 反思者

        # 4. 启动 Dispatcher (独立线程)
        self.logger.info(">>> [System] Starting Dispatcher...")
        self.dispatcher_thread = threading.Thread(target=self.dispatcher.start, daemon=True)
        self.dispatcher_thread.start()

        self.logger.info(">>> [System] Elysia Agent is Ready & Listening.")
        
        yield  # 服务运行中...

        # --- Shutdown ---
        self.logger.info(">>> [System] Shutting down Elysia Agent...")
        
        # 停止组件
        if self.dispatcher:
            self.dispatcher.stop()
        
        if self.l0:
            self.l0.stop_threads()
            
        if self.reflector:
            self.reflector.stop()
            
        self.logger.info(">>> [System] Shutdown Complete.")

    # === Route Handlers ===

    async def root(self):
        return {
            "status": "Elysia Agent is Running", 
            "agency": "Active",
            "components": {
                "l0": "Online",
                "dispatcher": "Running" if self.dispatcher_thread and self.dispatcher_thread.is_alive() else "Stopped"
            }
        }


    async def websocket_endpoint(self, websocket: WebSocket):
        """WebSocket 连接处理"""
        await self.manager.connect(websocket)
        try:
            while True:
                # 1. 接收前端消息 (异步等待)
                data = await websocket.receive_text()
                self.logger.debug(f"[WebSocket] Received: {data}")  
                
                # 2. 解析消息
                parsed_data: dict = self._parse_websocket_message(data)
                  
                # 3. 标记来源
                parsed_data['source'] = 'websocket'  
                
                # 4. 推送到 L0 输入队列
                self.l0.push_external_input(parsed_data)
                
        except WebSocketDisconnect:
            self.logger.info(f"[WebSocket] Client disconnected")
            self.manager.disconnect(websocket)
        except Exception as e:
            self.logger.error(f"[WebSocket] Error: {e}")
            # 可以在这里决定是否要断开连接或者仅仅记录错误
            
            
    def _parse_websocket_message(self, data: str) -> dict:
        """解析来自 WebSocket 的消息"""
        # 这里假设前端发送的是 JSON 格式
        import json
        try:
            parsed = json.loads(data)
            return parsed
        except json.JSONDecodeError as e:
            self.logger.error(f"WebSocket message parsing error: {e}")
            return {}
            
    def run(self):
        """运行 FastAPI 应用"""
        uvicorn.run(self.app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    elysia = ElysiaServer()
    elysia.run()
        
        