"""
系统心跳处理器：处理定时心跳事件，包括保存会话和主动发起对话
"""

from datetime import datetime, timedelta
import logging
from Core.Schema import Event, ChatMessage
from Core.ActuatorLayer import ActuatorLayer, ActionType
from Layers.PsycheSystem import PsycheSystem, EnvironmentalStimuli
from Layers.L0.Sensor import  EnvironmentInformation
from Layers.L0 import SensorLayer
from Layers.L1 import BrainLayer, ActiveResponse, NormalResponse
from Core.SessionState import SessionState
from Layers.L2 import MemoryLayer
from Layers.L3 import PersonaLayer
from Workers.Reflector.Reflector import Reflector
from Core.CheckPointManager import CheckpointManager
from Logger import setup_logger
from Utils import timedelta_to_text
from typing import Literal
from Core.Handlers.BaseHandler import BaseHandler


class SystemTickHandler(BaseHandler):
    def __init__(self, actuator: ActuatorLayer, 
                    psyche_system: PsycheSystem,
                    l0: SensorLayer,
                    l1: BrainLayer,
                    session: SessionState,
                    l2: MemoryLayer,
                    l3: PersonaLayer,
                    reflector: Reflector,
                    checkpoint_manager: CheckpointManager
                 ):
        self.logger: logging.Logger = setup_logger("SystemTickHandler")
        self.actuator = actuator
        self.psyche_system = psyche_system
        self.l0 = l0
        self.l1 = l1
        self.session = session
        self.l2 = l2
        self.l3 = l3
        self.reflector = reflector
        self.checkpoint_manager = checkpoint_manager
        
        # === 主动性控制参数 ===
        # 记录上次交互时间
        # TODO 这些运行时参数应该持久化到文件中
        tmp_time = datetime.now()
        self.last_interaction_time: datetime = tmp_time     # AI 或用户最后一次说话的时间
        self.last_ai_reply_time: datetime = tmp_time        # AI最后一次说话的时间
        self.last_user_reply_time: datetime = tmp_time      # 用户最后一次说话的时间
        self.last_speaker: Literal['Elysia', '妖梦'] = "Elysia"  # 记录上次发言者，初始为 AI

        # 用于计算两次心跳之间的时间差 (dt)
        self.last_tick_time = datetime.now()
        
        
    def handle(self, event: Event):
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
        self.logger.info("---------------------------------------------------")
        current_time: datetime = datetime.fromtimestamp(event.timestamp)
        self.logger.info(f"System tick received at {current_time.isoformat()}")
        
        # 0. 计算沉默时长
        silence_duration_since_last_ai_reply: timedelta = current_time - self.last_ai_reply_time
        silence_duration_since_last_user_reply: timedelta = current_time - self.last_user_reply_time
        self.logger.info(f"Silence duration since last AI reply: {timedelta_to_text(silence_duration_since_last_ai_reply)}, \
            since last user reply: {timedelta_to_text(silence_duration_since_last_user_reply)}"
        )
        
        # 1. 计算时间差 (dt) - 生理模拟需要精确的时间流逝
        dt_seconds = (current_time - self.last_tick_time).total_seconds()
        self.last_tick_time = current_time
        
        # 避免 dt 过大（比如系统休眠后唤醒），限制最大 dt 为 60秒
        dt_seconds = min(dt_seconds, 60)  
        
        # 2. 构建环境刺激 (Stimuli)
        # 简单判定：如果用户在过去 5 分钟内说过话，就算 "User Present"
        is_user_present = (current_time - self.last_user_reply_time).total_seconds() < 300
        
        env = EnvironmentalStimuli(
            current_time=current_time,
            is_user_present=is_user_present
        )
        
        # 3. [L0] 更新生理系统状态
        # update 返回 True 仅代表“身体有冲动”，不代表“必须说话”
        has_urge_to_speak = self.psyche_system.update(dt_seconds, env)
        self.logger.info(f"[Psyche Tick] {self.psyche_system.state}")
        
        if not has_urge_to_speak:
            self.logger.info("No strong urge to speak detected. Skipping active speaking process.")
            return
        
        # ==========================================================
        # 阈值突破！身体发出强烈信号："我好无聊/我想说话"
        # ==========================================================
        self.logger.info(">>> Biological Drive Threshold Reached! Waking up LLM... <<<")
        
        # 4. 准备传给 LLM 的“感觉描述”
        internal_sensation = self.psyche_system.get_internal_state_description()
        self.logger.info(f"Internal Sensation: {internal_sensation}")
        
        
        # 3.5 感知当前环境
        cur_envs: EnvironmentInformation = self.l0.sensory_processor.active_perception_envs()
        current_time = datetime.fromtimestamp(cur_envs.time_envs.current_time)
        silence_duration = current_time - self.last_interaction_time

        # 4. [L1] 决策层
        # 询问大脑："用户很久没说话了，现在是{时间}，你想说点什么吗？"
        cur_mood = self.l3.get_current_mood()
        # 读取近期记忆
        recent_memories = self.session.get_recent_history(limit=10)
        # 调用LLM
        response: ActiveResponse = self.l1.decide_to_act(
            silence_duration=silence_duration,
            last_speaker=self.last_speaker,
            cur_mood=cur_mood,
            cur_envs=cur_envs,
            recent_conversations=recent_memories,
            cur_psyche_state=internal_sensation
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
            self.session.add_messages(messages=[msg])   # 更新短时记忆(直接加入对话历史)
            self.reflector.on_new_message(msg)  # 发送给 Reflector 以便存入长期记忆(先进入buffer，再提取)
            
            # === [ADD] 生理反馈：释放压力，消耗能量 ===
            self.psyche_system.on_ai_active_speak()
            
            # 8. 更新情绪
            self.l3.update_mood(response.mood)
            
            # 9. 重置主动交互时间，避免连续触发
            tmp_time = datetime.now()
            self.last_ai_reply_time = tmp_time
            self.last_interaction_time = tmp_time
            self.last_speaker = "Elysia"
        else:
            # 7. AI 决定克制冲动 (Rational Suppression)
            # 可能是因为太晚了，或者觉得没话题
            self.logger.info("Elysia felt the urge but decided to STAY SILENT (Suppression).")
            
            # === [ADD] 强制抑制 ===
            # 必须手动降低无聊值，否则下一个 Tick (10秒后) 又会触发，导致死循环
            self.psyche_system.suppress_drive()
            
        self.logger.info("System tick processing completed.")