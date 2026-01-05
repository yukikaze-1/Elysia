"""
系统心跳处理器：处理定时心跳事件，包括保存会话和主动发起对话
"""

from datetime import datetime, timedelta
import logging
from core.Schema import Event, ChatMessage
from core.actuator.ActuatorLayer import ActuatorLayer, ActionType
from layers.PsycheSystem import PsycheSystem, EnvironmentalStimuli
from layers.L0.Sensor import  EnvironmentInformation
from layers.L0 import SensorLayer
from layers.L1 import BrainLayer, ActiveResponse, NormalResponse
from core.SessionState import SessionState
from layers.L2 import MemoryLayer
from layers.L3 import PersonaLayer
from workers.reflector.Reflector import Reflector
from core.CheckPointManager import CheckPointManager
from Logger import setup_logger
from Utils import timedelta_to_text
from core.handlers.BaseHandler import BaseHandler
from core.Schema import EventType, DEFAULT_ERROR_INNER_THOUGHT, DEFAULT_ERROR_MOOD, DEFAULT_ERROR_PUBLIC_REPLY
from core.AgentContext import AgentContext

from core.HandlerRegistry import HandlerRegistry


@HandlerRegistry.register(EventType.SYSTEM_TICK)
class SystemTickHandler(BaseHandler):
    # === 配置常量 ===
    MAX_TICK_DT = 60.0          # 最大生理更新步长（秒）
    USER_PRESENT_TIMEOUT = 300  # 用户被判定为“在场”的超时时间（秒）
    RECENT_MEMORY_LIMIT = 10    # 读取最近记忆的条数
    
    def __init__(self, context: AgentContext):
        super().__init__(context)
        self.logger: logging.Logger = setup_logger("SystemTickHandler")
        
        # 核心组件引用
        self.actuator: ActuatorLayer = context.actuator
        self.psyche_system: PsycheSystem = context.psyche_system
        self.l0: SensorLayer = context.l0
        self.l1: BrainLayer = context.l1
        self.session: SessionState = context.session
        self.l2: MemoryLayer = context.l2
        self.l3: PersonaLayer = context.l3
        self.reflector: Reflector = context.reflector
        self.checkpoint_manager: CheckPointManager = context.checkpoint_manager
        
        # === 主动性控制参数 ===
        # 用于计算两次心跳之间的时间差 (dt)
        self.last_tick_time = datetime.now()
        
        
    def handle(self, event: Event):
        """  处理系统心跳事件 """
        return self._handle_system_tick(event)
        
    
    def _handle_system_tick(self, event: Event):
        """
        处理心跳事件：包括保存会话和主动发起对话
        """
        self.logger.info("System tick event received.")
        
        # 1. 保存状态到检查点
        self.checkpoint_manager.save_checkpoint()
        
        # 2. 检查是否需要主动发起对话
        self._handle_system_tick_active_speak(event)
        
            
    
    def _handle_system_tick_active_speak(self, event: Event):
        """
        处理心跳事件：决定是否主动发起对话
        """
        # event.content 与 event.timestamp 是当前时间戳
        # 以l0感知到的环境信息中的的时间戳为基准进行计算，避免时间漂移
        # 此处的时间戳只为了计算沉默时长和判定冷却期(硬性条件)
        self.logger.debug("---------------------------------------------------")
        current_time: datetime = datetime.fromtimestamp(event.timestamp)
        self.logger.debug(f"System tick received at {current_time.isoformat()}")
        
        # [NEW] 从 SessionState 获取状态
        # 如果时间戳为0，说明从未说过话，使用当前时间作为默认值，避免刚启动就触发“很久没说话”的逻辑
        # 或者使用 datetime.min，但这会导致 silence_duration 极大。
        # 策略：如果从未说过话，认为 silence_duration = 0
        
        last_ai_reply_time: datetime = datetime.fromtimestamp(self.session.last_ai_reply_time) if self.session.last_ai_reply_time > 0 else current_time
        last_user_reply_time: datetime = datetime.fromtimestamp(self.session.last_user_reply_time) if self.session.last_user_reply_time > 0 else current_time
        last_interaction_time: datetime = datetime.fromtimestamp(self.session.last_interaction_time) if self.session.last_interaction_time > 0 else current_time
        last_speaker: str = self.session.last_speaker if self.session.last_speaker else "Elysia"

        # 0. 计算沉默时长
        silence_duration_since_last_ai_reply: timedelta = current_time - last_ai_reply_time
        silence_duration_since_last_user_reply: timedelta = current_time - last_user_reply_time
        self.logger.debug(f"Silence duration since last AI reply: {timedelta_to_text(silence_duration_since_last_ai_reply)}, \
            since last user reply: {timedelta_to_text(silence_duration_since_last_user_reply)}"
        )
        
        #  判断生理是否允许主动说话
        if not self._update_and_check_urge(current_time, last_user_reply_time):
            self.logger.info("No strong urge to speak detected. Skipping active speaking process.")
            return 
        
        # ==========================================================
        # 阈值突破！身体发出强烈信号："我好无聊/我想说话"
        # ==========================================================
        self.logger.info(">>> Biological Drive Threshold Reached! Waking up LLM... <<<")
        
        # 3. 调用大脑层，决定是否主动说话
        response: ActiveResponse = self._execute_brain_decision(last_interaction_time, last_speaker)
        
        should_speak: bool = response.should_speak
        
        if should_speak:
            # 决定主动说话
            self._active_speak(response)
        else:
            # 决定不说话
            self._no_speak()
            
        self.logger.info("System tick processing completed.")
        
        
    def _execute_brain_decision(self, last_interaction_time: datetime, last_speaker: str) -> ActiveResponse:
        """ 调用大脑层，决定是否主动说话 """
        # 准备传给 LLM 的“感觉描述”
        try:
            internal_sensation = self.psyche_system.get_internal_state_description()
            self.logger.info(f"Internal Sensation: {internal_sensation}")
            
            # 3.5 感知当前环境
            cur_envs: EnvironmentInformation = self.l0.sensory_processor.active_perception_envs()
            current_time = datetime.fromtimestamp(cur_envs.time_envs.current_time)
            silence_duration = current_time - last_interaction_time

            # 4. [L1] 决策层
            # 询问大脑："用户很久没说话了，现在是{时间}，你想说点什么吗？"
            cur_mood = self.l3.get_current_mood()
            # 读取近期记忆
            recent_memories = self.session.get_recent_history(limit=self.RECENT_MEMORY_LIMIT)
            # 调用LLM
            response: ActiveResponse = self.l1.decide_to_act(
                silence_duration=silence_duration,
                last_speaker=last_speaker,
                cur_mood=cur_mood,
                cur_envs=cur_envs,
                recent_conversations=recent_memories,
                cur_psyche_state=internal_sensation
            )
            return response
        except Exception as e:
            self.logger.error(f"Error during brain decision execution: {e}", exc_info=True)
            # 出错时默认不说话
            return ActiveResponse(should_speak=False, 
                                  public_reply=DEFAULT_ERROR_PUBLIC_REPLY, 
                                  inner_voice=DEFAULT_ERROR_INNER_THOUGHT, 
                                  mood=DEFAULT_ERROR_MOOD)
        
    def _update_and_check_urge(self, current_time: datetime, last_user_reply_time: datetime) -> bool:
        # 1. 计算时间差 (dt) - 生理模拟需要精确的时间流逝
        dt_seconds = (current_time - self.last_tick_time).total_seconds()
        self.last_tick_time = current_time
        
        # TODO magic 数字，要调整
        # 避免 dt 过大（比如系统休眠后唤醒），限制最大 dt 为 60秒
        dt_seconds = min(dt_seconds, self.MAX_TICK_DT)  
        
        # 2. 构建环境刺激 (Stimuli)
        # 简单判定：如果用户在过去 5 分钟内说过话，就算 "User Present"
        # TODO 未来可以结合 L0 的环境感知结果进行更复杂的判定
        is_user_present = (current_time - last_user_reply_time).total_seconds() < self.USER_PRESENT_TIMEOUT
        
        env = EnvironmentalStimuli(
            current_time=current_time,
            is_user_present=is_user_present
        )
        
        # 3. [L0] 更新生理系统状态
        # update 返回 True 仅代表“身体有冲动”，不代表“必须说话”
        has_urge_to_speak: bool = self.psyche_system.update(dt_seconds, env)
        self.logger.debug(f"[Psyche Tick] {self.psyche_system.state}")
        return has_urge_to_speak

        
    def _active_speak(self, response: ActiveResponse):
        """ 处理决定主动说话的情况 """
        self.logger.info("Elysia decided to initiate conversation.")
        # 回复内容
        msg = ChatMessage(role="Elysia", content=response.public_reply, inner_voice=response.inner_voice)
        
        # 输出
        self.actuator.perform_action(ActionType.SPEECH, msg)
        
        # 记忆更新
        self.session.add_messages(messages=[msg])   # 更新短时记忆(直接加入对话历史)
        self.reflector.on_new_message(msg)  # 发送给 Reflector 以便存入长期记忆(先进入buffer，再提取)
        
        # 生理反馈：释放压力，消耗能量
        self.psyche_system.on_ai_active_speak()
        
        # 更新情绪
        self.l3.update_mood(response.mood)
        
        # 重置主动交互时间，避免连续触发
        # 不需要手动重置了，因为 add_messages 会自动更新 SessionState
        
        
    def _no_speak(self):
        """处理决定不说话的情况"""
        #  AI 决定克制冲动 (Rational Suppression)
        # 可能是因为太晚了，或者觉得没话题
        self.logger.info("Elysia felt the urge but decided to STAY SILENT (Suppression).")
        
        # === [ADD] 强制抑制 ===
        # 必须手动降低无聊值，否则下一个 Tick (10秒后) 又会触发，导致死循环
        self.psyche_system.suppress_drive()