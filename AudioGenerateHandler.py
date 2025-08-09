import re
import json
import base64
import httpx
from ServiceConfig import ServiceConfig  

class AudioGenerateHandler:
    """音频处理类"""

    def __init__(self, config: ServiceConfig):
        self.config = config
        self.tts_client = httpx.AsyncClient(base_url=config.tts_base_url)

    @staticmethod
    def clean_text_from_brackets(text: str) -> str:
        """移除文本中的括号和标记内容"""
        cleaned = re.sub(r'\[.*?\]', '', text)  # 移除肢体动作描写
        cleaned = re.sub(r'<.*?>', '', cleaned)  # 移除面部表情描写
        cleaned = re.sub(r'<<.*?>>', '', cleaned)  # 移除心情描写
        cleaned = re.sub(r'\(.*?\)', '', cleaned)  # 移除语气标记
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
    
    
    async def _stream_tts_wav(self, text: str):
        # GPTSoVits 需要的请求参数
        payload = {
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
        }
        
        try:
            async with self.tts_client.stream("POST", "/tts", json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    yield chunk
        except Exception as e:
            print(f"TTS 流式处理失败: {e}")
            yield None


    async def _stream_tts_audio(self, text: str):
        """流式音频生成，目前tts 服务端采用的是 wav格式"""
        # GPTSoVits 需要的请求参数
        payload = {
            "text": text,
            "text_lang": "zh", 
            "ref_audio_path": self.config.tts_ref_audio_path,
            "prompt_lang": "zh",
            "prompt_text": self.config.tts_prompt_text,
            "text_split_method": "cut5",
            "batch_size": 20,
            "media_type": "ogg",
            "streaming_mode": True
        }
        
        try:
            response = await self.tts_client.request(
                method="POST",
                url="/tts",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=60.0
            )
            response.raise_for_status()
            
            # 使用流式响应
            async for chunk in response.aiter_bytes(chunk_size=8192):
                if chunk:
                    yield chunk
                    
        except Exception as e:
            print(f"TTS 流式处理失败: {e}")
            yield None