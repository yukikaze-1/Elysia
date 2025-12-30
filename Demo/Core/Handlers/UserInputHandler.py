"""
    用户输入处理器
"""

from datetime import datetime
import logging

from Core.Schema import Event, UserMessage, ChatMessage
from Layers.L0.Amygdala import AmygdalaOutput
from Layers.L0.Sensor import EnvironmentInformation, TimeInfo
from Core.ActuatorLayer import ActuatorLayer, ActionType
from Layers.PsycheSystem import PsycheSystem, EnvironmentalStimuli
from Core.SessionState import SessionState
from Layers.L2 import MemoryLayer
from Layers.L3 import PersonaLayer
from Layers.L1 import BrainLayer
from Workers.Reflector.Reflector import Reflector
from Core.Handlers.BaseHandler import BaseHandler

from Logger import setup_logger

class UserInputHandler(BaseHandler):
    def __init__(self, actuator: ActuatorLayer, 
                 psyche_system: PsycheSystem, 
                 session: SessionState,
                 l2: MemoryLayer,
                 l3: PersonaLayer,
                 l1: BrainLayer,
                 reflector: Reflector
                 ):
        self.logger: logging.Logger = setup_logger("UserInputHandler")
        self.actuator = actuator
        self.psyche_system = psyche_system
        self.session = session
        self.l2 = l2
        self.l3 = l3
        self.l1 = l1
        self.reflector = reflector
        
        
    def handle(self, event: Event):
        return self._handle_user_input(event)
    
    
    def _handle_user_input(self, event: Event):
        """
        处理用户输入的核心流程：
        感知 -> 检索记忆 -> 读取人设 -> 思考 -> 表达 -> 存储 
        """
        if not isinstance(event.content, UserMessage):
            self.logger.error(f"Invalid event content type for USER_INPUT: {type(event.content)}")
            return
        if not isinstance(event.metadata, dict):
            self.logger.error(f"Invalid event metadata type for USER_INPUT: {type(event.metadata)}")
            return
        if not isinstance(event.metadata.get("AmygdalaOutput"), AmygdalaOutput):
            self.logger.error(f"Invalid AmygdalaOutput type in event metadata: {type(event.metadata.get('AmygdalaOutput'))}")
            return
        
        user_input: UserMessage = event.content
        self.logger.info(f"Processing user input: {user_input.to_str()}")
        
        # 输出用户输入
        # TODO web端可以不用，但本地终端调试时需要看到
        self.actuator.perform_action(ActionType.SPEECH, ChatMessage.from_UserMessage(user_input))

        # === [ADD] 1. 刺激生效：用户理我了！ ===
        # 这会瞬间清空 Boredom，并恢复一点 Social Battery
        # TODO: 如果未来有情感分析模块，可以将情感分数传进去 self.psyche.on_user_interaction(sentiment)
        self.psyche_system.on_user_interaction()
        self.logger.info(f"[PsycheSystem] User interaction received. State reset. {self.psyche_system.state}")
        
        # 1. 更新交互时间
        self.last_interaction_time = datetime.now()
        
        # 2. [Actuator] 输出
        amygdala_output = event.metadata.get("AmygdalaOutput", AmygdalaOutput("", EnvironmentInformation(TimeInfo())) )

        # 3. [L2] 检索相关记忆 (Short-term + Long-term)
        # 获取 3条相关记忆 + 昨天的日记摘要
        # 获取 20 条最近对话作为上下文
        history: list[ChatMessage] = self.session.get_recent_history(limit=20)
        micro_memories, macro_memories = self.l2.retrieve_context(query=user_input.content)

        # 4. [L3] 获取人格状态
        personality:str = self.l3.get_persona_prompt()
        mood: str = self.l3.get_current_mood()

        # 5. [L1] 调用大脑生成回复
        # 组装 Prompt 的工作通常在 L1 内部或这里完成，建议由 L1 封装
        res = self.l1.generate_reply(
            user_input=user_input,
            mood=mood,
            personality=personality,
            micro_memories=micro_memories,
            macro_memories=macro_memories,
            history=history,
            l0_output=amygdala_output
        )
        
        # === 构造标准消息对象 ===
        user_msg = ChatMessage.from_UserMessage(user_input)
        ai_msg = ChatMessage(role="Elysia", content=res.public_reply, inner_voice=res.inner_thought)
        
        # [Actuator] 输出回复
        self.actuator.perform_action(ActionType.SPEECH, ai_msg)
        
        # === [ADD] 2. 消耗生效：AI 被动回复 ===
        # 虽然是被动回复，但也会消耗少量的 Energy 和 Social Battery
        self.psyche_system.on_ai_passive_reply()
        
        # 6. [L2] 写入短时记忆
        # === 分发给 L2 (为了下一句能接上话) ===
        messages: list[ChatMessage] = [user_msg, ai_msg]
        self.session.add_messages(messages)
        self.logger.info("Short-term memory updated.")
        
        # 更新最后发言时间和发言者
        self.last_user_reply_time = datetime.fromtimestamp(user_input.client_timestamp)
        self.last_ai_reply_time = datetime.now()
        # TODO 考虑不搭理用户的情况，需要扩展
        self.last_speaker = "Elysia" # 因为目前ELysia一定会回复 
        
        # === 分发给 Reflector (为了变成长期记忆) ===
        # Reflector 内部会将其加入 buffer，攒够了就提取并清空
        self.reflector.on_new_message(user_msg)
        self.reflector.on_new_message(ai_msg)
        self.logger.info("Message sent to Reflector for potential long-term memory storage.")
        
        # [L3] 更新情绪
        self.l3.update_mood(res.mood) 
        self.logger.info("Persona mood updated.")

        self.logger.info("User input processing completed.")
        self.logger.info("------------------------------------------------------------------------------------------------")
