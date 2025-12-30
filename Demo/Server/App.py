"""
Elysia Server 主程序入口 (FastAPI 版本)单机版本见 Demo/main.py
负责初始化各个组件并启动 FastAPI 服务
"""
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
from Core.EventBus import EventBus, Event
from Core.Dispatcher import Dispatcher
from Core.Schema import EventType, EventContentType, EventSource, UserMessage, L0InputSourceType
from Layers.L0.L0 import SensorLayer
from Layers.PsycheSystem import PsycheConfig, EnvironmentalStimuli, InternalState, PsycheSystem
from Layers.L1 import BrainLayer
from Layers.L2.L2 import MemoryLayer
from Layers.L3 import PersonaLayer
from Core.ActuatorLayer import ActuatorLayer, ActionType
from Core.SystemClock import SystemClock
from Workers.Reflector.Reflector import Reflector
from Server.ConnectionManager import ConnectionManager
from Logger import setup_logger
from Core.SessionState import SessionState
from Core.CheckPointManager import CheckpointManager

from Config import GlobalConfig

class ElysiaServer:
    def __init__(self, config: GlobalConfig):
        """
        初始化 Elysia Server 及其组件
        :param config: 全局配置对象
        """
        self.config: GlobalConfig = config
        
        self.logger = setup_logger(self.config.Server.App.logger_name)
        # 初始化uvicorn配置参数
        self.host = self.config.Server.App.host
        self.port = self.config.Server.App.port
        self.log_level = self.config.Server.App.log_level
        
        # 1. 初始化核心组件 (但不启动线程)
        self.checkpoint_manager = CheckpointManager(config=self.config.Core.CheckPointManager)
        self.bus: EventBus = EventBus(logger_name=self.config.Core.EventBus.logger_name)    # 全局事件总线
        self.manager = ConnectionManager()
        self.clock = SystemClock(event_bus=self.bus, config=self.config.Core.SystemClock)
        self.session = SessionState(config=self.config.Core.SessionState)
        
        
        # 初始化层级
        self.l0 = SensorLayer(event_bus=self.bus, config=self.config.L0)
        self.l1 = BrainLayer(config=self.config.L1)
        self.l2 = MemoryLayer(config=self.config.L2)
        self.l3 = PersonaLayer(config=self.config.L3)
        self.reflector = Reflector(event_bus=self.bus, config=self.config.Reflector, memory_layer=self.l2)
        self.actuator = ActuatorLayer(event_bus=self.bus, config=self.config.Core.Actuator)
        self.psyche_system = PsycheSystem(config=self.config.L0.PsycheSystem)  
        
        # 初始化调度器
        self.dispatcher = Dispatcher(
            event_bus=self.bus, 
            l0=self.l0, 
            l1=self.l1, 
            l2=self.l2, 
            l3=self.l3, 
            actuator=self.actuator, 
            reflector=self.reflector, 
            psyche_system=self.psyche_system, 
            session=self.session,
            checkpoint_manager=self.checkpoint_manager
        )
        
        # 注册检查点管理器
        self._setup_checkpoints()  

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
        
        # === 新增：Dashboard 专用接口 ===
        self.app.get("/dashboard/snapshot")(self.get_system_snapshot)
        # self.app.post("/dashboard/control")(self.control_system) # (可选) 用于手动控制


    async def get_system_snapshot(self):
        """
        上帝视角：聚合所有层级的状态
        Streamlit 将每隔几秒调用一次这个接口
        """
        return {
            "system": {
                "dispatcher_alive": self.dispatcher_thread.is_alive() if self.dispatcher_thread else False,
                "online_clients": len(self.manager.active_connections) if hasattr(self.manager, 'active_connections') else 0
            },
            "l3_persona": self.l3.get_status(),
            "session": self.session.get_status(),
            "l2_memory": self.l2.get_status(),
            "l1_brain": self.l1.get_status(),
            "l0_sensor": self.l0.get_status(),
            "actuator": self.actuator.get_status(),
            "psyche": self.psyche_system.get_status(),
            "reflector": self.reflector.get_status()
        }

    # # 3. (可选) 新增 handler 方法：反向控制
    # async def control_system(self, command: dict):
    #     """接收 Dashboard 的指令来修改 AI 状态"""
    #     action = command.get("action")
        
    #     # 示例：强制修改精力值
    #     if action == "set_energy":
    #         new_val = int(command.get("value", 50))
    #         self.l3.character_identity.energy_level = new_val
    #         self.logger.info(f"[Dashboard] Manually set energy to {new_val}")
            
    #     return {"status": "executed", "action": action}
    
    def _setup_checkpoints(self):
        """
        专门负责将各组件注册到 CheckpointManager。
        这样业务组件就不需要依赖 Manager，解耦彻底。
        """
        # TODO 有些不需要的要去掉
        registry_list = [
            ("layer_1_brain", self.l1.get_snapshot, self.l1.load_snapshot),
            # ("layer_2_memory", self.l2.export_memory, self.l2.import_memory), # L2 似乎不需要存储，因为是 Milvus 外部存储
            ("layer_3_persona", self.l3.get_snapshot, self.l3.load_snapshot),
            # ("system_clock", lambda: {"tick": self.clock.current_tick},lambda data: self.clock.set_tick(data["tick"])), # 时钟不需要存储
            ("reflector", self.reflector.dump_state, self.reflector.load_state),
            ("session", self.session.dump_state, self.session.load_state), # TODO 待完善
            ("psyche", self.psyche_system.dump_state, self.psyche_system.load_state)
        ]
        # 注册所有组件
        for name, getter, setter in registry_list:
            try:
                self.checkpoint_manager.register(name, getter, setter)
            except Exception as e:
                # 这样即使某一个写错了，也不会阻止 Server 启动，但会留下日志
                self.logger.error(f"Failed to register checkpoint for {name}: {e}")
        


    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """生命周期管理：处理 Agent 的启动和关闭"""
        # --- Startup ---
        self.logger.info(">>> [System] Elysia Server Starting...")
        
        # =========================================================
        # 第一阶段：静态恢复 (先找回脑子)
        # 此时没有任何线程在跑，没有任何事件在流动，是最安全的时刻
        # =========================================================
        self.checkpoint_manager.load_checkpoint()
        self.logger.info(">>> [System] Memory Restored.")

        # =========================================================
        # 第二阶段：基础设施准备 (准备四肢)
        # =========================================================
        # 1. 获取 EventLoop 并注入给 ConnectionManager
        try:
            loop = asyncio.get_running_loop()
            self.manager.set_loop(loop)
        except RuntimeError:
            self.logger.warning(">>> [Warning] No running event loop found for ConnectionManager.")

        # 2. 关键：将 WebSocket 管理器注册为 Actuator 的输出通道 (嘴巴)
        self.actuator.add_channel(self.manager)
        
        # 3. 启动时钟
        self.clock.start()

        # 4. 启动各个组件的线程
        self.logger.info(">>> [System] Starting Layer Threads...")
        self.l0.start_threads()  # L0 监听
        self.reflector.start()   # 反思者

        # 5. 启动 Dispatcher (独立线程)
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
            
        if self.checkpoint_manager:
            self.checkpoint_manager.save_checkpoint() # 关闭前保存检查点
            
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
                parsed_data['source'] = L0InputSourceType.WEBSOCKET.value
                
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
        uvicorn.run(self.app, 
                    host=self.host, 
                    port=self.port, 
                    log_level=self.log_level)


        
        