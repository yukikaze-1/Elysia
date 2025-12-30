import logging
from datetime import datetime, timedelta
from typing import Literal
from Core.EventBus import EventBus
from Core.Schema import Event, EventType
from Layers.L0.Sensor import EnvironmentInformation, TimeInfo
from Core.Schema import UserMessage, ChatMessage
from Layers.L0.L0 import SensorLayer
from Layers.PsycheSystem import PsycheSystem, EnvironmentalStimuli
from Layers.L1 import ActiveResponse, BrainLayer
from Layers.L2.L2 import MemoryLayer
from Layers.L3 import PersonaLayer
from Workers.Reflector.Reflector import Reflector
from Core.ActuatorLayer import ActuatorLayer, ActionType
from Core.SessionState import SessionState
from Core.CheckPointManager import CheckpointManager
from Logger import setup_logger


from Core.Handlers.UserInputHandler import UserInputHandler
from Core.Handlers.SystemTickHandler import SystemTickHandler

class Dispatcher:
    """
    调度器：负责协调 L0, L1, L2, L3 各层的工作流程
    1. 接收来自 EventBus 的事件
    2. 根据事件类型调用相应层的处理方法
    3. 管理各层之间的数据流动和依赖关系
    4. 实现主动性逻辑 (Agency)，决定何时让 AI 主动发起对话
    5. 处理错误和异常，确保系统稳定运行
    """
    def __init__(self, event_bus: EventBus, 
                 l0: SensorLayer, 
                 l1: BrainLayer, 
                 l2: MemoryLayer,
                 l3: PersonaLayer, 
                 actuator: ActuatorLayer,
                 reflector: Reflector,
                 psyche_system: PsycheSystem,
                 session: SessionState,
                 checkpoint_manager: CheckpointManager
                 ):
        """
        初始化调度器，注入所有依赖层
        """
        self.logger: logging.Logger = setup_logger("Dispatcher")
        
        # 核心组件
        self.bus: EventBus = event_bus  # 事件总线
        self.actuator: ActuatorLayer = actuator  # 执行层
        self.session: SessionState = session  # 会话状态管理
        self.checkpoint_manager: CheckpointManager = checkpoint_manager  # 检查点管理
        
        # 各层引用
        self.l0: SensorLayer = l0  # 感知层
        self.l1: BrainLayer = l1  # 大脑层
        self.l2: MemoryLayer = l2  # 记忆层
        self.l3: PersonaLayer = l3  # 人格层
        self.reflector: Reflector = reflector # 反思者
        self.psyche_system: PsycheSystem = psyche_system  # 心理系统
        
        self.running = False
        
        self.user_input_handler = UserInputHandler(
            actuator=self.actuator,
            psyche_system=self.psyche_system,
            session=self.session,
            l2=self.l2,
            l3=self.l3,
            l1=self.l1,
            reflector=self.reflector
        )
        self.systemtick_handler = SystemTickHandler(
            actuator=self.actuator,
            psyche_system=self.psyche_system,
            l0=self.l0,
            l1=self.l1,
            session=self.session,
            l2=self.l2,
            l3=self.l3,
            reflector=self.reflector,
            checkpoint_manager=self.checkpoint_manager
        )
        

    def start(self):
        """启动调度主循环 (阻塞式)"""
        self.running = True
        self.logger.info("Dispatcher Loop Started.")
        
        while self.running:
            # 1. 从总线获取事件 (阻塞 1 秒，方便处理退出信号)
            event = self.bus.get(block=True, timeout=1.0)
            
            if not event:
                continue

            try:
                # 2. 路由分发
                if event.type == EventType.USER_INPUT:
                    # 用户输入事件
                    self.user_input_handler.handle(event)
                
                elif event.type == EventType.SYSTEM_TICK:
                    # 系统心跳事件
                    self.systemtick_handler.handle(event)
                
                elif event.type == EventType.MACRO_REFLECTION_DONE:
                    # Reflector 完成了Macro reflect，通知 L2 或 L3 更新
                    # TODO 待实现
                    self.logger.info("Macro reflection completed.")
                
                elif event.type == EventType.MICRO_REFLECTION_DONE:
                    # Reflector 完成了Micro reflect，通知 L2 或 L3 更新
                    # TODO 待实现
                    self.logger.info("Micro reflection completed.")
                elif event.type == EventType.REFLECTION_DONE:
                    # Reflector 完成了 reflection，通知 L2 或 L3 更新
                    # TODO 待实现
                    self.logger.info("Reflection completed.")
                else:
                    self.logger.warning(f"Unknown event type: {event.type}")

            except Exception as e:
                self.logger.error(f"Error processing event {event.id}: {e}", exc_info=True)
                # 可以在这里让 L0 输出一个通用的错误提示，比如 "我有点头晕..."

        self.logger.info("Dispatcher Loop Stopped.")


    def stop(self):
        self.running = False
        self.logger.info("Dispatcher stopping...")
        
        
