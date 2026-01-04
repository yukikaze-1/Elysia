"""
Elysia Server 主程序入口 (FastAPI 版本)单机版本见 Demo/main.py
负责初始化各个组件并启动 FastAPI 服务
"""
import asyncio
from enum import StrEnum
import json
import threading
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from core.EventBus import EventBus
from core.Dispatcher import Dispatcher
from core.Schema import L0InputSourceType
from layers.L0.L0 import SensorLayer
from layers.PsycheSystem import PsycheSystem
from layers.L1 import BrainLayer
from layers.L2.L2 import MemoryLayer
from layers.L3 import PersonaLayer
from core.ActuatorLayer import ActuatorLayer
from core.SystemClock import SystemClock
from workers.reflector.Reflector import Reflector
from server.ConnectionManager import ConnectionManager
from core.SessionState import SessionState
from core.CheckPointManager import CheckPointManager
from core.PromptManager import PromptManager

from core.AgentContext import AgentContext

from config.Config import GlobalConfig
from Logger import setup_logger
from starlette.types import Message
from typing import Any


class InputMessageType(StrEnum):
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    FILE = "file"
    LOCATION = "location"
    MIX = "mix"
    STREAM_AUDIO = "stream_audio"
    STREAM_VIDEO = "stream_video"


from pydantic import BaseModel, ValidationError
from typing import Literal, Optional, Any

