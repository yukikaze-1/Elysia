import os
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from Memory import Memory, ChatMessage
from Utils import MessageIDGenerator
from RAG import RAG
import httpx
import aiofiles

from typing import Dict, List
import datetime

class Service:
    def __init__(self):
        self.app = FastAPI()
        self.llm_client = httpx.AsyncClient(base_url="http://localhost:11434")
        self.tts_client = httpx.AsyncClient(base_url="http://localhost:9880")
        self.memory = Memory()
        self.rag = RAG()
        self.message_id_generator = MessageIDGenerator()  # 添加ID生成器

    def setup_routes(self):
        """设置 API 路由"""
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy"}

        @self.app.post("/chat/text")
        async def chat(request: Request):
            data = await request.json()
            return await self._chat(data)


    async def _chat(self, data: Dict):
        """处理聊天请求"""
        message: str = data.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")
        
        # 存入用户消息
        # 生成消息 ID
        message_id = await self.message_id_generator.get_next_id()
        user_message = ChatMessage(
            role="user",
            content=message,
            message_id=message_id
        )
        print(f"User message ID: {message_id}, content: {message}")
        await self.memory.insert_chat_message(messages=[user_message])
        
        # 发送给llm
        text_response = await self._post_to_ollama(model="qwen2.5", message=message)
        text = text_response["message"].get("content", "")

        # 存入记忆
        message_id = await self.message_id_generator.get_next_id()
        assistant_message = ChatMessage(
            role="assistant",
            content=text,
            message_id=message_id
        )
        print(f"Assistant message ID: {message_id}, content: {text}")
        await self.memory.insert_chat_message(messages=[assistant_message])
        
        # 生成语音
        audio_response = await self._post_to_tts(text=text)
        
        return {"text": text, "audio": audio_response}


    async def _post_to_ollama(self, 
                              message: str ,
                              model: str = "qwen2.5", 
                              optimized_params: Dict | None = None)->Dict:
        """处理 POST 请求到 Ollama"""
        # 构建请求数据
        data = {
            "model": model, 
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ],
            "stream": False,
            "options": optimized_params or {}  # Ollama 使用 options 字段
        }
        
        try:
            response = await self.llm_client.post("/api/chat",
                                                  json=data, 
                                                  headers={"Content-Type": "application/json"},
                                                  timeout=60.0)
            response.raise_for_status()  # 检查HTTP状态码
            return response.json()
        except httpx.RequestError as e:
            print(f"Request error: {e}")
            raise HTTPException(status_code=500, detail="Failed to connect to LLM service")
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e}")
            raise HTTPException(status_code=500, detail="LLM service returned an error")
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Unexpected error occurred")


    async def _post_to_tts(self, text: str)->str:
        """处理 POST 请求到 TTS 服务"""
        payload = {
            "text": text,
            "text_lang": "zh",
            "ref_audio_path": "/home/yomu/Elysia/ref.wav",
            "prompt_lang": "zh",
            "prompt_text": "我的话，嗯哼，更多是靠少女的小心思吧~看看你现在的表情，好想去那里。",
            "text_split_method": "cut5",
            "batch_size": 20,
            "media_type": "wav",
            "streaming_mode": True
        }
        headers = {'Content-Type': 'application/json'}
        method = "POST"
        save_dir = "/home/yomu/Elysia/tts_output/"

        try:
            # 发起异步请求
            response = await self.tts_client.request(method, "/tts", json=payload, headers=headers, timeout=60.0)

            # 检查 HTTP 响应状态码
            response.raise_for_status()
            
            # 生成唯一的文件名
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S%f")
            filename = os.path.join(save_dir, f"{timestamp}_output.wav")
            
            # 异步写入文件
            async with aiofiles.open(filename, 'wb') as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    if chunk:
                        await f.write(chunk)
            
            return filename  # 返回文件路径

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing TTS request: {str(e)}")



    def run(self):
        """运行 FastAPI 应用"""
        self.setup_routes()
        uvicorn.run(self.app, host="0.0.0.0", port=11100)
        print(f"Service is running on http://0.0.0.0:11100")
        
        
        
if __name__ == "__main__":
    service = Service()
    service.run()

