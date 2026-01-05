
from config.Config import STTConfig
from Logger import setup_logger
from typing import Protocol, overload, List, Dict, Any
import httpx


class STTClient(Protocol):
    """语音转文本客户端接口"""
    def transcribe_file(self, audio_file_path: str) -> str: ...
    def transcribe_bytes(self, audio: bytes) -> str: ...
    def get_model(self) -> str: ...
    
    
class SenseVoiceLocalClient:
    """示例语音转文本客户端"""
    def __init__(self, url: str="http://192.168.1.18:20042"):
        self.url = url
        self.stt_client = httpx.AsyncClient(base_url=self.url)
        
    async def transcribe_file(self, audio_file_path: str) -> str:
        with open(audio_file_path, 'rb') as f:
            audio_data = f.read()
        res = await self._call_api(audio_data)
        if res and 'text' in res:
            return res['text']
        return ""
        
    async def transcribe_bytes(self, audio: bytes) -> str:
        res = await self._call_api(audio)
        if res and 'text' in res:
            return res['text']
        return ""
        
    def get_model(self) -> str:
        return "SenseVoice-Model-1.0"
    
    async def _call_api(self, audio_data: bytes) -> Dict[str, Any] | None:
        try:
            response = await self.stt_client.post(
                url="/predict/sentence", 
                files={"file": audio_data},
                timeout=60
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
        

class STTService:
    """语音转文本模块 (Speech-To-Text)"""
    def __init__(self, config: STTConfig, clients: List[STTClient]):
        self.config = config
        self._clients = clients
        self.logger = setup_logger(self.config.logger_name)
        self.logger.info("STT module initialized with config: %s", self.config)
    
    
    def transcribe_file(self, audio_file_path: str) -> str:
        """将音频文件转换为文本"""
        self.logger.info(f"Transcribing audio file: {audio_file_path}")
        return "Transcribed text from audio."  # TODO 实现实际的 STT 功能
    
    def get_models(self) -> list[str]:
        """获取可用的 STT 模型列表"""
        models = []
        for client in self._clients:
            models.append(client.get_model())
        return models