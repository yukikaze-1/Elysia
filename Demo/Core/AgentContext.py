"""
定义 AgentContext 数据类，封装智能体的各个核心组件实例。
"""
from dataclasses import dataclass

from Layers.L0.L0 import SensorLayer
from Layers.L1 import BrainLayer
from Layers.L2.L2 import MemoryLayer
from Layers.L3 import PersonaLayer
from Core.ActuatorLayer import ActuatorLayer
from Workers.Reflector.Reflector import Reflector
from Layers.PsycheSystem import PsycheSystem
from Core.SessionState import SessionState
from Core.CheckPointManager import CheckPointManager
from Core.EventBus import EventBus
from Core.PromptManager import PromptManager

@dataclass
class AgentContext:
    event_bus: EventBus
    l0: SensorLayer
    l1: BrainLayer
    l2: MemoryLayer
    l3: PersonaLayer
    actuator: ActuatorLayer
    reflector: Reflector
    psyche_system: PsycheSystem
    session: SessionState
    checkpoint_manager: CheckPointManager
    prompt_manager: PromptManager
    # 未来添加新组件只需在这里加一行