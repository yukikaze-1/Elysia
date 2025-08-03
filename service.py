from requests import session
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from Utils import MessageIDGenerator
from TokenManager import TokenManager
from RAG import RAG
import httpx
import base64
import json

from openai.types.chat import ChatCompletionMessageParam
from typing import Dict, List, Any, Tuple
import datetime
import os
from openai import OpenAI

from langchain.memory import ConversationBufferMemory, ConversationTokenBufferMemory, ConversationSummaryMemory, ConversationSummaryBufferMemory
from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnableWithMessageHistory, RunnableConfig
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from Prompt import CharacterPromptManager
from PersistentChatHistory import GlobalChatMessageHistory

from dotenv import load_dotenv, dotenv_values, find_dotenv

class Service:
    def __init__(self):
        self.app = FastAPI()
        self.character_prompt_manager = CharacterPromptManager()
        self.tts_client = httpx.AsyncClient(base_url="http://localhost:9880")
        # self.rag = RAG()
        
        # 立即初始化所有需要的组件
        self._initialize_all_components()
        
        print("=== Service 初始化完成 ===")
        
    def _initialize_all_components(self):
        """初始化所有组件"""
        
        # 1. 初始化 RAG（如果需要）
        print("正在初始化 RAG...")
        # self.rag = RAG()
        print("✓ RAG 跳过")
        
        # 2. 强制初始化全局聊天历史
        print("正在强制加载聊天历史...")
        self._global_history = GlobalChatMessageHistory()
        print(f"✓ 聊天历史已加载 ({len(self._global_history.messages)} 条消息)")
        
        # 3. 初始化对话处理器
        print("正在设置本地对话...")
        self.local_conversation = self.setup_local_conversation()
        print("✓ 本地对话已设置")
        
        self.config = RunnableConfig(configurable={"session_id": "default"})
        
        # 4. 初始化 Token 管理器
        print("正在初始化 Token 管理器...")
        self.token_manager = TokenManager()
        print("✓ Token 管理器已初始化")
        
        # 5. 初始化云端对话
        print("正在设置云端对话...")
        self.cloud_conversation = self.setup_cloud_conversation()
        print("✓ 云端对话已设置")
        
        # 6. 预热检查
        print("正在进行预热检查...")
        self._warmup_check()
        
    
    def _warmup_check(self):
        """预热检查 - 确保所有组件正常工作"""
        try:
            # 检查聊天历史
            message_count = len(self._global_history.messages)
            print(f"  - 聊天历史: {message_count} 条消息")
            
            # 检查 Token 管理器
            stats = self.token_manager.get_current_stats()
            print(f"  - Token 统计: 总计 {stats['total_stats']['total_tokens']} tokens")
            
            print("✓ 预热检查完成")
            
        except Exception as e:
            print(f"✗ 预热检查失败: {e}")    

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """获取会话历史 - 始终返回全局单例"""
        return self._global_history  # 每次调用都返回同一实例！

    async def check_memory_status(self, session_id=None)->List[str]:
        """检查记忆状态 - session_id 参数被忽略"""
        history = self._global_history
        messages = history.messages
        res = [] 
        
        # 定义显示名称映射
        type_mapping = {
            "human": "魂魄妖梦",
            "ai": "爱莉希雅", 
            "system": "系统",
            "AIMessageChunk": "爱莉希雅",
        }
        
        for i, msg in enumerate(messages):
            display_type = type_mapping.get(msg.type, msg.type)
            formatted_msg = f"{i+1}. {display_type}: {msg.content}"
            res.append(formatted_msg)
            # print(f"  {formatted_msg}")
        return res

    def setup_cloud_conversation(self, model: str = "qwen3-235b-a22b-instruct-2507" )-> OpenAI:
        """
        设置云端聊天会话处理
        即使用云端模型进行对话处理
        """
        self.cloud_llm_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.cloud_llm_name = model
        load_dotenv(find_dotenv())
        self.api_key = dotenv_values(".env").get("QWEN3_API_KEY","")
        if not self.api_key:
            raise ValueError("API key for QWEN3 is not set in the environment variables.")
        
        return OpenAI(
            api_key=self.api_key,
            base_url=self.cloud_llm_url,
        )
        
        
    
    def setup_local_conversation(self, model: str = "qwen2.5") -> RunnableWithMessageHistory:
        """
        设置本地聊天会话处理
        即使用本地Ollama模型进行对话处理
        """
        llm = ChatOllama(
            model=model,
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
            runnable=chain,
            get_session_history=self.get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        
        return conversation
        

    def setup_routes(self):
        """设置 API 路由"""
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy"}

        @self.app.post("/chat/stream_text")
        async def chat_stream(request: Request):
            data = await request.json()
            return await self._chat_stream_local(data)
        
        @self.app.post("/chat/stream_text_cloud")
        async def chat_stream_cloud(request: Request):
            data = await request.json()
            return await self._chat_stream_cloud(data)
        
        @self.app.get("/chat/show_history")
        async def show_history(request: Request):
            session_id = request.query_params.get("session_id", "default")
            return await self.check_memory_status(session_id)
        
        # Token 管理相关 API
        @self.app.get("/chat/token_stats")
        async def get_token_stats():
            """获取详细的 token 统计信息"""
            return self.token_manager.get_current_stats()
        
        @self.app.get("/chat/token_stats/simple")
        async def get_simple_token_stats():
            """获取简化的 token 统计信息"""
            stats = self.token_manager.get_current_stats()
            return {
                "local_tokens": stats["local_stats"]["total_tokens"],
                "cloud_tokens": stats["cloud_stats"]["total_tokens"],
                "total_tokens": stats["total_stats"]["total_tokens"],
                "session_local": stats["session_stats"]["local"]["total_tokens"],
                "session_cloud": stats["session_stats"]["cloud"]["total_tokens"],
                "session_total": stats["session_stats"]["total"]["total_tokens"],
            }
        
        @self.app.post("/chat/reset_session_tokens")
        async def reset_session_tokens():
            """重置会话 token 统计"""
            self.token_manager.reset_session_stats()
            return {"message": "Session token statistics reset successfully"}
        
        @self.app.post("/chat/reset_all_tokens")
        async def reset_all_tokens():
            """重置所有 token 统计"""
            self.token_manager.reset_all_stats()
            return {"message": "All token statistics reset successfully"}
        
        
        # 新增：持久化相关 API
        @self.app.post("/chat/save_token_stats")
        async def save_token_stats():
            """手动保存 token 统计数据"""
            self.token_manager.force_save()
            return {"message": "Token statistics saved successfully"}
        
        @self.app.post("/chat/export_token_stats")
        async def export_token_stats(export_name: str):
            """导出 token 统计数据"""
            if not export_name:
                raise HTTPException(status_code=400, detail="Export name is required")
            
            try:
                file_path = self.token_manager.export_stats(export_name)
                return {"message": f"Statistics exported to {file_path}", "file_path": file_path}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    
    async def _generate_token_usage_response(self, model_type: str, input_tokens: int, output_tokens: int, usage_info=None):
        """生成标准化的 token 使用统计响应"""
        base_usage = {
            "type": "token_usage",
            "model_type": model_type,
            "current_turn": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            },
            "session_total": {
                "input_tokens": self.token_manager.session_input_tokens,
                "output_tokens": self.token_manager.session_output_tokens,
                "total_tokens": self.token_manager.session_total_tokens
            },
            "grand_total": {
                "local_tokens": self.token_manager.local_total_tokens,
                "cloud_tokens": self.token_manager.cloud_total_tokens,
                "total_tokens": self.token_manager.total_tokens
            }
        }
        
        # 添加模型特定的会话统计
        if model_type == "local":
            base_usage["session_local"] = {
                "input_tokens": self.token_manager.local_session_input_tokens,
                "output_tokens": self.token_manager.local_session_output_tokens,
                "total_tokens": self.token_manager.local_session_total_tokens
            }
        elif model_type == "cloud":
            base_usage["session_cloud"] = {
                "input_tokens": self.token_manager.cloud_session_input_tokens,
                "output_tokens": self.token_manager.cloud_session_output_tokens,
                "total_tokens": self.token_manager.cloud_session_total_tokens
            }
            
            # 添加云端实际使用统计
            if usage_info:
                base_usage["cloud_usage"] = {
                    "prompt_tokens": usage_info.prompt_tokens,
                    "completion_tokens": usage_info.completion_tokens,
                    "total_tokens": usage_info.total_tokens
                }
        
        return base_usage
    
    
    async def _handle_audio_generation(self, content: str):
        """处理语音生成的通用逻辑"""
        def clean_text_from_brackets(text: str) -> str:
            """移除文本中的方括号内容"""
            import re
            cleaned = re.sub(r'\[.*?\]', '', text)
            return cleaned.strip()
        
        try:
            # 发送音频开始标记
            yield json.dumps({"type": "audio_start", "audio_format": "ogg"}, ensure_ascii=False) + "\n"
            
            # 流式音频生成
            async for audio_chunk in self._stream_tts_audio(text=clean_text_from_brackets(content)):
                if audio_chunk:
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
            
    
    async def _chat_stream_cloud(self, data: Dict):
        """云端模型流式聊天"""
        message: str = data.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")
        
        async def generate():
            try:
                # 准备请求
                estimated_input_tokens, messages = await self._prepare_cloud_request(message)
                
                # 处理流式响应 - 直接流式处理
                full_content = ""
                estimated_output_tokens = 0
                usage_info = None
                
                async for response in self._process_cloud_stream(messages):
                    # 如果是流式完成标记，提取数据
                    try:
                        response_data = json.loads(response.strip())
                        if response_data.get("type") == "stream_complete":
                            full_content = response_data.get("full_content", "")
                            estimated_output_tokens = response_data.get("estimated_output_tokens", 0)
                            usage_info_data = response_data.get("usage_info")
                            if usage_info_data:
                                # 创建一个简单的对象来模拟 usage_info
                                class UsageInfo:
                                    def __init__(self, data):
                                        self.prompt_tokens = data.get("prompt_tokens", 0)
                                        self.completion_tokens = data.get("completion_tokens", 0)
                                        self.total_tokens = data.get("total_tokens", 0)
                                usage_info = UsageInfo(usage_info_data)
                            break
                        else:
                            # 转发流式文本数据
                            yield response
                    except:
                        # 如果不是JSON，直接转发
                        yield response
                
                # 调整 token 统计
                actual_input_tokens, actual_output_tokens = await self._adjust_cloud_tokens(
                    estimated_input_tokens, estimated_output_tokens, usage_info
                )
                
                # 发送 token 统计
                token_usage = await self._generate_token_usage_response(
                    "cloud", actual_input_tokens, actual_output_tokens, usage_info
                )
                yield json.dumps(token_usage, ensure_ascii=False) + "\n"
                
                # 添加到历史记录
                if full_content:
                    self._global_history.add_ai_message(full_content)
                    
                    # 处理语音生成
                    async for audio_response in self._handle_audio_generation(full_content):
                        yield audio_response
                
                yield json.dumps({"type": "done"}) + "\n"
                
            except Exception as e:
                yield json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False) + "\n"
        
        return StreamingResponse(generate(), media_type="application/x-ndjson")

    async def _prepare_cloud_request(self, message: str)-> Tuple[int, List[ChatCompletionMessageParam]]:
        """
        准备云端请求
        1. 计算输入 tokens 
        2. 添加到全局历史
        3. 构建消息列表(将历史消息转换为适合云端模型的格式并添加)
        
        参数:
        - message: 用户输入的消息
        
        返回:
        - estimated_input_tokens: 估计的输入 tokens 数量
        - messages: 构建好的消息列表
        """
        # 计算并记录输入 tokens
        estimated_input_tokens = self.token_manager.count_tokens_approximate(message)
        self.token_manager.add_cloud_input_tokens(estimated_input_tokens)
        
        # 添加到全局历史
        history = self._global_history
        history.add_user_message(message)
        
        # 构建消息列表 - 使用正确的类型
        messages: List[ChatCompletionMessageParam] = [{
            'role': 'system', 
            'content': self.character_prompt_manager.get_Elysia_prompt()
            }]
        
        # 添加历史消息(消息类型转换)
        for msg in history.messages:
            if msg.type == "human":
                messages.append({'role': 'user', 'content': str(msg.content)})
            elif msg.type == "ai":
                messages.append({'role': 'assistant', 'content': str(msg.content)})
        
        # 返回估计的输入 tokens 和消息列表
        return estimated_input_tokens, messages
    

    async def _process_cloud_stream(self, messages: List[ChatCompletionMessageParam]):
        """处理云端模型的流式响应"""
        # 创建云端聊天完成请求(流式)
        response = self.cloud_conversation.chat.completions.create(
            model=self.cloud_llm_name,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            temperature=0.3,
            max_tokens=1000
        )
        
        full_content = ""
        estimated_output_tokens = 0
        usage_info = None
        
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    full_content += content
                    
                    chunk_tokens = self.token_manager.count_tokens_approximate(content)
                    self.token_manager.add_cloud_streaming_output_tokens(chunk_tokens)
                    estimated_output_tokens += chunk_tokens
                    
                    yield json.dumps({"type": "text", "content": content}, ensure_ascii=False) + "\n"
            
            if hasattr(chunk, 'usage') and chunk.usage:
                usage_info = chunk.usage
        
        # 不能在异步生成器中使用 return，改为 yield 最终结果
        yield json.dumps({"type": "stream_complete", 
                          "full_content": full_content, 
                          "estimated_output_tokens": estimated_output_tokens, 
                          "usage_info": usage_info.model_dump() if usage_info else None
                          }, ensure_ascii=False) + "\n"

    async def _adjust_cloud_tokens(self, estimated_input: int, estimated_output: int, usage_info) -> Tuple[int, int]:
        """调整云端 token 统计"""
        if usage_info:
            actual_input = usage_info.prompt_tokens
            actual_output = usage_info.completion_tokens
            
            self.token_manager.adjust_cloud_tokens_with_usage(
                estimated_input, estimated_output,
                actual_input, actual_output
            )
            return actual_input, actual_output
        
        return estimated_input, estimated_output
    
    
    async def _process_local_stream(self, message: str):
        """处理本地模型的流式响应"""
        full_content = ""
        output_tokens = 0
        
        async for chunk in self.local_conversation.astream(
            {"input": message}, 
            config=self.config
        ):
            if hasattr(chunk, 'content') and chunk.content:
                content: str = chunk.content
                full_content += content
                
                # 累加输出 tokens
                chunk_tokens = self.token_manager.count_tokens_approximate(content)
                self.token_manager.add_local_streaming_output_tokens(chunk_tokens)
                output_tokens += chunk_tokens
                
                # 发送流式文本数据
                yield json.dumps({"type": "text", "content": content}, ensure_ascii=False) + "\n"
        
        # 不能在异步生成器中使用 return，改为 yield 最终结果
        yield json.dumps({"type": "stream_complete", "full_content": full_content, "output_tokens": output_tokens}, ensure_ascii=False) + "\n"
    
    async def _chat_stream_local(self, data: Dict):
        """
        处理新的聊天请求, 使用本地Ollama模型
        支持流式响应
        """
        message: str = data.get("message", "")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")
        
        async def generate():
            try:
                # 计算并记录输入 tokens
                input_tokens = self.token_manager.add_input_tokens(message)
                
                # 处理流式响应 - 直接流式处理
                full_content = ""
                output_tokens = 0
                
                async for response in self._process_local_stream(message):
                    # 如果是流式完成标记，提取数据
                    try:
                        response_data = json.loads(response.strip())
                        if response_data.get("type") == "stream_complete":
                            full_content = response_data.get("full_content", "")
                            output_tokens = response_data.get("output_tokens", 0)
                            break
                        else:
                            # 转发流式文本数据
                            yield response
                    except:
                        # 如果不是JSON，直接转发
                        yield response
                
                # 发送 token 统计
                token_usage = await self._generate_token_usage_response("local", input_tokens, output_tokens)
                yield json.dumps(token_usage, ensure_ascii=False) + "\n"
                
                # 处理语音生成
                if full_content:
                    async for audio_response in self._handle_audio_generation(full_content):
                        yield audio_response
                        
                # 发送完成标记
                yield json.dumps({"type": "done"}) + "\n"
                
            except Exception as e:
                error_msg = str(e)
                print(f"流式响应错误: {error_msg}")
                yield json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False) + "\n"
        
        # 返回流式响应
        return StreamingResponse(generate(), media_type="application/x-ndjson")
    
    
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

   
    def run(self):
        """运行 FastAPI 应用"""
        self.setup_routes()
        uvicorn.run(self.app, host="0.0.0.0", port=11100)
        print(f"Service is running on http://0.0.0.0:11100")
        
        
        
if __name__ == "__main__":
    service = Service()
    service.run()

