from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv, dotenv_values
from typing import Optional

@dataclass
class ServiceConfig:
    """服务配置类"""
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 11100
    
    # TTS配置
    tts_base_url: str = "http://localhost:9880"
    tts_ref_audio_path: str = "/home/yomu/Elysia/ref.wav"
    tts_prompt_text: str = "我的话，嗯哼，更多是靠少女的小心思吧~看看你现在的表情，好想去那里。"
    
    # STT配置
    stt_base_url: str = "http://localhost:20042"
    
    # 本地模型配置
    ollama_base_url: str = "http://localhost:11434"
    local_model: str = "qwen2.5"
    local_temperature: float = 0.3
    local_num_predict: int = 512
    local_top_p: float = 0.9
    local_repeat_penalty: float = 1.1
    
    # 云端模型配置
    cloud_model: str = "qwen3-235b-a22b-instruct-2507"
    cloud_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    cloud_temperature: float = 0.3
    cloud_max_tokens: int = 2000
    
    def __post_init__(self):
        """初始化后加载环境变量"""
        load_dotenv(find_dotenv())
        env_vars = dotenv_values(".env")
        self.api_key = env_vars.get("QWEN3_API_KEY", "")
        if not self.api_key:
            raise ValueError("API key for QWEN3 is not set in the environment variables.")


# 全局配置实例
_config_instance: Optional[ServiceConfig] = None

def get_service_config() -> ServiceConfig:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ServiceConfig()
    return _config_instance

def set_service_config(config: ServiceConfig) -> None:
    """设置全局配置实例（主要用于测试）"""
    global _config_instance
    _config_instance = config