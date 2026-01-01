"""
配置文件，包含各个模块的配置类定义
遵循原则：
1. 结构与默认值在 dataclass
2. 具体参数在 YAML
3. 密钥在环境变量
"""
from json import load
import os
import yaml
import logging
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Optional, Any, Dict, Type, TypeVar
from dotenv import load_dotenv



# ============================================================================================
# 基础配置类与加载工具
# ============================================================================================

def _load_env(key: str, default: Any = None) -> Any:
    """从环境变量加载配置，如果不存在则返回默认值"""
    load_dotenv()  # 加载 .env 文件
    return os.getenv(key, default)

# ============================================================================================
# 通用配置
# ============================================================================================
@dataclass
class LoggerConfig:
    DEFAULT_LOG_PATH: str = "/home/yomu/Elysia/Demo/log"
    DEFAULT_LOG_LEVEL: str = "INFO"

@dataclass
class DashBoardConfig:
    API_URL: str = "http://localhost:8000"
    REFRESH_RATE: float = 1.0   # 刷新频率，单位秒

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
class ActuatorConfig:
    logger_name: str = "ActuatorLayer"
    
@dataclass
class SystemClockConfig:
    logger_name: str = "SystemClock"
    heartbeat_interval: float = 10.0 # 系统时钟滴答间隔，单位秒

@dataclass
class SessionStateConfig:
    logger_name: str = "SessionState"
    user_name: str = "妖梦"
    role: str = "Elysia"
    session_capacity: int = 100
    inner_capacity: int = 5
    persist_dir: str = "/home/yomu/Elysia/Demo/storage/sessions"
    
@dataclass
class CheckPointManagerConfig:
    logger_name: str = "CheckPointManager"
    checkpoint_file: str = "/home/yomu/Elysia/Demo/storage/runtime_state.json"
    save_interval: float = 30.0  # TODO 自动保存间隔，单位秒，这个参数没有被使用到  后续实现 
    
@dataclass
class PromptManagerConfig:
    logger_name: str = "PromptManager"

@dataclass
class CoreConfig:
    EventBus: EventBusConfig = field(default_factory=EventBusConfig)
    Dispatcher: DispatcherConfig = field(default_factory=DispatcherConfig)
    Actuator: ActuatorConfig = field(default_factory=ActuatorConfig)
    SystemClock: SystemClockConfig = field(default_factory=SystemClockConfig)
    SessionState: SessionStateConfig = field(default_factory=SessionStateConfig)
    CheckPointManager: CheckPointManagerConfig = field(default_factory=CheckPointManagerConfig)
    PromptManager: PromptManagerConfig = field(default_factory=PromptManagerConfig)


# ============================================================================================
# L0 层配置
# ============================================================================================
@dataclass
class SensorLayerConfig:
    logger_name: str = "SensorLayer"
    LLM_API_KEY: str = field(default_factory=lambda: _load_env("DEEPSEEK_API_KEY", ""))
    LLM_URL: str = field(default_factory=lambda: _load_env("DEEPSEEK_API_BASE", "https://api.deepseek.com/"))

@dataclass
class SensorConfig:
    pass

@dataclass
class AmygdalaConfig:
    model: str = "deepseek-chat"
    use_prefix: bool = False
    max_tokens: int = 1500
    temperature: float = 1.2
    stream: bool = False    # TODO 这个参数加上之后静态检查会报错，暂时写死在代码中
    

@dataclass
class PsycheConfig:
    """生理参数配置"""
    max_energy: float = 100.0
    sleep_start_hour: int = 2
    sleep_end_hour: int = 8
    energy_drain_rate: float = 5.0
    energy_recover_rate: float = 15.0
    max_social_battery: float = 100.0
    social_battery_recover_rate: float = 10.0
    boredom_threshold: float = 80.0
    base_boredom_growth: float = 30.0
    cost_speak_active: float = 15.0
    cost_speak_passive: float = 5.0
    relief_boredom_active: float = 50.0
    momentum_multiplier: float = 50.0
    momentum_decay_half_life: float = 10.0
    
    def __dict__(self):
        return {
            "max_energy": self.max_energy,
            "sleep_start_hour": self.sleep_start_hour,
            "sleep_end_hour": self.sleep_end_hour,
            "energy_drain_rate": self.energy_drain_rate,
            "energy_recover_rate": self.energy_recover_rate,
            "max_social_battery": self.max_social_battery,
            "social_battery_recover_rate": self.social_battery_recover_rate,
            "boredom_threshold": self.boredom_threshold,
            "base_boredom_growth": self.base_boredom_growth,
            "cost_speak_active": self.cost_speak_active,
            "cost_speak_passive": self.cost_speak_passive,
            "relief_boredom_active": self.relief_boredom_active,
            "momentum_multiplier": self.momentum_multiplier,
            "momentum_decay_half_life": self.momentum_decay_half_life
        }

