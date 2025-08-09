"""
网络处理模块
处理HTTP请求、流式数据、异步通信等
"""

import requests
import aiohttp
import asyncio
import json
import os
from typing import Dict, Any, Callable, Optional
from core.config import Config


class NetworkHandler:
    """网络处理器"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or Config.API_BASE_URL
    
    def normal_chat_request(self, message: str, user_id: str = "test_user") -> Dict[str, Any]:
        """普通聊天请求"""
        try:
            url = f"{self.base_url}/chat/text"
            payload = {"message": message, "user_id": user_id}
            
            print(f"发送请求到: {url}")
            print(f"payload: {payload}")
            
            response = requests.post(url, json=payload, timeout=Config.CONNECTION_TIMEOUT)
            response.raise_for_status()
            
            print(f"收到响应: {response.status_code}")
            
            data = response.json()
            print(f"响应数据: {data}")
            
            return data
            
        except Exception as e:
            print(f"普通聊天异常: {e}")
            raise
    
    def upload_audio_file_sync(self, audio_file: str) -> requests.Response:
        """同步上传音频文件"""
        try:
            url = f"{self.base_url}/chat/audio/stream/cloud"
            
            print(f"上传音频文件到: {url}")
            print(f"文件路径: {audio_file}")
            
            # 准备文件
            with open(audio_file, 'rb') as f:
                files = {'file': (os.path.basename(audio_file), f, 'audio/*')}
                
                # 发送请求
                response = requests.post(url, files=files, timeout=Config.REQUEST_TIMEOUT, stream=True)
                response.raise_for_status()
                
                print(f"收到响应: {response.status_code}")
                return response
                
        except Exception as e:
            print(f"音频上传异常: {e}")
            raise
    
    def get_chat_history(self) -> Dict[str, Any]:
        """获取聊天历史"""
        try:
            url = f"{self.base_url}/chat/show_history"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"获取历史失败: {e}")
            raise
    
    async def stream_chat_async(self, message: str, user_id: str = "test_user", 
                               on_data_received: Optional[Callable] = None) -> None:
        """异步流式聊天 - 重写版本，直接传递消息行"""
        try:
            # 设置连接参数
            connector = aiohttp.TCPConnector(
                limit_per_host=100,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(total=Config.CONNECTION_TIMEOUT)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                read_bufsize=Config.STREAM_BUFFER_SIZE,
                max_line_size=Config.MAX_LINE_SIZE,
                max_field_size=Config.MAX_FIELD_SIZE
            ) as session:
                url = f"{self.base_url}/chat/text/stream/local"
                payload = {"message": message, "user_id": user_id}
                
                print(f"发送流式请求到: {url}")
                print(f"payload: {payload}")
                
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        if on_data_received:
                            await on_data_received('{"type": "error", "error": "' + error_text + '"}')
                        return
                    
                    print(f"收到响应: {response.status}")
                    
                    # 直接传递消息行给处理器
                    while True:
                        try:
                            line = await response.content.readline()
                            if not line:
                                break
                                
                            line_text = line.decode('utf-8').strip()
                            if not line_text:
                                continue
                                
                            print(f"收到数据行: {line_text[:100]}...")
                            
                            # 直接传递原始JSON行给处理器
                            if on_data_received:
                                await on_data_received(line_text)
                                
                        except Exception as line_error:
                            print(f"读取行错误: {line_error}")
                            break
                            
        except Exception as e:
            error_msg = str(e)
            print(f"流式聊天异常: {error_msg}")
            if on_data_received:
                await on_data_received('{"type": "error", "error": "' + error_msg + '"}')
    
    async def cloud_chat_async(self, message: str, user_id: str = "test_user", 
                              on_data_received: Optional[Callable] = None) -> None:
        """异步云端流式聊天 - 重写版本，直接传递消息行"""
        try:
            # 设置连接参数
            connector = aiohttp.TCPConnector(
                limit_per_host=100,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)  # 云端可能需要更长时间
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                read_bufsize=Config.STREAM_BUFFER_SIZE,
                max_line_size=Config.MAX_LINE_SIZE,
                max_field_size=Config.MAX_FIELD_SIZE
            ) as session:
                url = f"{self.base_url}/chat/text/stream/cloud"
                payload = {"message": message, "user_id": user_id}
                
                print(f"发送云端流式请求到: {url}")
                print(f"payload: {payload}")
                
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        if on_data_received:
                            await on_data_received('{"type": "error", "error": "' + error_text + '"}')
                        return
                    
                    print(f"收到云端响应: {response.status}")
                    
                    # 直接传递消息行给处理器
                    while True:
                        try:
                            line = await response.content.readline()
                            if not line:
                                break
                                
                            line_text = line.decode('utf-8').strip()
                            if not line_text:
                                continue
                                
                            print(f"收到云端数据行: {line_text[:100]}...")
                            
                            # 直接传递原始JSON行给处理器
                            if on_data_received:
                                await on_data_received(line_text)
                                
                        except Exception as line_error:
                            print(f"云端读取行错误: {line_error}")
                            break
                            
        except Exception as e:
            error_msg = str(e)
            print(f"云端流式聊天异常: {error_msg}")
            if on_data_received:
                await on_data_received('{"type": "error", "error": "' + error_msg + '"}')
    
    async def audio_upload_async(self, audio_file: str, on_data_received: Optional[Callable] = None) -> None:
        """异步音频上传和流式响应处理"""
        try:
            # 设置连接参数
            connector = aiohttp.TCPConnector(
                limit_per_host=100,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                read_bufsize=Config.STREAM_BUFFER_SIZE,
                max_line_size=Config.MAX_LINE_SIZE,
                max_field_size=Config.MAX_FIELD_SIZE
            ) as session:
                url = f"{self.base_url}/chat/audio/stream/cloud"
                
                print(f"异步上传音频文件到: {url}")
                print(f"文件路径: {audio_file}")
                
                # 准备文件数据
                with open(audio_file, 'rb') as f:
                    file_data = aiohttp.FormData()
                    file_data.add_field('file', f, filename=os.path.basename(audio_file), content_type='audio/*')
                    
                    async with session.post(url, data=file_data) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            if on_data_received:
                                on_data_received({"type": "error", "error": error_text})
                            return
                        
                        print(f"收到异步音频响应: {response.status}")
                        
                        # 使用 content.readline() 读取流式数据
                        while True:
                            try:
                                line = await response.content.readline()
                                if not line:
                                    break
                                    
                                line_text = line.decode('utf-8').strip()
                                if not line_text:
                                    continue
                                    
                                print(f"收到异步音频数据: {line_text[:100]}...")
                                
                                try:
                                    data = json.loads(line_text)
                                    if on_data_received:
                                        on_data_received(data)
                                        
                                except json.JSONDecodeError as e:
                                    print(f"异步音频JSON解析错误: {e}, 原始数据: {line_text}")
                                    continue
                                    
                            except Exception as line_error:
                                print(f"异步音频读取行错误: {line_error}")
                                break
                                
        except Exception as e:
            error_msg = str(e)
            print(f"异步音频上传异常: {error_msg}")
            if on_data_received:
                on_data_received({"type": "error", "error": error_msg})
    
    def process_streaming_response(self, response: requests.Response, on_data_received: Optional[Callable] = None):
        """处理流式响应"""
        try:
            print("开始处理流式响应...")
            
            # 逐行读取流式响应
            for line in response.iter_lines():
                if not line:
                    continue
                    
                line_text = line.decode('utf-8').strip()
                if not line_text:
                    continue
                    
                print(f"收到流式数据: {line_text[:100]}...")
                
                try:
                    data = json.loads(line_text)
                    if on_data_received:
                        on_data_received(data)
                        
                except json.JSONDecodeError as e:
                    print(f"流式JSON解析错误: {e}, 原始数据: {line_text}")
                    continue
                    
        except Exception as e:
            print(f"处理流式响应异常: {e}")
            if on_data_received:
                on_data_received({"type": "error", "error": str(e)})
    
    async def tts_stream_async(self, text: str, on_data_received: Optional[Callable] = None) -> None:
        """异步TTS生成和流式音频播放"""
        try:
            # 创建会话超时配置
            timeout = aiohttp.ClientTimeout(
                total=Config.REQUEST_TIMEOUT,
                connect=Config.CONNECTION_TIMEOUT,
                sock_read=120  # 流式读取超时
            )
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.base_url}/tts/generate"
                payload = {"text": text}
                
                print(f"🎵 发送TTS请求到: {url}")
                print(f"📝 文本内容: '{text[:50]}...' (长度: {len(text)})")
                
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error_msg = f"TTS服务器响应错误 {response.status}: {error_text}"
                        print(f"❌ {error_msg}")
                        if on_data_received:
                            on_data_received({"type": "error", "error": error_msg})
                        return
                    
                    print(f"✅ 收到TTS响应: {response.status}")
                    
                    # 处理流式音频数据
                    chunk_count = 0
                    total_audio_size = 0
                    header_skipped = False
                    
                    async for chunk in response.content.iter_chunked(1024):
                        if chunk:
                            chunk_count += 1
                            total_audio_size += len(chunk)
                            
                            # 构造音频数据消息
                            audio_message = {
                                "type": "audio_chunk",
                                "data": chunk,
                                "chunk_id": chunk_count,
                                "header_skipped": header_skipped,
                                "total_size": total_audio_size
                            }
                            
                            # 第一个chunk包含WAV头部，标记为需要处理
                            if not header_skipped:
                                audio_message["has_wav_header"] = True
                                header_skipped = True
                            
                            # 调用回调函数处理音频数据
                            if on_data_received and callable(on_data_received):
                                try:
                                    if asyncio.iscoroutinefunction(on_data_received):
                                        await on_data_received(audio_message)
                                    else:
                                        on_data_received(audio_message)
                                except Exception as e:
                                    print(f"处理TTS音频数据异常: {e}")
                                    continue
                    
                    # 发送完成信号
                    if on_data_received and callable(on_data_received):
                        complete_message = {
                            "type": "audio_complete",
                            "total_chunks": chunk_count,
                            "total_size": total_audio_size
                        }
                        try:
                            if asyncio.iscoroutinefunction(on_data_received):
                                await on_data_received(complete_message)
                            else:
                                on_data_received(complete_message)
                        except Exception as e:
                            print(f"处理TTS完成信号异常: {e}")
                    
                    print(f"🎵 TTS流式音频传输完成，共{chunk_count}个chunk，总大小{total_audio_size}字节")
                                
        except asyncio.TimeoutError:
            error_msg = "TTS请求超时，请检查网络连接"
            print(f"⏰ {error_msg}")
            if on_data_received:
                on_data_received({"type": "error", "error": error_msg})
        except Exception as e:
            error_msg = f"TTS流式请求异常: {e}"
            print(f"❌ {error_msg}")
            if on_data_received:
                on_data_received({"type": "error", "error": error_msg})
                on_data_received({"type": "error", "error": str(e)})
