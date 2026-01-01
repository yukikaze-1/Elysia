"""
    用户输入处理器
"""

import logging

from core.Schema import Event, UserMessage, ChatMessage
from layers.L0.Amygdala import AmygdalaOutput
from layers.L0.Sensor import EnvironmentInformation, TimeInfo
from core.ActuatorLayer import ActuatorLayer, ActionType
from layers.PsycheSystem import PsycheSystem
from core.SessionState import SessionState
from layers.L2 import MemoryLayer
from layers.L3 import PersonaLayer
from layers.L1 import BrainLayer, NormalResponse
from workers.Reflector.Reflector import Reflector
from core.Handlers.BaseHandler import BaseHandler

from core.AgentContext import AgentContext
from core.HandlerRegistry import HandlerRegistry
from core.Schema import EventType

from Logger import setup_logger

@HandlerRegistry.register(EventType.USER_INPUT)
class UserInputHandler(BaseHandler):
    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.logger: logging.Logger = setup_logger("UserInputHandler")
        
        # 核心组件引用
        self.actuator: ActuatorLayer = context.actuator
        self.psyche_system: PsycheSystem = context.psyche_system
        self.session: SessionState = context.session
        self.l2: MemoryLayer = context.l2
        self.l3: PersonaLayer = context.l3
        self.l1: BrainLayer = context.l1
        self.reflector: Reflector = context.reflector
        
        
    def handle(self, event: Event):
        return self._handle_user_input(event)
    
    
    def _handle_user_input(self, event: Event):
        """
        处理用户输入的核心流程：
        感知 -> 检索记忆 -> 读取人设 -> 思考 -> 表达 -> 存储 
        """
        # 0. 检查事件有效性
        if not self._check_event_validity(event):
            self.logger.error("Event validity check failed. Aborting user input handling.")
            return
        
        user_input: UserMessage = event.content
        self.logger.info(f"Processing user input: {user_input.to_str()}")
        
        # 输出用户输入
        self.actuator.perform_action(ActionType.SPEECH, ChatMessage.from_UserMessage(user_input))

        # === [ADD] 1. 刺激生效：用户理我了！ ===
        # 这会瞬间清空 Boredom，并恢复一点 Social Battery
        # TODO: 如果未来有情感分析模块，可以将情感分数传进去 self.psyche.on_user_interaction(sentiment)
        self.psyche_system.on_user_interaction()
        self.logger.info(f"[PsycheSystem] User interaction received. State reset. {self.psyche_system.state}")
        
        # 调用大脑层生成回复
        res = self._execute_brain_decision(event, user_input)
        
        # === 构造标准消息对象 ===
        user_msg = ChatMessage.from_UserMessage(user_input)
        ai_msg = ChatMessage(role="Elysia", content=res.public_reply, inner_voice=res.inner_thought)
        
        # [Actuator] 输出回复
        self.actuator.perform_action(ActionType.SPEECH, ai_msg)
        
        # 消耗生效：AI 被动回复 
        # 虽然是被动回复，但也会消耗少量的 Energy 和 Social Battery
        self.psyche_system.on_ai_passive_reply()
        
        # === 存储对话到记忆系统 ===
        self._save_to_memory(user_msg, ai_msg)
        
        # [L3] 更新情绪
        self.l3.update_mood(res.mood) 
        self.logger.info("Persona mood updated.")

        self.logger.info("User input processing completed.")
        self.logger.info("------------------------------------------------------------------------------------------------")

    
    def _check_event_validity(self, event: Event) -> bool:
        """检查事件的有效性"""
        if not isinstance(event.content, UserMessage):
            self.logger.error(f"Invalid event content type for USER_INPUT: {type(event.content)}")
            return False
        if not isinstance(event.metadata, dict):
            self.logger.error(f"Invalid event metadata type for USER_INPUT: {type(event.metadata)}")
            return False
        if not isinstance(event.metadata.get("AmygdalaOutput"), AmygdalaOutput):
            self.logger.error(f"Invalid AmygdalaOutput type in event metadata: {type(event.metadata.get('AmygdalaOutput'))}")
            return False
        return True
    
    
    def _execute_brain_decision(self, event: Event, user_input: UserMessage) -> NormalResponse:
        """调用大脑层生成回复"""
        
        # 1. amygdala输出
        amygdala_output = (event.metadata or {}).get("AmygdalaOutput", AmygdalaOutput("", EnvironmentInformation(TimeInfo())) )

        # 2. [L2] 检索相关记忆 (Short-term + Long-term)
        # 获取 3条相关记忆 + 昨天的日记摘要
        # 获取 20 条最近对话作为上下文
        history: list[ChatMessage] = self.session.get_recent_history(limit=20)
        micro_memories, macro_memories = self.l2.retrieve_context(query=user_input.content)

        # 4. [L3] 获取人格状态
        personality:str = self.l3.get_persona_prompt()
        mood: str = self.l3.get_current_mood()

        # 5. [L1] 调用大脑生成回复
        # 组装 Prompt 的工作通常在 L1 内部或这里完成，建议由 L1 封装
        res: NormalResponse = self.l1.generate_reply(
            user_input=user_input,
            mood=mood,
            personality=personality,
            micro_memories=micro_memories,
            macro_memories=macro_memories,
            history=history,
            l0_output=amygdala_output
        )
        return res
    
    def _save_to_memory(self, user_msg: ChatMessage, ai_msg: ChatMessage):
        """将对话对保存到短时记忆和长期记忆缓冲区"""
        # 1. 分发给 L2 (Session)
        self.session.add_messages([user_msg, ai_msg])
        self.logger.info("Short-term memory updated.")
        
        # 2. 分发给 Reflector (Long-term Buffer)
        self.reflector.on_new_message(user_msg)
        self.reflector.on_new_message(ai_msg)
        self.logger.info("Message sent to Reflector for potential long-term memory storage.")
    
    