# Demo/Core/Dispatcher.py
import time
import logging
from datetime import datetime, timedelta
from Demo.Core.EventBus import EventBus, global_event_bus
from Demo.Core.Schema import Event, EventType
from Demo.Layers.L0.Amygdala import AmygdalaOutput
from Demo.Layers.L0.Sensor import EnvironmentInformation
from Demo.Layers.Session import UserMessage, ChatMessage


from Demo.Layers.L0.L0 import SensorLayer
from Demo.Layers.L1 import BrainLayer
from Demo.Layers.L2 import MemoryLayer
from Demo.Layers.L3 import PersonaLayer
from Demo.Workers.Reflector.Reflector import Reflector
from Demo.Logger import setup_logger

class Dispatcher:
    def __init__(self, event_bus: EventBus = global_event_bus, 
                 l0: SensorLayer = SensorLayer(), 
                 l1: BrainLayer = BrainLayer(), 
                 l2: MemoryLayer = MemoryLayer(),
                 l3: PersonaLayer = PersonaLayer(), 
                 reflector: Reflector = Reflector()):
        """
        初始化调度器，注入所有依赖层
        """
        self.logger: logging.Logger = setup_logger("Dispatcher")
        self.bus: EventBus = event_bus
        self.l0: SensorLayer = l0  # 感知层
        self.l1: BrainLayer = l1  # 大脑层
        self.l2: MemoryLayer = l2  # 记忆层
        self.l3: PersonaLayer = l3  # 人格层
        self.reflector: Reflector = reflector # 反思者
        
        self.running = False
        
        # === 主动性控制参数 ===
        self.last_interaction_time: datetime = datetime.now()
        # 冷却时间：AI 主动说话后，至少安静 100 秒
        # TODO 此处限制并没有被使用
        self.active_cooldown: timedelta = timedelta(seconds=100) 
        # 触发阈值：用户沉默超过 20 秒才考虑主动说话
        self.silence_threshold: timedelta = timedelta(seconds=20)


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
                
                else:
                    self.logger.warning(f"Unknown event type: {event.type}")

            except Exception as e:
                self.logger.error(f"Error processing event {event.id}: {e}", exc_info=True)
                # 可以在这里让 L0 输出一个通用的错误提示，比如 "我有点头晕..."

        self.logger.info("Dispatcher Loop Stopped.")


    def _handle_user_input(self, event: Event):
        """
        处理用户输入的核心流程：
        感知 -> 检索记忆 -> 读取人设 -> 思考 -> 表达 -> 存储 -> 触发反思
        """
        user_input: UserMessage = event.content
        self.logger.info(f"Processing user input: {user_input.to_str()}")

        # 1. 更新交互时间
        self.last_interaction_time = datetime.now()
        
        # 2. [L0] 输出
        cur_env: EnvironmentInformation = self.l0.sensory_processor.active_perception_envs() 
        l0_output: AmygdalaOutput = self.l0.amygdala.react(user_message=user_input, current_env=cur_env)

        # 3. [L2] 检索相关记忆 (Short-term + Long-term)
        # 获取 3条相关记忆 + 昨天的日记摘要
        history, micro_memories, macro_memories = self.l2.retrieve_context(query=user_input.content)

        # 4. [L3] 获取人格状态
        persona:str = self.l3.get_persona_prompt()

        # 5. [L1] 调用大脑生成回复
        # 组装 Prompt 的工作通常在 L1 内部或这里完成，建议由 L1 封装
        public_reply, inner_thought = self.l1.generate_reply(
            user_input=user_input,
            persona=persona,
            micro_memories=micro_memories,
            macro_memories=macro_memories,
            history=history,
            l0_output=l0_output
        )
        
        # [L0] 输出回复
        self.l0.output(public_reply, inner_thought)
        
        # === 构造标准消息对象 ===
        user_msg = ChatMessage.from_UserMessage(user_input)
        ai_msg = ChatMessage(role="Elysia", content=public_reply, inner_voice=inner_thought)
        
        # 6. [L2] 写入短时记忆
        # === 分发给 L2 (为了下一句能接上话) ===
        messages: list[ChatMessage] = [user_msg, ai_msg]
        self.l2.add_short_term_memory(messages)
        self.logger.info("Short-term memory updated.")
        
        # === 分发给 Reflector (为了变成长期记忆) ===
        # Reflector 内部会将其加入 buffer，攒够了就提取并清空
        self.reflector.on_new_message(user_msg)
        self.reflector.on_new_message(ai_msg)
        self.logger.info("Message sent to Reflector for potential long-term memory storage.")
        
        # [L3] 更新情绪
        self.l3.update_mood(user_input) 
        self.logger.info("Persona mood updated.")

        self.logger.info("User input processing completed.")


    def _handle_system_tick(self, event: Event):
        """
        处理心跳事件：决定是否主动发起对话 (Agency)
        """
        # event.content 可能是当前时间戳
        current_time: datetime = datetime.fromtimestamp(event.timestamp)
        self.logger.info(f"System tick received at {current_time.isoformat()}")
        
        # 1. 计算沉默时长
        silence_duration = current_time - self.last_interaction_time
        
        # 2. 检查硬性条件 (避免频繁打扰)
        if silence_duration < self.silence_threshold:
            self.logger.info(f"Event time: {current_time.isoformat()}, 'silence_duration': {silence_duration}, last interaction: {self.last_interaction_time.isoformat()}")
            self.logger.info("Silence duration below threshold, not initiating conversation.")
            return # 还没到寂寞的时候，直接返回

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

        # 4. [L1] 决策层 (廉价 LLM 调用)
        # 询问大脑："用户很久没说话了，现在是{时间}，你想说点什么吗？"
        recent_memories = self.l2.get_recent_summary(limit=5)
        response = self.l1.decide_to_act(
            silence_duration=silence_duration,
            cur_envs=cur_envs,
            recent_conversations=recent_memories
        )
        should_speak: bool = response.should_speak
        if should_speak:
            self.logger.info("AI decided to initiate conversation.")
            
            # 5. 生成主动问候语
            # 注意：这里不需要 user_input，因为是无中生有
            greeting = response.content
            reason = response.reasoning
            # 6. 输出并记录
            self.l0.output(greeting, reason)
            # 发送给L2，存入session
            self.l2.add_short_term_memory(
                messages=[ChatMessage(role="Elysia", content=greeting, inner_voice=reason)]
            )
            # 发送给Reflector，存入长期记忆
            self.reflector.on_new_message(
                ChatMessage(role="Elysia", content=greeting, inner_voice=reason)
            )
            # 重置交互时间，避免连续触发
            self.last_interaction_time = datetime.now()
        else:
            self.logger.info("AI decided not to initiate conversation at this time.")
            
        self.logger.info("System tick processing completed.")


    def stop(self):
        self.running = False
        self.logger.info("Dispatcher stopping...")
        
        
