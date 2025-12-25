from email import message
import json
from tkinter.filedialog import Open
from attr import has
import httpx
from openai import OpenAI
from typing import List, Tuple, Dict, Any
from fastapi import HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from regex import T

from ServiceConfig import ServiceConfig
from AudioGenerateHandler import AudioGenerateHandler
from AudioRecognizeHandler import AudioRecognizeHandler
from TokenManager import TokenManager, UsageInfo
from CharacterPromptManager import CharacterPromptManager
from PersistentChatHistory import GlobalChatMessageHistory
from Utils__ import TimeTracker

from langchain_ollama import ChatOllama
from langchain_core.runnables import RunnableWithMessageHistory, RunnableConfig
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory

class ChatHandler:
    """聊天处理器 - 自己管理需要的依赖"""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.time_tracker = TimeTracker()
        self.client = httpx.AsyncClient()
        self._setup_components()
        
    
    def _setup_components(self):
        """内部设置组件"""
        print("=== 角色提示管理器 初始化开始 ===")
        self.character_prompt_manager = CharacterPromptManager()
        print("✅ 角色提示管理器 初始化完成")
        
        print("=== 全局历史初始化开始 ===")
        # 使用全局单例模式，确保全局只有一个 GlobalChatMessageHistory 实例
        self.global_history = GlobalChatMessageHistory()
        print("✅ 全局历史初始化完成")
        
        # 设置Token管理器
        print("=== Token管理器 初始化开始 ===")
        # 使用单例模式，确保全局只有一个 TokenManager 实例
        self.token_manager = TokenManager()
        print("✅ Token管理器 初始化完成")
        
        # 设置 tts_handler
        print("=== TTS 初始化开始 ===")
        self.tts_handler = AudioGenerateHandler(self.config)
        print("✅ TTS 初始化完成")
        
        # 设置 stt_handler
        print("=== STT 初始化开始 ===")
        self.stt_handler = AudioRecognizeHandler(self.config)
        print("✅ STT 初始化完成")
        
        # 设置对话处理器
        print("=== 本地对话处理器 初始化开始 ===")
        self.local_conversation = self._setup_local_conversation()
        print("✅ 本地对话处理器 初始化完成")
        
        print("=== 云端对话处理器 初始化开始 ===")
        self.cloud_conversation = self._setup_cloud_conversation()
        print("✅ 云端对话处理器 初始化完成")
        
        
    def get_session_history(self, session_id: str | None = None) -> BaseChatMessageHistory:
        """获取会话历史 - 始终返回全局单例"""
        return self.global_history  
    
    async def warmup_local_model(self):
        """预热本地llm"""
        # 调用一次本地llm，看看通不通，返回是否正常
        try:
            payload = {
                "model": self.config.local_model,
                "stream": False,
                "messages": [
                    {"role": "user", "content": "你好"}
                ]
            }
            url = self.config.ollama_base_url + "/api/chat"
            response = await self.client.post(url=url, json=payload, timeout=30)
            response.raise_for_status()  # 确保请求成功
            if response.status_code == 200:
                res = response.json()
                print(f"✅ 本地模型预热成功: {res['message']['content']}")
            else:
                print(f"⚠️ 本地模型预热失败: {response.status_code}")
        except Exception as e:
            print(f"⚠️ 本地模型预热失败: {e}")

    async def warmup_cloud_model(self):
        """预热云端llm"""
        # 调用一次云端llm，看看通不通，返回是否正常
        try:
            client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.cloud_base_url,
                timeout=30
            )
            response =  client.chat.completions.create(
                model=self.config.cloud_model,
                messages=[{"role": "user", "content": "你好"}],
                stream=False,
            )
            if response and response.choices:
                print(f"✅ 云端模型预热响应: {response.choices[0].message.content}")
            else:
                print("⚠️ 云端模型预热失败: 未返回响应")
        except Exception as e:
            print(f"⚠️ 云端模型预热失败: {e}")
            

    async def warmup_stt(self):
        """预热stt服务"""
        # 调用一次stt服务，看看通不通，返回是否正常
        try:
            audio_path = self.config.tts_ref_audio_path
            with open(audio_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            response = await self.stt_handler.recognize_audio(audio_data)
            if response and isinstance(response, dict) and 'text' in response:
                print(f"✅ STT预热成功: {response['text']}")
            else:
                print("⚠️ STT预热失败: 未能识别音频")
        except Exception as e:
            print(f"⚠️ STT预热失败: {e}")
            
            
    async def warmup_tts(self):
        """预热tts服务"""
        # 调用一次tts服务，看看通不通，返回是否正常
        try:
            payload = {
                        "text": "你好",
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
                        "streaming_mode": False,
                        "parallel_infer": True,
                        "repetition_penalty": 1.35
            }
            response = await self.client.post(url=self.config.tts_base_url + "/tts", json=payload, timeout=60)
            if response.status_code == 200:
                print(f"✅ 音频生成成功")
            else:
                print(f"⚠️ TTS 预热失败: {response.status_code if response else '无响应'}")
        except Exception as e:
            print(f"⚠️ TTS 预热异常: {e}")
            

    def _setup_local_conversation(self)-> RunnableWithMessageHistory:
        """设置本地对话处理器"""
        self.conversation_config = RunnableConfig(configurable={"session_id": "default"})
        
        # 本地对话
        llm = ChatOllama(
            model=self.config.local_model,
            base_url=self.config.ollama_base_url,
            temperature=self.config.local_temperature,
            num_predict=self.config.local_num_predict,
            top_p=self.config.local_top_p,
            repeat_penalty=self.config.local_repeat_penalty
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.character_prompt_manager.get_Elysia_prompt()),
            MessagesPlaceholder(variable_name="history"),
            ("user", "{input}")
        ])
        
        chain = prompt | llm
        conversation = RunnableWithMessageHistory(
            runnable=chain,
            get_session_history=self.get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        return conversation
    
    
    def _setup_cloud_conversation(self)-> OpenAI:
        """设置云端对话处理器"""        
        conversation = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.cloud_base_url,
        )
        return  conversation
        
    
    async def handle_local_chat_stream(self, message: str):
        """处理本地聊天流式响应"""
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")
        
        async def generate():
            try:
                # 开始请求计时
                self.time_tracker.start_request()
                
                # 计算并记录输入 tokens
                input_tokens = self.token_manager.add_input_tokens(message)
                
                full_content = ""
                output_tokens = 0
                
                # 处理流式响应
                with self.time_tracker.time_stage("llm_processing"):
                    async for response in self._process_local_stream(message):
                        try:
                            response_data = json.loads(response.strip())
                            if response_data.get("type") == "stream_complete":
                                full_content = response_data.get("full_content", "")
                                output_tokens = response_data.get("output_tokens", 0)
                                break
                            else:
                                # 发送流式文本数据
                                yield response
                        except:
                            yield response
                
                # 发送 token 统计
                token_usage:Dict[str, Any] = self.token_manager.generate_usage_response("local", input_tokens, output_tokens)
                yield json.dumps(token_usage, ensure_ascii=False) + "\n"               
                            
                # 发送计时信息
                timing_summary = self.time_tracker.get_timing_summary()
                yield json.dumps({"type": "timing", "timing": timing_summary}, ensure_ascii=False) + "\n"
                
                # 强制保存token统计
                self.token_manager.force_save()
                        
                # 发送完成标记
                yield json.dumps({"type": "done"}) + "\n"
                
            except Exception as e:
                error_msg = str(e)
                print(f"流式响应错误: {error_msg}")
                yield json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False) + "\n"
        
        return StreamingResponse(generate(), media_type="application/x-ndjson")

    
    async def _process_local_stream(self, message: str):
        """处理本地模型的流式响应"""
        full_content = ""
        output_tokens = 0
        
        # 生成流式响应
        async for chunk in self.local_conversation.astream(
            {"input": message}, 
            config=self.conversation_config
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
        
        # yield 最终结果
        yield json.dumps({"type": "stream_complete", "full_content": full_content, "output_tokens": output_tokens}, ensure_ascii=False) + "\n"
    
    
    async def _process_cloud_stream(self, messages: List[ChatCompletionMessageParam]):
        """处理云端模型的流式响应,异步生成器"""
        # 创建云端聊天完成请求(流式)
        response = self.cloud_conversation.chat.completions.create(
            model=self.config.cloud_model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            temperature=0.3,
            max_tokens=1000
        )
        
        full_content = ""
        usage_info = None
        
        # 处理流式响应
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    full_content += content
                    
                    # 返回流式文本数据
                    yield json.dumps({"type": "text", "content": content}, ensure_ascii=False) + "\n"
            
            if hasattr(chunk, 'usage') and chunk.usage is not None:
                usage_info = chunk.usage
                print(f"捕获到usage信息: prompt_tokens={usage_info.prompt_tokens}, completion_tokens={usage_info.completion_tokens}")

        # 发送流式响应完成标记
        yield json.dumps({"type": "stream_complete", 
                          "full_content": full_content, 
                          "usage_info": usage_info.model_dump() if usage_info else None
                          }, ensure_ascii=False) + "\n"


    async def handle_cloud_chat_stream(self, message: str):
        """处理云端聊天流式响应的业务逻辑"""
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")
        
        async def generate():
            try:
                # 开始请求计时
                self.time_tracker.start_request()
                
                # 准备请求
                estimated_input_tokens, messages = self._prepare_cloud_request(message)
                
                # 处理流式响应
                full_content = ""
                estimated_output_tokens = 0
                usage_info = None
                
                with self.time_tracker.time_stage("llm_processing"):
                    async for response in self._process_cloud_stream(messages):
                        try:
                            response_data = json.loads(response.strip())
                            if response_data.get("type") == "stream_complete":
                                full_content = response_data.get("full_content", "")
                                estimated_output_tokens = response_data.get("estimated_output_tokens", 0)
                                usage_info_data = response_data.get("usage_info")
                                if usage_info_data:
                                    usage_info = UsageInfo(usage_info_data)
                                break
                            else:
                                yield response
                        except:
                            yield response
                
                # 调整 token 统计
                actual_input_tokens, actual_output_tokens = self.token_manager.adjust_cloud_tokens_with_actual_usage(
                    estimated_input_tokens, estimated_output_tokens, usage_info
                )
                
                # 发送 token 统计
                token_usage = self.token_manager.generate_usage_response(
                    "cloud", actual_input_tokens, actual_output_tokens, usage_info
                )
                yield json.dumps(token_usage, ensure_ascii=False) + "\n"
                
                # 添加到历史记录
                if full_content:
                    self.global_history.add_ai_message(full_content)    
                
                # 强制保存token统计
                self.token_manager.force_save()
                
                yield json.dumps({"type": "done"}) + "\n"
                
            except Exception as e:
                yield json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False) + "\n"
        
        return StreamingResponse(generate(), media_type="application/x-ndjson")
    
    
    def _prepare_cloud_request(self, message: str)-> Tuple[int, List[ChatCompletionMessageParam]]:
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
        history = self.global_history
        history.add_user_message(message)
        
        # 构建消息列表 - 使用正确的类型
        messages: List[ChatCompletionMessageParam] = [{
            'role': 'system', 
            'content': self.character_prompt_manager.get_Elysia_prompt()
            }]
        
        # TODO 需要添加压缩的记忆
        # 添加历史消息(消息类型转换)
        for msg in history.messages:
            if msg.type == "human":
                messages.append({'role': 'user', 'content': str(msg.content)})
            elif msg.type == "ai":
                messages.append({'role': 'assistant', 'content': str(msg.content)})
        
        # 返回估计的输入 tokens 和消息列表
        return estimated_input_tokens, messages
    
    
    async def handle_chat_with_audio(self, file: UploadFile, cloud: bool = True) -> StreamingResponse:
        """处理音频聊天"""
        if not file:
            raise HTTPException(status_code=400, detail="Audio file is required")
        
        # 开始请求计时
        self.time_tracker.start_request()
        
        # 读取音频数据
        audio_data = await file.read()
        
        # 识别音频内容
        with self.time_tracker.time_stage("stt_processing"):
            result = await self.stt_handler.recognize_audio(audio_data)
            if not result:
                raise HTTPException(status_code=500, detail="Failed to recognize audio")
            
            recognized_text = result.get("text", "")
            if not recognized_text:
                raise HTTPException(status_code=500, detail="Failed to recognize audio")
        
        # 处理识别后的文本
        if cloud:
            return await self.handle_cloud_chat_stream(recognized_text)
        else:
            return await self.handle_local_chat_stream(recognized_text)