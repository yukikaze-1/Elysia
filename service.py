import os
from requests import session
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from Utils import MessageIDGenerator
from RAG import RAG
import httpx
import aiofiles
import base64

from typing import Dict, List
import datetime

from langchain.memory import ConversationBufferMemory, ConversationTokenBufferMemory, ConversationSummaryMemory, ConversationSummaryBufferMemory
from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnableWithMessageHistory, RunnableConfig
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from Prompt import CharacterPromptManager


class Service:
    def __init__(self):
        self.app = FastAPI()
        self.character_prompt_manager = CharacterPromptManager()
        self.tts_client = httpx.AsyncClient(base_url="http://localhost:9880")
        self.rag = RAG()
        self.message_id_generator = MessageIDGenerator()  # 添加ID生成器
        # 存储会话历史
        self.store = {}
        self.conversation = self.advanced_setup()  # 初始化会话处理
        self.config = RunnableConfig(configurable={"session_id": "default"})
        
    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = ChatMessageHistory()
        return self.store[session_id]

    async def check_memory_status(self, session_id="default")->List[str]:
        """检查内存状态"""
        history = self.get_session_history(session_id)
        messages = history.messages
        
        print(f"当前消息数量: {len(messages)}")
        print("对话历史:")
        res = [] 
        
        # 定义显示名称映射
        type_mapping = {
            "human": "用户",
            "ai": "爱莉希雅", 
            "system": "系统",
            "AIMessageChunk": "爱莉希雅",
        }
        
        for i, msg in enumerate(messages):
            display_type = type_mapping.get(msg.type, msg.type)
            formatted_msg = f"{i+1}. {display_type}: {msg.content}"
            res.append(formatted_msg)
            print(f"  {formatted_msg}")
        return res
    
    def advanced_setup(self):
        llm = ChatOllama(
            model="qwen2.5",
            base_url="http://localhost:11434",
            temperature=0.3,
            num_predict=512,
            top_p=0.9,
            repeat_penalty=1.1
        )
        
        # 创建聊天提示模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.character_prompt_manager.get_Elysia_prompt()),
            MessagesPlaceholder(variable_name="history"),
            ("user", "{input}")
        ])
        
        # 创建链
        chain = prompt | llm
        
        # 使用RunnableWithMessageHistory包装
        conversation = RunnableWithMessageHistory(
            chain,
            self.get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        
        return conversation
        

    def setup_routes(self):
        """设置 API 路由"""
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy"}

        @self.app.post("/chat/text")
        async def chat(request: Request):
            data = await request.json()
            return await self._chat(data)
        
        @self.app.post("/chat/stream_text")
        async def chat_stream(request: Request):
            data = await request.json()
            return await self._chat_stream(data)
        
        @self.app.get("/chat/show_history")
        async def show_history(request: Request):
            session_id = request.query_params.get("session_id", "default")
            return await self.check_memory_status(session_id)

    async def _chat_stream(self, data: Dict):
        """处理新的聊天请求, 支持流式响应"""
        message: str = data.get("message", "")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")
        
        async def generate():
            try:
                import json
                
                # 发送给LLM，获取流式响应
                full_content = ""
                
                # 使用 astream 方法获取流式响应
                async for chunk in self.conversation.astream(
                    {"input": message}, 
                    config=self.config
                ):
                    # 检查chunk是否包含内容
                    if hasattr(chunk, 'content') and chunk.content:
                        content = chunk.content
                        full_content += content
                        
                        # 发送流式文本数据
                        yield json.dumps({"type": "text", "content": content}, ensure_ascii=False) + "\n"
                
                # 流式响应完成后，处理语音生成
                if full_content:
                    try:
                        def clean_text_from_brackets(text: str) -> str:
                            """移除文本中的方括号内容"""
                            import re
                            cleaned = re.sub(r'\[.*?\]', '', text)
                            return cleaned.strip()
                        
                        # 发送音频开始标记
                        yield json.dumps({"type": "audio_start", "audio_format": "ogg"}, ensure_ascii=False) + "\n"
                        
                        # 真正的音频流式生成和传输
                        async for audio_chunk in self._stream_tts_audio(text=clean_text_from_brackets(full_content)):
                            if audio_chunk:
                                # 将音频块编码为base64并流式发送
                                chunk_base64 = base64.b64encode(audio_chunk).decode('utf-8')
                                yield json.dumps({
                                    "type": "audio_chunk", 
                                    "audio_data": chunk_base64,
                                    "chunk_size": len(audio_chunk)
                                }, ensure_ascii=False) + "\n"
                        
                        # 发送音频结束标记
                        yield json.dumps({"type": "audio_end"}, ensure_ascii=False) + "\n"
                            
                    except Exception as e:
                        print(f"语音生成失败: {e}")
                        yield json.dumps({'type': 'error', 'error': f'语音生成失败: {str(e)}'}, ensure_ascii=False) + "\n"
                
                # 发送完成标记
                yield json.dumps({"type": "done"}) + "\n"
                
            except Exception as e:
                error_msg = str(e)
                print(f"流式响应错误: {error_msg}")
                yield json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False) + "\n"
        
        # 返回流式响应
        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson"
        )
    
    async def _stream_tts_audio(self, text: str):
        """真正的流式音频生成"""
        payload = {
            "text": text,
            "text_lang": "zh", 
            "ref_audio_path": "/home/yomu/Elysia/ref.wav",
            "prompt_lang": "zh",
            "prompt_text": "我的话，嗯哼，更多是靠少女的小心思吧~看看你现在的表情，好想去那里。",
            "text_split_method": "cut5",
            "batch_size": 20,
            "media_type": "ogg",
            "streaming_mode": True
        }
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = await self.tts_client.request("POST", "/tts", json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            
            # 真正的流式处理 - 逐块yield音频数据
            async for chunk in response.aiter_bytes(chunk_size=8192):
                if chunk:
                    yield chunk  # 直接yield音频块
                    
        except Exception as e:
            print(f"TTS 流式处理失败: {e}")
            yield None

    async def _chat(self, data: Dict):
        """处理新的聊天请求"""
        message: str = data.get("message", "")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
        # 发送给LLM
        response = self.conversation.invoke({"input": message}, config=self.config)

        def clean_text_from_brackets(text: str) -> str:
            """移除文本中的方括号内容"""
            import re
            # 移除方括号及其内容
            cleaned = re.sub(r'\[.*?\]', '', text)
            return cleaned.strip()

        # 生成语音
        audio_response = await self._post_to_tts(text=clean_text_from_brackets(response.content))

        return {"text": response.content, "audio": audio_response}
    
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

