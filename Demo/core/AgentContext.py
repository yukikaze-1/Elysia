"""
定义 AgentContext 数据类，封装智能体的各个核心组件实例。
"""
from dataclasses import dataclass

from layers.L0.L0 import SensorLayer
from layers.L1 import BrainLayer
from layers.L2.L2 import MemoryLayer
from layers.L3 import PersonaLayer
from core.ActuatorLayer import ActuatorLayer
from workers.reflector.Reflector import Reflector
from layers.PsycheSystem import PsycheSystem
from core.SessionState import SessionState
from core.CheckPointManager import CheckPointManager
from core.EventBus import EventBus
from core.PromptManager import PromptManager

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