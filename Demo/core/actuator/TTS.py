from types import CoroutineType
from typing import Any, AsyncGenerator, Protocol
import httpx
from dataclasses import dataclass

@dataclass
class ServiceConfig:
    """服务配置类"""
    # TTS配置
    tts_base_url: str = "http://localhost:9880"
    tts_ref_audio_path: str = "/home/yomu/Elysia/ref.wav"
    tts_prompt_text: str = "我的话，嗯哼，更多是靠少女的小心思吧~看看你现在的表情，好想去那里。"
    

class AudioGenerateHandler:
    """音频处理类"""

    def __init__(self, config: ServiceConfig= ServiceConfig()):
        self.config = config
        self.tts_client = httpx.AsyncClient(base_url=config.tts_base_url,timeout=120)

    @staticmethod
    def clean_text_from_brackets(text: str) -> str:
        """移除文本中的括号和标记内容"""
        import re
        cleaned = re.sub(r'\[.*?\]', '', text)  # 移除肢体动作描写[]
        cleaned = re.sub(r'<.*?>', '', cleaned)  # 移除面部表情描写<>
        cleaned = re.sub(r'<<.*?>>', '', cleaned)  # 移除心情描写<<>>
        cleaned = re.sub(r'\(.*?\)', '', cleaned)  # 移除语气标记()
        return cleaned.strip()
    
    async def generate_tts_stream(self, text: str):
        """生成 TTS 音频流"""
        if not text:
            raise ValueError("Text is required")

        # 清理文本
        text = self.clean_text_from_brackets(text)
        
        async def relay_tts():
            try:
                async with self.tts_client.stream("POST", "/tts", json={
                    "text": text,
                    "text_lang": "zh",
                    "ref_audio_path": self.config.tts_ref_audio_path,
                    "prompt_lang": "zh",
                    "prompt_text": self.config.tts_prompt_text,
                    "top_k": 5,
                    "top_p": 1.0,
                    "temperature": 1.0,
                    "text_split_method": "cut5",
                    "batch_size": 1,
                    "batch_threshold": 0.75,
                    "speed_factor": 1.0,
                    "split_bucket": True,
                    "fragment_interval": 0.3,
                    "seed": -1,
                    "media_type": "wav",
                    "streaming_mode": True,
                    "parallel_infer": True,
                    "repetition_penalty": 1.35
                }) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        yield chunk
            except Exception as e:
                print(f"TTS 中转流式失败: {e}")
                raise e
        
        return relay_tts()
    

class TTSLocalClient(Protocol):
    """文本转语音客户端接口"""
    async def synthesize_text_full(self, text: str)->AsyncGenerator: ...
    async def synthesize_text_streaming(self, text: str)->AsyncGenerator: ...
    def get_model(self) -> str: ...
    

class GPTSoVitsLocalClient:
    """示例文本转语音客户端"""
    def __init__(self, url = "http://192.168.1.18:9880"):
        self.url = url
        # self.client = httpx.AsyncClient(base_url=self.url)
        self.handler = AudioGenerateHandler(ServiceConfig(tts_base_url=self.url))
        
    async def synthesize_text_full(self, text: str)->AsyncGenerator:
        # 示例实现：返回空字节
        res = await self.handler.generate_tts_stream(text)
        return res
        
    async def synthesize_text_streaming(self, text: str)->AsyncGenerator:
        # 示例实现：返回空字节
        return await self.handler.generate_tts_stream(text)
        
    def get_model(self) -> str:
        return "GPTSoVits-Model-1.0"    

    
class TTSService:
    """示例文本转语音客户端"""
    def __init__(self, clients: list[TTSLocalClient]= [GPTSoVitsLocalClient()]):
        self._clients = clients
        
    async def synthesize_text_full(self, text: str) -> AsyncGenerator:
        # 示例实现：返回空字节
        if not self._clients:
            raise ValueError("No TTS clients available")
        # 这里简单使用第一个客户端
        client = self._clients[0]
        return await client.synthesize_text_full(text)
        
    async def synthesize_text_streaming(self, audio: bytes) -> bytes:
        # 示例实现：返回空字节
        return b""
        
    def get_model(self) -> str:
        return "Example-TTS-Model-1.0"