@dataclass
class InternalState:
    """当前生理数值状态"""
    energy: float = 100.0
    social_battery: float = 100.0
    boredom: float = 0.0
    mood: float = 0.0
    conversation_momentum: float = 0.0
    
    def __dict__(self):
        return {
            "energy": self.energy,
            "social_battery": self.social_battery,
            "boredom": self.boredom,
            "mood": self.mood,
            "conversation_momentum": self.conversation_momentum
        }

    def __str__(self):
        return (f"🔋Energy: {self.energy:.1f} | ⚡Social: {self.social_battery:.1f} | "
                f"🥱Boredom: {self.boredom:.1f} | 🌈Mood: {self.mood:.1f} | 🔥Momentum: {self.conversation_momentum:.0f}")

@dataclass
class PsycheSystemConfig:
    logger_name: str = "PsycheSystem"
    psyche_config: PsycheConfig = field(default_factory=PsycheConfig)
    internal_state: InternalState = field(default_factory=InternalState)

@dataclass
class L0Config:
    SensorLayer: SensorLayerConfig = field(default_factory=SensorLayerConfig) # YAML key is L0
    Sensor: SensorConfig = field(default_factory=SensorConfig)
    Amygdala: AmygdalaConfig = field(default_factory=AmygdalaConfig)
    PsycheSystem: PsycheSystemConfig = field(default_factory=PsycheSystemConfig)

# ============================================================================================
# L1 层配置
# ============================================================================================
# 主动生成 LLM 配置
@dataclass
class ActiveGenerateConfig:
    model: str = "deepseek-chat"
    use_prefix: bool = True
    stream:  bool = False
    temperature: float = 1.3
    max_tokens: int = 2000
    
# 正常对话生成 LLM 配置
@dataclass
class NormalGenerateConfig:
    model: str = "deepseek-chat"
    use_prefix: bool = True
    stream:  bool = False
    temperature: float = 1.3
    max_tokens: int = 1500

@dataclass
class BrainLayerConfig:
    logger_name: str = "BrainLayer"
    LLM_API_KEY: str = field(default_factory=lambda: _load_env("DEEPSEEK_API_KEY", ""))
    LLM_URL: str = field(default_factory=lambda: _load_env("DEEPSEEK_API_BETA", "https://api.deepseek.com/beta"))
    ActiveGenerate: ActiveGenerateConfig = field(default_factory=ActiveGenerateConfig)
    NormalGenerate: NormalGenerateConfig = field(default_factory=NormalGenerateConfig)

@dataclass
class L1Config:
    BrainLayer: BrainLayerConfig = field(default_factory=BrainLayerConfig)

# ============================================================================================
# L2 层配置
# ============================================================================================
@dataclass
class MemoryLayerConfig:
    logger_name: str = "MemoryLayer"
    micro_memory_collection: str = "micro_memory"
    macro_memory_collection: str = "macro_memory"
    MILVUS_URI: str = field(default_factory=lambda: _load_env("MILVUS_URI", "http://localhost:19530"))
    MILVUS_TOKEN: str = field(default_factory=lambda: _load_env("MILVUS_TOKEN", "root:Milvus"))


@dataclass
class L2Config:
    MemoryLayer: MemoryLayerConfig = field(default_factory=MemoryLayerConfig)

# ============================================================================================
# L3 层配置
# ============================================================================================
@dataclass
class L3Config:
    logger_name: str = "PersonaLayer"

# ============================================================================================
# Reflector 配置
# ============================================================================================
@dataclass
class MicroReflectorConfig:
    logger_name: str = "MicroReflector"
    conversation_split_gap_seconds: float = 1800.0
    milvus_collection: str = "micro_memory"
    model: str = "deepseek-chat"
    use_prefix: bool = True
    temperature: float = 1.2
    max_tokens: int = 1500
    LLM_API_KEY: str = field(default_factory=lambda: _load_env("DEEPSEEK_API_KEY", ""))
    LLM_URL: str = field(default_factory=lambda: _load_env("DEEPSEEK_API_BETA", "https://api.deepseek.com/beta"))

@dataclass
class MacroReflectorConfig:
    logger_name: str = "MacroReflector"
    gather_memory_time_interval_seconds: int = 86400
    milvus_collection: str = "macro_memory"
    model: str = "deepseek-chat"
    use_prefix: bool = True
    temperature: float = 1.0
    max_tokens: int = 3000
    LLM_API_KEY: str = field(default_factory=lambda: _load_env("DEEPSEEK_API_KEY", ""))
    LLM_URL: str = field(default_factory=lambda: _load_env("DEEPSEEK_API_BETA", "https://api.deepseek.com/beta"))

@dataclass
class MemoryReflectorConfig:
    MicroReflector: MicroReflectorConfig = field(default_factory=MicroReflectorConfig)
    MacroReflector: MacroReflectorConfig = field(default_factory=MacroReflectorConfig)

@dataclass
class ReflectorConfig:
    logger_name: str = "Reflector"
    micro_threshold: int = 10
    macro_interval_seconds: int = 120 # Macro Reflector 每隔多少秒触发一次反思
    worker_sleep_interval: float = 2.0
    MemoryReflector: MemoryReflectorConfig = field(default_factory=MemoryReflectorConfig)

