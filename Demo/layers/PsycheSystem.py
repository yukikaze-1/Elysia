import math
from dataclasses import dataclass, field
from datetime import datetime
from Logger import setup_logger
import logging

# ==========================================
# 1. 配置与数据结构
# ==========================================

# @dataclass
# class PsycheConfig:
#     """
#     生理参数配置表 (Game Design / Tuning)
#     调整这里的数值可以改变 AI 的性格 (Elysia 的体质)
#     """
#     # === 基础代谢 ===
#     max_energy: float = 100.0
#     sleep_start_hour: int = 2   # 凌晨 2 点开始犯困
#     sleep_end_hour: int = 8     # 早上 8 点起床
#     energy_drain_rate: float = 5.0  # 每小时自然消耗的精力
#     energy_recover_rate: float = 15.0 # 睡眠时每小时恢复的精力

#     # === 社交属性 ===
#     max_social_battery: float = 100.0
#     social_battery_recover_rate: float = 10.0 # 独处时每小时恢复的电量
    
#     # === 表达欲 (驱动力) ===
#     boredom_threshold: float = 80.0  # 超过这个值尝试说话
#     base_boredom_growth: float = 30.0 # 每小时无聊值增长的基础速度 (话唠程度)
    
#     # === 消耗成本 ===
#     cost_speak_active: float = 15.0  # 主动说话消耗的社恐电量
#     cost_speak_passive: float = 5.0  # 被动回复消耗的社恐电量
#     relief_boredom_active: float = 50.0 # 主动说话释放的无聊值
    
#     # === [ADD] 对话惯性参数 ===
#     # 刚刚结束对话时的惯性倍率 (例如 10 倍速增长)
#     momentum_multiplier: float = 50.0 
#     # 惯性衰减半衰期 (分钟)：多少分钟后惯性消失一半
#     momentum_decay_half_life: float = 10.0
    
#     def __dict__(self):
#         return {
#             "max_energy": self.max_energy,
#             "sleep_start_hour": self.sleep_start_hour,
#             "sleep_end_hour": self.sleep_end_hour,
#             "energy_drain_rate": self.energy_drain_rate,
#             "energy_recover_rate": self.energy_recover_rate,
#             "max_social_battery": self.max_social_battery,
#             "social_battery_recover_rate": self.social_battery_recover_rate,
#             "boredom_threshold": self.boredom_threshold,
#             "base_boredom_growth": self.base_boredom_growth,
#             "cost_speak_active": self.cost_speak_active,
#             "cost_speak_passive": self.cost_speak_passive,
#             "relief_boredom_active": self.relief_boredom_active,
#             "momentum_multiplier": self.momentum_multiplier,
#             "momentum_decay_half_life": self.momentum_decay_half_life
#         }


@dataclass
class EnvironmentalStimuli:
    """环境刺激输入"""
    current_time: datetime
    is_user_present: bool = False # 用户是否在线/活跃


# @dataclass
# class InternalState:
#     """当前的生理数值状态"""
#     energy: float = 100.0        # 精力 (0~100)
#     social_battery: float = 100.0 # 社交电量 (0~100)
#     boredom: float = 0.0         # 表达欲/无聊 (0~100+)
#     mood: float = 0.0            # 心情 (-100~100)
#     # === [ADD] 对话惯性/热度 (0.0 ~ 1.0) ===
#     # 1.0 表示刚刚还在热聊，0.0 表示早已冷却
#     conversation_momentum: float = 0.0
    
#     def __str__(self):
#         return (f"🔋Energy: {self.energy:.1f} | ⚡Social: {self.social_battery:.1f} | "
#                 f"🥱Boredom: {self.boredom:.1f} | 🌈Mood: {self.mood:.1f} | 🔥Momentum: {self.conversation_momentum:.0f}")

# ==========================================
# 2. 核心逻辑类
# ==========================================
from config.Config import PsycheSystemConfig, PsycheConfig, InternalState

