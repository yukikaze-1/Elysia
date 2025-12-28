"""
配置文件，包含各个模块的配置类定义
"""
from dataclasses import dataclass
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings, 
    SettingsConfigDict, 
    PydanticBaseSettingsSource,
    YamlConfigSettingsSource
)
import yaml

# ============================================================================================
# 通用配置
# ============================================================================================
@dataclass
class LoggerConfig:
    DEFAULT_LOG_PATH: str = "/home/yomu/Elysia/Demo/Log"
    DEFAULT_LOG_LEVEL: str = "logging.INFO"
    
    
@dataclass
class DashBoardConfig:
    API_URL: str = "http://localhost:8000"
    REFRESH_RATE: float = 1.0  # 刷新频率(秒)
 
# ============================================================================================
# 核心配置
# ============================================================================================
    
@dataclass
class EventBusConfig:
    logger_name: str = "EventBus"
    
@dataclass
class DispatcherConfig:
    logger_name: str = "Dispatcher"
    
@dataclass
class CoreConfig:
    event_bus: EventBusConfig = EventBusConfig()
    dispatcher: DispatcherConfig = DispatcherConfig()

# ============================================================================================
# L0 层配置
# ============================================================================================    
@dataclass
class SensorLayerConfig:
    logger_name: str = "SensorLayer"
    heartbeat_interval: float = 10.0  # 心跳间隔，单位秒
    model: str = "deepseek-chat" 
    use_prefix: bool = True
    max_tokens: int = 1500
    temperature: float = 1.2
    LLM_API_KEY: str = ""  # TODO 放在 .env 文件中
    LLM_URL: str = "https://api.deepseek.com/beta"  # TODO 放在 .env 文件中
    
@dataclass
class SensorConfig:
    pass

@dataclass
class AmygdalaConfig:
    pass


@dataclass
class PsycheConfig:
    """
    生理参数配置表 (Game Design / Tuning)
    调整这里的数值可以改变 AI 的性格 (Elysia 的体质)
    """
    # === 基础代谢 ===
    max_energy: float = 100.0
    sleep_start_hour: int = 2   # 凌晨 2 点开始犯困
    sleep_end_hour: int = 8     # 早上 8 点起床
    energy_drain_rate: float = 5.0  # 每小时自然消耗的精力
    energy_recover_rate: float = 15.0 # 睡眠时每小时恢复的精力

    # === 社交属性 ===
    max_social_battery: float = 100.0
    social_battery_recover_rate: float = 10.0 # 独处时每小时恢复的电量
    
    # === 表达欲 (驱动力) ===
    boredom_threshold: float = 80.0  # 超过这个值尝试说话
    base_boredom_growth: float = 30.0 # 每小时无聊值增长的基础速度 (话唠程度)
    
    # === 消耗成本 ===
    cost_speak_active: float = 15.0  # 主动说话消耗的社恐电量
    cost_speak_passive: float = 5.0  # 被动回复消耗的社恐电量
    relief_boredom_active: float = 50.0 # 主动说话释放的无聊值
    
    # === [ADD] 对话惯性参数 ===
    # 刚刚结束对话时的惯性倍率 (例如 10 倍速增长)
    momentum_multiplier: float = 50.0 
    # 惯性衰减半衰期 (分钟)：多少分钟后惯性消失一半
    momentum_decay_half_life: float = 10.0
    
    
@dataclass
class InternalState:
    """当前的生理数值状态"""
    energy: float = 100.0        # 精力 (0~100)
    social_battery: float = 100.0 # 社交电量 (0~100)
    boredom: float = 0.0         # 表达欲/无聊 (0~100+)
    mood: float = 0.0            # 心情 (-100~100)
    conversation_momentum: float = 0.0  # 对话惯性/热度 1.0 表示刚刚还在热聊，0.0 表示早已冷却
    