# === 新增 Pydantic 模型用于信令控制 ===
class StreamControlPayload(BaseModel):
    """
    WebSocket 信令控制包
    客户端发送的 JSON 必须符合此格式
    """
    # 事件类型: 
    # - "chat": 普通文本聊天
    # - "start": 开始发送二进制流
    # - "stop": 停止发送二进制流
    # - "heartbeat": 心跳
    event: Literal["chat", "start", "stop", "heartbeat"] 
    
    # 如果是 "chat"，这里是文本内容
    content: str = "" 
    
    # 如果是 "start"，这里指定接下来的二进制数据是什么类型
    stream_type: Optional[Literal["audio", "video", "image", "file"]] = None
    
    # 元数据 (文件名、采样率等)
    meta: dict = {}


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
        self.checkpoint_manager = CheckPointManager(config=self.config.Core.CheckPointManager)
        self.bus: EventBus = EventBus(config=self.config.Core.EventBus)    # 全局事件总线
        self.manager = ConnectionManager()
        self.clock = SystemClock(event_bus=self.bus, config=self.config.Core.SystemClock)
        self.session = SessionState(config=self.config.Core.SessionState)
        
        # 2. 初始化层级
        self.prompt_manager = PromptManager(config=self.config.Core.PromptManager)
        self.l0 = SensorLayer(event_bus=self.bus, config=self.config.L0, prompt_manager=self.prompt_manager)
        self.l1 = BrainLayer(config=self.config.L1, prompt_manager=self.prompt_manager)
        self.l2 = MemoryLayer(config=self.config.L2)
        self.l3 = PersonaLayer(config=self.config.L3)
        self.reflector = Reflector(event_bus=self.bus, config=self.config.Reflector, memory_layer=self.l2, prompt_manager=self.prompt_manager)
        self.actuator = ActuatorLayer(event_bus=self.bus, config=self.config.Core.Actuator)
        self.psyche_system = PsycheSystem(config=self.config.L0.PsycheSystem)  
        
        # 3. 打包成 Context
        self.context = AgentContext(
            event_bus=self.bus,
            l0=self.l0,
            l1=self.l1,
            l2=self.l2,
            l3=self.l3,
            actuator=self.actuator,
            reflector=self.reflector,
            psyche_system=self.psyche_system,
            session=self.session,
            checkpoint_manager=self.checkpoint_manager,
            prompt_manager=self.prompt_manager
        )
        
        # 初始化调度器
        self.dispatcher = Dispatcher(self.context)
        
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
        self.reflector.start()   # 反思者s

        # 5. 启动 Dispatcher (独立线程)
        self.logger.info(">>> [System] Starting Dispatcher...")
        self.dispatcher_thread = threading.Thread(target=self.dispatcher.start, daemon=True)
        self.dispatcher_thread.start()

        self.logger.info(">>> [System] Elysia Agent is Ready & Listening.")
        
        yield  # 服务运行中...

        # =========================================================
        # 停止阶段：关闭各组件
        # =========================================================
        self.logger.info(">>> [System] Shutting down Elysia Agent...")
        
        # 停止组件
        if self.dispatcher:
            self.dispatcher.stop()  # 停止 Dispatcher 线程
        
        if self.l0:
            self.l0.stop_threads()  # 停止L0线程
            
        if self.reflector:
            self.reflector.stop()   # 停止Reflector线程
            
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
        """
        WebSocket 主循环 (Scheme B: 信令 + 二进制流分离)
        """
        await self.manager.connect(websocket)
        
        # === 连接级状态变量 ===
        # 这些变量只在当前这个连接的生命周期内有效
        current_stream_type: Optional[str] = None # 当前正在接收的流类型 (audio/video/image)
        is_streaming: bool = False               # 是否处于流传输模式

        try:
            while True:
                # 1. 接收原始 ASGI 消息
                # websocket.receive() 返回的是一个字典，例如:
                # Text帧:   {'type': 'websocket.receive', 'text': '...json...'}
                # Binary帧: {'type': 'websocket.receive', 'bytes': b'...'}
                message: Message = await websocket.receive()
                
                # 2. 处理 文本帧 (通常是 JSON 信令 或 聊天内容)
                if "text" in message:
                    text_data = message["text"]
                    
                    try:
                        # 解析信令
                        payload_dict = json.loads(text_data)
                        cmd = StreamControlPayload(**payload_dict)
                        
                        # --- 事件分发 ---
                        if cmd.event == "chat":
                            # 普通文本聊天 -> 这里的逻辑对应之前的 _handle_text_input
                            self.logger.debug(f"[WS] Chat received: {cmd.content}")
                            await self._process_text_chat(websocket, cmd.content, cmd.meta)
                            
                        elif cmd.event == "start":
                            # 客户端通知：我要开始发二进制数据了
                            is_streaming = True
                            current_stream_type = cmd.stream_type
                            self.logger.info(f"[WS] Stream START: Type={current_stream_type}, Meta={cmd.meta}")
                            # 可选：回执确认
                            await websocket.send_text(json.dumps({"status": "ready_to_receive", "type": current_stream_type}))
                            
                        elif cmd.event == "stop":
                            # 客户端通知：二进制发送完毕
                            self.logger.info(f"[WS] Stream STOP: Type={current_stream_type}")
                            # TODO: 这里可以触发流结束后的处理，比如“语音接收完毕，开始STT”
                            # self.l0.trigger_stt_process(...) 
                            
                            # 重置状态
                            is_streaming = False
                            current_stream_type = None
                            
                        elif cmd.event == "heartbeat":
                            pass # 心跳包，忽略或回应
                            
                    except (json.JSONDecodeError, ValidationError) as e:
                        self.logger.warning(f"[WS] Invalid JSON signal: {e}")
                        await websocket.send_text(json.dumps({"error": "invalid_protocol"}))

                # 3. 处理 二进制帧 (实际的音视频/图片数据)
                elif "bytes" in message:
                    binary_data = message["bytes"]
                    
                    if not is_streaming or not current_stream_type:
                        self.logger.warning(f"[WS] Received unexpected bytes ({len(binary_data)}b). Ignored.")
                        continue
                        
                    # 根据之前的 "start" 信令中确定的类型，分发数据
                    if current_stream_type == "audio":
                        # 实时语音流 -> 推送给 L0 或 STT 模块
                        await self._handle_stream_audio_chunk(binary_data)
                        
                    elif current_stream_type == "image":
                        # 图片数据 -> 可能是分片的，也可能是一整张
                        await self._handle_image_chunk(binary_data)
                        
                    elif current_stream_type == "video":
                        await self._handle_stream_video_chunk(binary_data)

                # 4. 处理断开连接 (receive 返回 disconnect 类型)
                elif message["type"] == "websocket.disconnect":
                    raise WebSocketDisconnect

        except WebSocketDisconnect:
            self.logger.info(f"[WebSocket] Client disconnected")
            self.manager.disconnect(websocket)
        except Exception as e:
            self.logger.error(f"[WebSocket] Critical Error: {e}", exc_info=True)
            self.manager.disconnect(websocket)
            
    # =========================================================
    #  业务逻辑处理 (L0 交互)
    # =========================================================

    async def _process_text_chat(self, websocket: WebSocket, content: str, meta: dict):
        """处理普通文本对话"""
        if not content:
            return
            
        input_data = {
            "content": content,
            # 1. 显式提取必填字段 (如果前端没传，这里可以用 .get 给默认值，或者让它报错)
            "role": meta.get("role", "user"), 
            "timestamp": meta.get("timestamp"),
            "last_ai_timestamp": meta.get("last_ai_timestamp", 0.0),
            
            # 2. 补充系统内部需要的字段
            "type": InputMessageType.TEXT.value,
            "source": L0InputSourceType.WEBSOCKET.value,
            
            # 3. 如果还有其他杂项，可以放进 metadata (可选)
            "metadata": meta 
        }

        # 现在 input_data 的结构是扁平的，符合 WebClientMessage 的要求：
        # {
        #   "role": "妖梦",
        #   "content": "...",
        #   "timestamp": 12345.6,
        #   ...
        # }
        
        self.l0.push_external_input(input_data)

    async def _handle_stream_audio_chunk(self, chunk: bytes):
        """
        处理音频流切片
        如果是实时流，这里直接喂给 VAD 或 STT Buffer
        """
        # self.logger.debug(f"[WS] Audio Chunk: {len(chunk)} bytes")
        
        # 方案 A: 如果 L0 支持流式写入
        # self.l0.push_audio_stream(chunk) 
        
        # 方案 B: 简单封装推送到 L0 (可能会产生大量小消息，取决于架构)
        # 这里演示封装成 InputMessage
        # 注意：通常流式音频不会每收到一个包就生成一个 InputMessage，
        # 而是由专门的 AudioBufferWorker 收集
        pass 

    async def _handle_image_chunk(self, chunk: bytes):
        """处理图片数据 (通常图片是一次性发完，但也可能分包)"""
        self.logger.info(f"[WS] Image Data Received: {len(chunk)} bytes")
        
        # 构造图片输入
        # 注意：这里假设客户端是一次性发完了整张图片的二进制
        input_data = {
            "content": "", # 图片没有文本内容
            "type": InputMessageType.IMAGE.value,
            "source": L0InputSourceType.WEBSOCKET.value,
            "payload": chunk, # 原始二进制
            "metadata": {}
        }
        self.l0.push_external_input(input_data)

    async def _handle_stream_video_chunk(self, chunk: bytes):
        pass
            
            
    def _handle_text_input(self, websocket: WebSocket, text_data: str):
        """处理来自 WebSocket 的文本消息"""
        self.logger.debug(f"[WebSocket] Received Text: {text_data}")
        # 1. 解析消息
        parsed_data: dict = self._parse_websocket_message(text_data)
        # 2. 标记来源
        parsed_data['source'] = L0InputSourceType.WEBSOCKET.value
        # 3. 推送到 L0 输入队列
        self.l0.push_external_input(parsed_data)
        
        
    
            
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


        
        