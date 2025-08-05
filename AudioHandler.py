import re
import json
import base64
import httpx
from ServiceConfig import ServiceConfig  # 假设 ServiceConfig 是一个配置类，包含

class AudioHandler:
    """音频处理类"""

    def __init__(self, config: ServiceConfig, tts_client: httpx.AsyncClient):
        self.tts_client = tts_client
        self.config = config

    @staticmethod
    def clean_text_from_brackets(text: str) -> str:
        """移除文本中的括号和标记内容"""
        cleaned = re.sub(r'\[.*?\]', '', text)  # 移除肢体动作描写
        cleaned = re.sub(r'<.*?>', '', cleaned)  # 移除面部表情描写
        cleaned = re.sub(r'<<.*?>>', '', cleaned)  # 移除心情描写
        cleaned = re.sub(r'\(.*?\)', '', cleaned)  # 移除语气标记
        return cleaned.strip()
    
    async def generate_audio_stream(self, content: str):
        """处理语音生成的通用逻辑"""
        try:
            yield json.dumps({"type": "audio_start", "audio_format": "ogg"}, ensure_ascii=False) + "\n"
            
            async for audio_chunk in self._stream_tts_audio(self.clean_text_from_brackets(content)):
                if audio_chunk:
                    chunk_base64 = base64.b64encode(audio_chunk).decode('utf-8')
                    yield json.dumps({
                        "type": "audio_chunk", 
                        "audio_data": chunk_base64,
                        "chunk_size": len(audio_chunk)
                    }, ensure_ascii=False) + "\n"
            
            yield json.dumps({"type": "audio_end"}, ensure_ascii=False) + "\n"
            
        except Exception as e:
            print(f"语音生成失败: {e}")
            yield json.dumps({'type': 'error', 'error': f'语音生成失败: {str(e)}'}, ensure_ascii=False) + "\n"
    
    async def _stream_tts_audio(self, text: str):
        """真正的流式音频生成"""
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
                "POST", "/tts", json=payload, 
                headers={'Content-Type': 'application/json'}, 
                timeout=60.0
            )
            response.raise_for_status()
            
            async for chunk in response.aiter_bytes(chunk_size=8192):
                if chunk:
                    yield chunk
                    
        except Exception as e:
            print(f"TTS 流式处理失败: {e}")
            yield None