# ============================================================================================
# Server 配置
# ============================================================================================
@dataclass
class AppConfig:
    logger_name: str = "ElysiaServer"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

@dataclass
class ServerConfig:
    App: AppConfig = field(default_factory=AppConfig)

# ============================================================================================
# 全局配置入口
# ============================================================================================
@dataclass
class GlobalConfig:
    Logger: LoggerConfig = field(default_factory=LoggerConfig)
    DashBoard: DashBoardConfig = field(default_factory=DashBoardConfig)
    Core: CoreConfig = field(default_factory=CoreConfig)
    L0: L0Config = field(default_factory=L0Config)
    L1: L1Config = field(default_factory=L1Config)
    L2: L2Config = field(default_factory=L2Config)
    L3: L3Config = field(default_factory=L3Config)
    Reflector: ReflectorConfig = field(default_factory=ReflectorConfig)
    Server: ServerConfig = field(default_factory=ServerConfig)

    @classmethod
    def load(cls, yaml_path: str) -> "GlobalConfig":
        """
        加载配置：
        1. 实例化默认配置
        2. 读取 YAML 文件覆盖默认值
        3. 环境变量已经在 default_factory 中处理 (如果 YAML 中没有覆盖，则使用 env 或 默认值)
           注意：如果 YAML 中显式写了空字符串或特定值，会覆盖 default_factory 的逻辑。
           为了确保环境变量优先级最高（针对密钥），我们需要在加载 YAML 后再次检查关键字段，
           或者在 YAML 加载逻辑中处理。
           
           这里采用策略：
           - 默认值：代码中定义
           - YAML：覆盖默认值
           - 环境变量：覆盖 YAML 和默认值 (针对特定字段)
        """
        config = cls()
        
        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f)
                    if yaml_data:
                        _update_dataclass_from_dict(config, yaml_data)
            except Exception as e:
                print(f"Error loading config file {yaml_path}: {e}")
        else:
            print(f"Warning: Config file {yaml_path} not found. Using defaults.")

        # 强制从环境变量覆盖敏感信息 (如果环境变量存在)
        _override_secrets_from_env(config)
        
        return config

def _update_dataclass_from_dict(instance: Any, data: Dict[str, Any]):
    """递归更新 dataclass 实例"""
    if not is_dataclass(instance):
        return

    for field_info in fields(instance):
        key = field_info.name
        if key in data:
            value = data[key]
            field_value = getattr(instance, key)
            
            if is_dataclass(field_value) and isinstance(value, dict):
                _update_dataclass_from_dict(field_value, value)
            else:
                # 简单的类型转换可以加在这里，目前直接赋值
                setattr(instance, key, value)

def _override_secrets_from_env(config: GlobalConfig):
    """
    强制使用环境变量覆盖敏感配置
    """
    # Helper to set if env exists
    def set_if_env(obj, attr, env_key):
        val = os.getenv(env_key)
        if val:
            setattr(obj, attr, val)

    # L0
    set_if_env(config.L0.SensorLayer, 'LLM_API_KEY', 'DEEPSEEK_API_KEY')
    set_if_env(config.L0.SensorLayer, 'LLM_URL', 'DEEPSEEK_API_BASE')
    
    # L1
    set_if_env(config.L1.BrainLayer, 'LLM_API_KEY', 'DEEPSEEK_API_KEY')
    set_if_env(config.L1.BrainLayer, 'LLM_URL', 'DEEPSEEK_API_BETA')
    
    # L2
    set_if_env(config.L2.MemoryLayer, 'MILVUS_URI', 'MILVUS_URI')
    set_if_env(config.L2.MemoryLayer, 'MILVUS_TOKEN', 'MILVUS_TOKEN')
    
    # Reflector
    set_if_env(config.Reflector.MemoryReflector.MicroReflector, 'LLM_API_KEY', 'DEEPSEEK_API_KEY')
    set_if_env(config.Reflector.MemoryReflector.MicroReflector, 'LLM_URL', 'DEEPSEEK_API_BETA')
    set_if_env(config.Reflector.MemoryReflector.MacroReflector, 'LLM_API_KEY', 'DEEPSEEK_API_KEY')
    set_if_env(config.Reflector.MemoryReflector.MacroReflector, 'LLM_URL', 'DEEPSEEK_API_BETA')


# 全局单例
# 使用方法: from Config import config
# config = GlobalConfig.load("config.yaml") 
# 为了避免导入时立即加载导致路径问题，建议在 main.py 中显式加载，或者这里使用懒加载
# 这里提供一个默认加载，假设 config.yaml 在同级目录
current_dir = os.path.dirname(os.path.abspath(__file__))
default_yaml_path = os.path.join(current_dir, "config.yaml")

# 预定义一个 config 对象，但需要在应用启动时调用 load 刷新
global_config = GlobalConfig() 

def init_config(yaml_path: str = default_yaml_path):
    global global_config
    global_config = GlobalConfig.load(yaml_path)