@dataclass
class L0Config:
    sensor_layer: SensorLayerConfig = SensorLayerConfig()
    sensor: SensorConfig = SensorConfig()
    amygdala: AmygdalaConfig = AmygdalaConfig()
    psyche: PsycheConfig = PsycheConfig()
    
# ============================================================================================
# L1 层配置
# ============================================================================================


@dataclass
class BrainLayerConfig:
    model: str = "deepseek-chat"
    use_prefix: bool = True
    temperature: float = 1.0
    max_tokens: int = 2000
    LLM_API_KEY: str = ""  # TODO 放在 .env 文件中
    LLM_URL: str = "https://api.deepseek.com/beta"  # TODO 放在 .env 文件中
    
    
@dataclass
class L1Config:
    brain_layer_config: BrainLayerConfig = BrainLayerConfig()
    
# ============================================================================================
# L2 层配置
# ============================================================================================

@dataclass
class MemoryLayerConfig:
    logger_name: str = "MemoryLayer"
    micro_memory_collection: str = "micro_memory"
    macro_memory_collection: str = "macro_memory"
    MILVUS_URI: str = "http://localhost:19530" # TODO 放在 .env 文件中
    MILVUS_TOKEN: str = "root:Milvus" # TODO 放在 .env 文件中
    

@dataclass
class SessionStateConfig:
    logger_name: str = "SessionState"
    user_name: str = "妖梦"
    role: str = "Elysia"
    session_capacity: int = 30
    inner_capacity: int = 3
    persist_dir: str = "/home/yomu/Elysia/Demo/storage/sessions"


@dataclass
class L2Config:
    memory_layer_config: MemoryLayerConfig = MemoryLayerConfig()
    session_state_config: SessionStateConfig = SessionStateConfig()
    
# ============================================================================================
# L3 层配置
# ============================================================================================

@dataclass
class L3Config:
    pass


# ============================================================================================
# Reflector 配置
# ============================================================================================

@dataclass
class MicroReflectorConfig:
    logger_name: str = "MicroReflector"
    conversation_split_gap_seconds: float = 1800.0  # 对话切割的时间间隔，单
    milvus_collection: str = "micro_memory"
    model: str = "deepseek-chat"
    use_prefix: bool = True
    temperature: float = 1.2
    max_tokens: int = 1500
    LLM_API_KEY: str = ""  # TODO 放在 .env 文件中
    LLM_URL: str = "https://api.deepseek.com/beta"  # TODO 放在 .env 文件中

@dataclass
class MacroReflectorConfig:
    logger_name: str = "MacroReflector"
    gather_memory_time_interval_seconds: float = 86400.0  # 汇集记忆的时间间隔，单位秒，默认一天
    milvus_collection: str = "macro_memory"
    model: str = "deepseek-chat"
    use_prefix: bool = True
    temperature: float = 1.0
    max_tokens: int = 3000
    LLM_API_KEY: str = ""  # TODO 放在 .env 文件中
    LLM_URL: str = "https://api.deepseek.com/beta"  # TODO 放在 .env 文件中


@dataclass
class MemoryReflectorConfig:
    micro_reflector: MicroReflectorConfig = MicroReflectorConfig()
    macro_reflector: MacroReflectorConfig = MacroReflectorConfig()
    
    
@dataclass
class ReflectorConfig:
    logger_name: str = "Reflector"
    micro_threshold: int = 10  # 微观反思触发阈值(10条 ChatMessage)(约等于5轮对话)
    macro_interval_seconds: int = 86400  # 宏观反思触发间隔，单位秒（默认24小时）
    work_sleep_interval: float = 2.0  # 反思工作线程休眠间隔，单位秒
    
    memory_reflector: MemoryReflectorConfig = MemoryReflectorConfig()
    
    
# ============================================================================================
# Server配置    
# ============================================================================================

@dataclass
class AppConfig:
    logger_name: str = "ElysiaServer"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    log_level: str = "info"