class PsycheSystem:
    def __init__(self, config: PsycheSystemConfig):
        self.config: PsycheSystemConfig = config
        self.cfg: PsycheConfig = config.psyche_config
        self.state: InternalState = config.internal_state # TODO 这里好像有点问题
        self.logger: logging.Logger = setup_logger(self.config.logger_name)
        
        self.logger.info(">>> PsycheSystem initialized with config:")
        
            
    def get_status(self) -> dict:
        """获取当前状态的字典表示"""
        return {
            "energy": self.state.energy,
            "social_battery": self.state.social_battery,
            "boredom": self.state.boredom,
            "mood": self.state.mood,
            "conversation_momentum": self.state.conversation_momentum,
            "config": self.cfg.__dict__()
        }
        
    def dump_state(self) -> dict:
        """导出当前状态为字典"""
        return {
            "energy": self.state.energy,
            "social_battery": self.state.social_battery,
            "boredom": self.state.boredom,
            "mood": self.state.mood,
            "conversation_momentum": self.state.conversation_momentum
        }
        
        
    def load_state(self, data: dict):
        """从字典加载状态"""
        self.state.energy = data.get("energy", 100.0)
        self.state.social_battery = data.get("social_battery", 100.0)
        self.state.boredom = data.get("boredom", 0.0)
        self.state.mood = data.get("mood", 0.0)
        self.state.conversation_momentum = data.get("conversation_momentum", 0.0)
        
        
    def update(self, dt_seconds: float, env: EnvironmentalStimuli) -> bool:
        """
        核心代谢循环 (System Tick)
        :param dt_seconds: 距离上次 update 过去的时间 (秒)
        :param env: 环境信息
        :return: True 如果产生了强烈的表达冲动 (Need to wake up LLM)
        """
        # 将时间转换为小时单位，方便计算
        dt_hours = dt_seconds / 3600.0
        current_hour = env.current_time.hour
        
        # === [ADD] 更新对话惯性 (自然冷却) ===
        self._update_momentum(dt_hours)
        
        # 1. 更新精力 (Energy) - 昼夜节律
        self._update_energy(dt_hours, current_hour)
        
        # 2. 更新社交电量 (Social Battery) - 缓慢回充
        self._update_social_battery(dt_hours)
        
        # 3. 更新表达欲 (Boredom) - 核心驱动
        self._update_boredom(dt_hours, current_hour, env.is_user_present)
        
        # 4. 更新心情 (Mood) - 情绪回归
        self._update_mood(dt_hours)
        
        # === [CRITICAL CHANGE] 动态阈值计算 ===
        # 基础阈值
        target_threshold = self.cfg.boredom_threshold
        
        # 惯性修正：如果聊得正嗨 (Momentum=1.0)，阈值降低一半！
        # 比如从 80 降到 40。这意味着只要有一点点话头，她就会接下去。
        if self.state.conversation_momentum > 0:
            # 这里的 0.5 是权重，表示最多降低 50% 的门槛
            discount = self.state.conversation_momentum * 0.5 
            target_threshold = target_threshold * (1.0 - discount)
            
        # 打印一下当前的动态阈值，方便调试
        print(f"DEBUG: Boredom={self.state.boredom:.1f} / Threshold={target_threshold:.1f}")
        
        # 5. 检查是否触发阈值
        # 必须满足：无聊值够高 AND 精力够用 (没累趴下)
        should_act = (self.state.boredom >= target_threshold) and \
                     (self.state.energy > 20.0)
                     
        return should_act

    # === 内部代谢逻辑 ===
    
    def _update_momentum(self, dt_hours: float):
        """
        惯性自然衰减：
        模拟话题随时间“凉了”。如果不衰减，AI 会一直处于急躁状态。
        使用指数衰减公式。
        """
        # 简单算法：每分钟衰减一定比例
        # 转换为分钟
        dt_minutes = dt_hours * 60.0
        decay_rate = 0.15 # 每分钟热度下降 15%
        
        self.state.conversation_momentum -= self.state.conversation_momentum * decay_rate * dt_minutes
        self.state.conversation_momentum = max(0.0, self.state.conversation_momentum)
        

    def _update_energy(self, dt_hours: float, current_hour: int):
        """精力代谢：睡觉回血，醒着掉血"""
        is_sleeping_time = self.cfg.sleep_start_hour <= current_hour < self.cfg.sleep_end_hour
        
        if is_sleeping_time:
            # 睡觉中：快速恢复
            self.state.energy += self.cfg.energy_recover_rate * dt_hours
        else:
            # 清醒中：缓慢流失
            self.state.energy -= self.cfg.energy_drain_rate * dt_hours
            
        # 钳制范围 0-100
        self.state.energy = max(0.0, min(100.0, self.state.energy))


    def _update_social_battery(self, dt_hours: float):
        """社交电量：随时间自然恢复"""
        # 只有在精力尚可时才能恢复社交能量
        if self.state.energy > 30:
            self.state.social_battery += self.cfg.social_battery_recover_rate * dt_hours
        self.state.social_battery = max(0.0, min(100.0, self.state.social_battery))


    def _update_boredom(self, dt_hours: float, current_hour: int, is_user_present: bool):
        """
        表达欲更新：Project "Homeostasis" 的核心
        增长速度受到 [精力] 和 [社交电量] 的双重压制 (Damping)
        """
        # TODO 这个睡觉时间有点死板，后续可以改成根据环境光线/声音等更动态的判断
        is_sleeping_time = self.cfg.sleep_start_hour <= current_hour < self.cfg.sleep_end_hour
    
        if is_sleeping_time and not is_user_present:
            # 睡觉时基本不涨无聊值 (除非用户打扰)
            base_factor = 0.05 
        else:
            # === 阻尼计算 (Damping) ===
            # 1. 精力因子：精力越低，增长越慢 (0.1 ~ 1.0)
            energy_factor = max(0.1, self.state.energy / 100.0)
            
            # 2. 社交因子：电量越低，增长越慢 (0.0 ~ 1.0)
            # 如果刚刚聊完天(电量低)，这里会接近0，自然实现了"冷却期"
            social_factor = max(0.0, self.state.social_battery / 100.0)
            
            # === [New Code] 加入惯性加成 ===
            # 基础因子
            base_factor = energy_factor * social_factor
        
        # 惯性加成：如果 heat=1.0，增长速度变为原来的 (1 + 20) = 21 倍！
        # 这意味着原本需要 60 分钟满的无聊值，现在只需要 3 分钟
        momentum_bonus = 1.0 + (self.state.conversation_momentum * self.cfg.momentum_multiplier)
        
        final_growth_factor = base_factor * momentum_bonus

        # 计算最终增长
        delta = self.cfg.base_boredom_growth * final_growth_factor * dt_hours
        self.state.boredom += delta
        
        # 无聊值没有上限，越高说明越急，但一般不会超过 120 (会被触发)

    def _update_mood(self, dt_hours: float):
        """情绪回归：时间会冲淡一切情绪"""
        # 情绪自然向 0 (平静) 回归
        decay = 10.0 * dt_hours # 每小时回归 10 点
        if self.state.mood > 0:
            self.state.mood = max(0.0, self.state.mood - decay)
        elif self.state.mood < 0:
            self.state.mood = min(0.0, self.state.mood + decay)
            
        # 负面 buff：如果太累或者太无聊，心情会变差
        if self.state.energy < 20:
            self.state.mood -= 5.0 * dt_hours
        if self.state.boredom > 90:
            self.state.mood -= 10.0 * dt_hours
            
        self.state.mood = max(-100.0, min(100.0, self.state.mood))

    # === 外部交互接口 ===

    def on_user_interaction(self, sentiment_score: float = 0.0):
        """
        当用户说话时调用
        :param sentiment_score: 用户的情绪分 (-1.0 ~ 1.0)，可由 NLP 分析得出
        """
        # 1. 满足了表达欲，无聊清零
        self.state.boredom /= 2.0  # 减半而不是清零，更自然一些
        
        # 2. 社交回血 (用户主动找我，我很开心，甚至可能回血)
        # 这里设定为不消耗，反而稍微恢复一点，因为被在乎了
        self.state.social_battery = min(100.0, self.state.social_battery + 5.0)
        
        # 3. 情绪波动
        self.state.mood += sentiment_score * 20.0 # 简单的共情
        self.state.mood = max(-100.0, min(100.0, self.state.mood))
        
        # === [ADD] 拉满惯性 ===
        # 用户刚说话，现在是“热聊状态”
        self.state.conversation_momentum = 1.0


    def on_ai_active_speak(self):
        """当 AI 决定主动说话时调用"""
        # 1. 释放压力
        self.state.boredom = max(0.0, self.state.boredom - self.cfg.relief_boredom_active)
        
        # 2. 消耗大量社交电量 (Active Action Cost)
        self.state.social_battery -= self.cfg.cost_speak_active
        
        # 3. 消耗少量精力
        self.state.energy -= 2.0
        
        # === [ADD] 维持惯性 ===
        # AI 主动开启话题后，应该期待回复，所以热度依然很高
        # 可以稍微降低一点，或者保持 1.0
        self.state.conversation_momentum = max(0.8, self.state.conversation_momentum)


    def on_ai_passive_reply(self):
        """当 AI 回复用户时调用"""
        # 被动回复消耗较少
        self.state.social_battery -= self.cfg.cost_speak_passive
        self.state.energy -= 1.0

    def suppress_drive(self):
        """
        强制抑制：当 LLM 醒了但决定不说话时调用
        手动降低无聊值，防止死循环触发
        """
        self.state.boredom = max(0.0, self.state.boredom - 20.0)

    # === LLM 接口 ===

    def get_internal_state_description(self) -> str:
        """
        生成给 LLM 看的 System Prompt
        将数值翻译成自然语言
        """
        desc_parts = []
        
        # 1. 翻译精力
        if self.state.energy < 20:
            desc_parts.append("Body: Exhausted, struggling to keep eyes open")
        elif self.state.energy < 50:
            desc_parts.append("Body: Tired, energy is low")
        else:
            desc_parts.append("Body: Energetic and awake")
            
        # 2. 翻译社交状态
        if self.state.social_battery < 20:
            desc_parts.append("Social: Drained, prefers silence or short replies")
        elif self.state.social_battery > 80:
            desc_parts.append("Social: Eager to connect")
            
        # 3. 翻译表达欲
        if self.state.boredom > 90:
            desc_parts.append("Drive: Desperate for attention, feels ignored")
        elif self.state.boredom > 50:
            desc_parts.append("Drive: Slightly bored, wants to chat")
            
        # 4. 翻译心情
        if self.state.mood > 30:
            desc_parts.append("Emotion: Happy and positive")
        elif self.state.mood < -30:
            desc_parts.append("Emotion: Feeling down/gloomy")
            
        return " | ".join(desc_parts)

