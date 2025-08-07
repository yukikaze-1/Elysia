import httpx

from typing import Dict, Any
from ServiceConfig import ServiceConfig

class AudioRecognizeHandler:
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.stt_client = httpx.AsyncClient(base_url=self.config.stt_base_url)
        
        
    async def recognize_audio(self, audio_data: bytes) -> Dict[str, Any] | None:
        """识别音频数据并返回文本"""
        try:
            response = await self.stt_client.post(
                url="/predict/sentence", 
                files={"file": audio_data}
            )
            response.raise_for_status()
            result = response.json()
            if result.get('result'):
                print("   ✅ 音频识别成功")
                return result['result']
            else:
                print("   ⚠️  未返回识别结果")
                return 
        except httpx.HTTPStatusError as e:
            print(f"   ⚠️  音频识别失败: {e}")
            return 
        except Exception as e:
            print(f"   ⚠️  发生错误: {e}")
            return 