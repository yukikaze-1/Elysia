import logging
from datetime import datetime, timedelta
from typing import Literal
from Core.EventBus import EventBus, global_event_bus
from Core.Schema import Event, EventType
from Layers.L0.Amygdala import AmygdalaOutput
from Layers.L0.Sensor import EnvironmentInformation, TimeInfo
from Core.Schema import UserMessage, ChatMessage
from Layers.L0.L0 import SensorLayer
from Layers.L1 import ActiveResponse, BrainLayer
from Layers.L2 import MemoryLayer
from Layers.L3 import PersonaLayer
from Workers.Reflector.Reflector import Reflector
from Layers.Actuator.ActuatorLayer import ActuatorLayer, ActionType
from Logger import setup_logger

from Utils import timedelta_to_text

class Dispatcher:
    """
    调度器：负责协调 L0, L1, L2, L3 各层的工作流程
    1. 接收来自 EventBus 的事件
    2. 根据事件类型调用相应层的处理方法
    3. 管理各层之间的数据流动和依赖关系
    4. 实现主动性逻辑 (Agency)，决定何时让 AI 主动发起对话
    5. 处理错误和异常，确保系统稳定运行
    """
    def __init__(self, event_bus: EventBus = global_event_bus, 
                 l0: SensorLayer = SensorLayer(), 
                 l1: BrainLayer = BrainLayer(), 
                 l2: MemoryLayer = MemoryLayer(),
                 l3: PersonaLayer = PersonaLayer(), 
                 actuator: ActuatorLayer = ActuatorLayer(),
                 reflector: Reflector = Reflector()
                 ):
        """
        初始化调度器，注入所有依赖层
        """
        self.logger: logging.Logger = setup_logger("Dispatcher")
        self.bus: EventBus = event_bus
        self.l0: SensorLayer = l0  # 感知层
        self.l1: BrainLayer = l1  # 大脑层
        self.l2: MemoryLayer = l2  # 记忆层
        self.l3: PersonaLayer = l3  # 人格层
        self.actuator: ActuatorLayer = actuator  # 执行层
        self.reflector: Reflector = reflector # 反思者
        
        self.running = False
        
        # === 主动性控制参数 ===
        # 记录上次交互时间
        tmp_time = datetime.now()
        self.last_interaction_time: datetime = tmp_time     # last_interaction_time：AI 或用户最后一次说话的时间
        self.last_ai_reply_time: datetime = tmp_time        # last_ai_reply_time：AI最后一次说话的时间
        self.last_user_reply_time: datetime = tmp_time      # last_user_reply_time：用户最后一次说话的时间
        self.last_speaker: Literal['Elysia', '妖梦'] = "Elysia"  # 记录上次发言者，初始为 AI
        
        # 冷却时间：AI 主动说话后，至少安静 100 秒
        # TODO 此处限制并没有被使用
        self.active_cooldown: timedelta = timedelta(seconds=60) 
        # 触发阈值：用户沉默超过 60 秒才考虑主动说话
        self.silence_threshold: timedelta = timedelta(seconds=60)

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
                    self._handle_user_input(event)
                
                elif event.type == EventType.SYSTEM_TICK:
                    self._handle_system_tick(event)
                
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
        # self.l0.output(ChatMessage.from_UserMessage(user_input))
        self.actuator.perform_action(ActionType.SPEECH, ChatMessage.from_UserMessage(user_input))

        # 1. 更新交互时间
        self.last_interaction_time = datetime.now()
        
        # 2. [Actuator] 输出
        l0_output = event.metadata.get("AmygdalaOutput", AmygdalaOutput("", EnvironmentInformation(TimeInfo())) )

        # 3. [L2] 检索相关记忆 (Short-term + Long-term)
        # 获取 3条相关记忆 + 昨天的日记摘要
        history, micro_memories, macro_memories = self.l2.retrieve_context(query=user_input.content)

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
            l0_output=l0_output
        )
        
        # === 构造标准消息对象 ===
        user_msg = ChatMessage.from_UserMessage(user_input)
        ai_msg = ChatMessage(role="Elysia", content=res.public_reply, inner_voice=res.inner_thought)
        
        # [Actuator] 输出回复
        self.actuator.perform_action(ActionType.SPEECH, ai_msg)
        
        # 6. [L2] 写入短时记忆
        # === 分发给 L2 (为了下一句能接上话) ===
        messages: list[ChatMessage] = [user_msg, ai_msg]
        self.l2.add_short_term_memory(messages)
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


        
    def _handle_system_tick(self, event: Event):
        """
        处理心跳事件：包括保存会话和主动发起对话
        """
        self.logger.info("System tick event received.")
        
        # 1. 定期保存会话状态
        self._handle_system_tick_save_session(event)
        
        # 2. 检查是否需要主动发起对话
        self._handle_system_tick_active_speak(event)
        
        
    def _handle_system_tick_save_session(self, event: Event):
        """
        处理心跳事件：定期保存会话状态
        """
        # TODO 这里可以根据实际需求调整保存频率
        self.logger.info("Saving session state...")
        try:
            self.l2.session._save_session()
            self.logger.info("Session state saved successfully.")
        except Exception as e:
            self.logger.error(f"Error saving session state: {e}", exc_info=True)
            
    
    def _handle_system_tick_active_speak(self, event: Event):
        """
        处理心跳事件：决定是否主动发起对话
        """
        # event.content 与 event.timestamp 是当前时间戳
        # 以l0感知到的环境信息中的的时间戳为基准进行计算，避免时间漂移
        # 此处的时间戳只为了计算沉默时长和判定冷却期(硬性条件)
        self.logger.info("---------------------------------------------------")
        current_time: datetime = datetime.fromtimestamp(event.timestamp)
        self.logger.info(f"System tick received at {current_time.isoformat()}")
        
        # 1. 计算沉默时长
        silence_duration_since_last_ai_reply: timedelta = current_time - self.last_ai_reply_time
        silence_duration_since_last_user_reply: timedelta = current_time - self.last_user_reply_time
        self.logger.info(f"Silence duration since last AI reply: {timedelta_to_text(silence_duration_since_last_ai_reply)}, \
            since last user reply: {timedelta_to_text(silence_duration_since_last_user_reply)}"
        )
        
        # 2. 检查硬性条件 (避免频繁打扰)
        if silence_duration_since_last_ai_reply < self.silence_threshold:
            self.logger.info(f"Event time: {current_time.isoformat()}, 'silence_duration_since_last_ai_reply': {timedelta_to_text(silence_duration_since_last_ai_reply)}, \
                last interaction: {self.last_interaction_time.isoformat()}")
            self.logger.info(f"Silence duration below threshold '{timedelta_to_text(self.silence_threshold)}', not initiating conversation.")
            return # 还没到寂寞的时候，直接返回
        
        if self.last_speaker == "Elysia" and silence_duration_since_last_ai_reply < self.active_cooldown:
            self.logger.info(f"Last speaker was AI and still in cooldown period '{timedelta_to_text(self.active_cooldown)}', not initiating conversation.")
            return

        # 检查是否还在冷却期内 (比如刚主动说完话)
        # 这里需要额外的逻辑记录 "last_active_message_time"，简化起见暂略
        
        # 3. [L3] 检查人格状态 (是否具备主动性)
        # 比如：如果是“高冷”性格，可能永远不主动
        # TODO 待考虑修改, 目前L3没有这个接口，返回True
        if not self.l3.should_initiate_conversation():
            return
        self.logger.info("Persona allows initiating conversation.")
        
        # 3.5 感知当前环境
        cur_envs: EnvironmentInformation = self.l0.sensory_processor.active_perception_envs()
        current_time = datetime.fromtimestamp(cur_envs.time_envs.current_time)
        silence_duration = current_time - self.last_interaction_time

        # 4. [L1] 决策层
        # 询问大脑："用户很久没说话了，现在是{时间}，你想说点什么吗？"
        cur_mood = self.l3.get_current_mood()
        # 读取近期记忆
        recent_memories = self.l2.get_recent_summary(limit=5)
        # 调用LLM
        response: ActiveResponse = self.l1.decide_to_act(
            silence_duration=silence_duration,
            last_speaker=self.last_speaker,
            cur_mood=cur_mood,
            cur_envs=cur_envs,
            recent_conversations=recent_memories
        )
        should_speak: bool = response.should_speak
        
        # 决定主动说话
        if should_speak:
            self.logger.info("Elysia decided to initiate conversation.")
            
            # 5. 生成主动问候语，已经在第四步完成
            msg = ChatMessage(role="Elysia", content=response.public_reply, inner_voice=response.inner_voice)
            
            # 6. 输出
            self.actuator.perform_action(ActionType.SPEECH, msg)
            
            # 7. 记忆更新
            self.l2.add_short_term_memory(messages=[msg])
            self.reflector.on_new_message(msg)
            
            # 8. 更新情绪
            self.l3.update_mood(response.mood)
            
            # 9. 重置主动交互时间，避免连续触发
            tmp_time = datetime.now()
            self.last_ai_reply_time = tmp_time
            self.last_interaction_time = tmp_time
            self.last_speaker = "Elysia"
        else:
            self.logger.info("Elysia decided not to initiate conversation at this time.")
            
        self.logger.info("System tick processing completed.")


    def stop(self):
        self.running = False
        self.logger.info("Dispatcher stopping...")
        
        
