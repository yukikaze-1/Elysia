"""
主应用程序类
整合所有模块，处理业务逻辑
"""
import threading
import asyncio
import os
import time
from typing import Dict, Any

from core.config import Config
from core.audio_manager import AudioManager
from ui.main_window import MainUI
from handlers.network_handler import NetworkHandler
from handlers.streaming_manager import StreamingResponseManager
from streaming_message_handler_new import StreamingMessageHandler


class ElysiaClient:
    """Elysia 聊天客户端主类"""
    
    def __init__(self):
        # 初始化各个模块
        self.ui = MainUI()
        self.audio_manager = AudioManager()
        self.network_handler = NetworkHandler()
        self.streaming_manager = StreamingResponseManager(self.ui, self)  # 传递自引用
        
        # 流式消息处理器
        self.message_handler = StreamingMessageHandler(self.audio_manager)
        self._setup_message_callbacks()
        
        # 请求时间记录
        self.request_start_time = None
        self.first_response_received = False
        self.first_audio_received = False
        self.audio_time = None  # 存储音频响应时间
        self.request_type = None  # 请求类型标记
        self.audio_playback_start_time = None  # 音频播放开始时间
        
        # 设置UI事件回调
        self._setup_ui_callbacks()
        
        # 设置窗口关闭事件
        self.ui.set_window_close_callback(self.on_closing)
        
        # 设置WAV流式播放状态回调
        if self.audio_manager.use_wav_streaming and self.audio_manager.wav_stream_manager:
            self.audio_manager.wav_stream_manager.set_status_callback(self.ui.set_status)
        
        # 设置音频播放开始回调
        self.audio_manager.set_audio_playback_start_callback(self._on_audio_playback_start)
    
    def _setup_ui_callbacks(self):
        """设置UI事件回调"""
        self.ui.on_send_message_callback = self.on_send_message
        self.ui.on_stream_chat_callback = self.on_stream_chat
        self.ui.on_cloud_chat_callback = self.on_cloud_chat
        self.ui.on_normal_chat_callback = self.on_normal_chat
        self.ui.on_upload_audio_callback = self.on_upload_audio
        self.ui.on_show_history_callback = self.on_show_history
        self.ui.on_test_wav_stream_callback = self.on_test_wav_stream
    
    def _setup_message_callbacks(self):
        """设置流式消息处理回调 - 修复文本显示问题"""
        
        async def on_text_update(content, full_text):
            """文本更新回调"""
            self._record_first_response()
            print(f"🔍 UI文本更新: '{full_text}' (长度: {len(full_text)})")
            self.ui.root.after(0, 
                lambda: self.streaming_manager.update_local_response(full_text))
        
        async def on_text_complete(full_text):
            """文本完成回调 - 自动触发TTS"""
            print(f"✅ 文本完成: '{full_text}'")
            self.ui.root.after(0, 
                lambda: self.streaming_manager.update_local_response(full_text))
            
            # 自动调用TTS生成音频
            if full_text and full_text.strip():
                print(f"🎵 文本完成后自动触发TTS...")
                self.ui.root.after(100, lambda: self._auto_tts_after_text_complete(full_text.strip()))
        
        async def on_audio_start(message):
            """音频开始回调"""
            self._record_first_audio()
            self.ui.root.after(0, 
                lambda: self.ui.set_status("🎵 开始接收语音..."))
        
        async def on_audio_status(status):
            """音频状态回调"""
            self.ui.root.after(0, lambda: self.ui.set_status(status))
        
        async def on_audio_chunk(message):
            """音频块回调"""
            # 在这里可以添加音频块处理的UI更新逻辑
            pass
        
        async def on_audio_end(message):
            """音频结束回调"""
            self.ui.root.after(0, 
                lambda: self.ui.set_status("🎵 语音播放完成"))
        
        async def on_token_usage(message):
            """Token使用回调"""
            # 在这里可以添加token统计逻辑
            pass
        
        async def on_error(message):
            """错误处理回调"""
            error_msg = message.get("error", "未知错误")
            self.ui.root.after(0, 
                lambda: self.ui.show_error("错误", error_msg))
        
        async def on_done(message):
            """完成回调"""
            # 确保最终文本显示
            final_text = self.message_handler.get_current_text()
            if final_text:
                print(f"📋 最终文本显示: '{final_text}'")
                self.ui.root.after(0, 
                    lambda: self.streaming_manager.finalize_response("cloud", final_text))
            
            self.ui.root.after(0, self._finish_current_request)
        
        # 注册所有回调
        self.message_handler.set_callback("text_update", on_text_update)
        self.message_handler.set_callback("text_complete", on_text_complete)
        self.message_handler.set_callback("audio_start", on_audio_start)
        self.message_handler.set_callback("audio_status", on_audio_status)
        self.message_handler.set_callback("audio_chunk", on_audio_chunk)
        self.message_handler.set_callback("audio_end", on_audio_end)
        self.message_handler.set_callback("token_usage", on_token_usage)
        self.message_handler.set_callback("error", on_error)
        self.message_handler.set_callback("done", on_done)
    
    def _finish_current_request(self):
        """完成当前请求"""
        self.ui.enable_buttons()
        self.ui.set_status("就绪")
        
        # 重置消息处理器状态
        self.message_handler.reset()
        self.ui.on_clear_chat_callback = self.on_clear_chat
    
    def on_send_message(self):
        """发送消息事件处理"""
        message = self.ui.get_message_text()
        if not message:
            return
        
        self.ui.clear_message_text()
        self.ui.append_to_chat(message, "用户")
    
    def on_stream_chat(self):
        """流式聊天"""
        message = self.ui.get_last_user_message()
        if not message:
            self.ui.show_warning("警告", "请先输入消息")
            return
        
        # 重置流式响应状态
        self.streaming_manager.reset_streaming_response()
        
        # 开始聊天请求计时
        self._start_chat_request_timer()
        
        self.ui.set_status("正在发送流式请求...")
        self.ui.disable_buttons()
        
        # 在新线程中运行异步函数
        thread = threading.Thread(target=self._run_async_stream_chat, args=(message,))
        thread.daemon = True
        thread.start()
    
    def on_cloud_chat(self):
        """云端流式聊天"""
        message = self.ui.get_last_user_message()
        if not message:
            self.ui.show_warning("警告", "请先输入消息")
            return
        
        # 重置流式响应状态
        self.streaming_manager.reset_streaming_response()
        
        # 开始聊天请求计时
        self._start_chat_request_timer()
        
        self.ui.set_status("正在发送云端流式请求...")
        self.ui.disable_buttons()
        
        # 在新线程中运行异步函数
        thread = threading.Thread(target=self._run_async_cloud_chat, args=(message,))
        thread.daemon = True
        thread.start()
    
    def on_normal_chat(self):
        """普通聊天"""
        message = self.ui.get_last_user_message()
        if not message:
            self.ui.show_warning("警告", "请先输入消息")
            return
        
        # 开始聊天请求计时
        self._start_chat_request_timer()
        
        self.ui.set_status("正在发送普通请求...")
        self.ui.disable_buttons()
        
        thread = threading.Thread(target=self._normal_chat, args=(message,))
        thread.daemon = True
        thread.start()
    
    def on_upload_audio(self):
        """上传音频文件"""
        # 打开文件选择对话框
        audio_file = self.ui.show_file_dialog("选择音频文件")
        
        if not audio_file:
            return
        
        # 检查文件大小
        try:
            file_size = os.path.getsize(audio_file)
            if file_size > Config.MAX_AUDIO_FILE_SIZE:
                self.ui.show_error("错误", 
                    f"文件太大（{file_size / 1024 / 1024:.1f}MB），最大支持{Config.MAX_AUDIO_FILE_SIZE / 1024 / 1024}MB")
                return
        except Exception as e:
            self.ui.show_error("错误", f"无法读取文件信息: {e}")
            return
        
        self.ui.append_to_chat(
            f"📎 正在上传音频文件: {os.path.basename(audio_file)} ({file_size / 1024 / 1024:.1f}MB)", 
            "用户"
        )
        
        # 开始计时
        self._start_request_timer()
        
        self.ui.set_status("正在上传音频文件...")
        self.ui.disable_buttons()
        
        # 在新线程中处理音频上传
        thread = threading.Thread(target=self._upload_audio_file, args=(audio_file,))
        thread.daemon = True
        thread.start()
    
    def on_show_history(self):
        """显示聊天历史"""
        self.ui.set_status("正在获取历史记录...")
        
        thread = threading.Thread(target=self._show_history)
        thread.daemon = True
        thread.start()
    
    def on_clear_chat(self):
        """清空聊天记录"""
        self.ui.clear_chat_display()
    
    def on_test_wav_stream(self):
        """测试WAV流式播放"""
        if not self.audio_manager.use_wav_streaming:
            self.ui.show_warning("提示", "WAV流式播放功能不可用")
            return
        
        # 预定义的测试文本
        test_text = "大概率是没有的，我也希望如此，毕竟自己的故事还是应当由自己来诉说。"
        
        self.ui.append_to_chat(f"🎵 开始WAV流式播放测试: {test_text}", "系统")
        self.ui.set_status("正在启动WAV流式播放测试...")
        self.ui.disable_buttons()
        
        # 在新线程中运行测试
        thread = threading.Thread(target=self._test_wav_stream, args=(test_text,))
        thread.daemon = True
        thread.start()
    
    def _test_wav_stream(self, text: str):
        """在后台线程中执行WAV流式播放测试"""
        try:
            # 状态更新回调
            def status_callback(message):
                self.ui.root.after(0, lambda: self.ui.set_status(message))
            
            # 启动WAV流式播放
            success = self.audio_manager.play_wav_stream_direct(text, status_callback)
            
            if success:
                self.ui.root.after(0, 
                    lambda: self.ui.append_to_chat("✅ WAV流式播放测试启动成功", "系统"))
                
                # 等待一段时间让播放完成
                time.sleep(3)
                
                # 显示统计信息
                stats = self.audio_manager.get_wav_stream_stats()
                if stats.get("wav_stream_available", False):
                    total_received = stats.get("total_received", 0)
                    total_played = stats.get("total_played", 0)
                    duration = stats.get("duration", 0)
                    
                    stats_msg = f"📊 播放统计: 接收 {total_received//1024}KB, 播放 {total_played//1024}KB, 时长 {duration:.2f}s"
                    self.ui.root.after(0, 
                        lambda: self.ui.append_to_chat(stats_msg, "系统"))
                
                self.ui.root.after(0, 
                    lambda: self.ui.set_status("WAV流式播放测试完成"))
            else:
                self.ui.root.after(0, 
                    lambda: self.ui.append_to_chat("❌ WAV流式播放测试启动失败", "系统"))
                self.ui.root.after(0, 
                    lambda: self.ui.set_status("WAV流式播放测试失败"))
            
        except Exception as e:
            error_msg = f"WAV流式播放测试异常: {e}"
            print(error_msg)
            self.ui.root.after(0, 
                lambda: self.ui.append_to_chat(f"❌ {error_msg}", "系统"))
        finally:
            self.ui.root.after(0, self.ui.enable_buttons)
    
    def _auto_tts_after_text_complete(self, text: str):
        """文本完成后自动调用TTS"""
        try:
            print(f"🎵 开始自动TTS生成，文本: '{text[:50]}...'")
            self.ui.set_status("🎵 正在生成语音...")
            
            # 直接使用现有的WAV流式播放功能
            success = self.audio_manager.play_wav_stream_direct(text)
            
            if success:
                print("✅ 自动TTS启动成功")
                # 设置一个定时器检查播放状态
                self.ui.root.after(1000, self._check_tts_status)
            else:
                print("❌ 自动TTS启动失败")
                self.ui.set_status("❌ TTS启动失败")
            
        except Exception as e:
            error_msg = f"自动TTS启动异常: {e}"
            print(error_msg)
            self.ui.append_to_chat(f"❌ {error_msg}", "系统")
            self.ui.set_status("就绪")

    def _check_tts_status(self):
        """检查TTS播放状态"""
        try:
            if self.audio_manager.use_wav_streaming:
                stats = self.audio_manager.get_wav_stream_stats()
                if stats and stats.get("wav_stream_available", False):
                    is_playing = stats.get("is_playing", False)
                    total_received = stats.get("total_received", 0)
                    
                    if not is_playing and total_received > 0:
                        # 播放完成
                        print("✅ 自动TTS播放完成")
                        self.ui.set_status("✅ 语音播放完成")
                        return
                    elif is_playing:
                        # 继续播放中，继续检查
                        self.ui.root.after(1000, self._check_tts_status)
                        return
            
            # 默认情况下设置为完成
            self.ui.root.after(3000, lambda: self.ui.set_status("就绪"))
            
        except Exception as e:
            print(f"检查TTS状态异常: {e}")
            self.ui.set_status("就绪")
    
    def _run_async_stream_chat(self, message: str):
        """在新线程中运行异步流式聊天"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._stream_chat_async(message))
        finally:
            loop.close()
    
    def _run_async_cloud_chat(self, message: str):
        """在新线程中运行异步云端流式聊天"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._cloud_chat_async(message))
        finally:
            loop.close()
    
    async def _stream_chat_async(self, message: str):
        """异步流式聊天 - 使用新的音频处理逻辑"""
        try:
            # 使用新的流式消息处理器
            await self.network_handler.stream_chat_async(
                message, 
                on_data_received=self.message_handler.handle_message_line
            )
        except Exception as e:
            error_msg = str(e)
            print(f"流式聊天异常: {error_msg}")
            
            # 如果是chunk太大的错误，尝试用普通方式获取响应
            if "Chunk too big" in error_msg or "chunk" in error_msg.lower():
                print("检测到chunk错误，尝试使用普通聊天方式...")
                self.ui.root.after(0, lambda: self.ui.append_to_chat("流式响应失败，尝试普通聊天...", "系统"))
                try:
                    self._normal_chat(message)
                    return
                except Exception as fallback_error:
                    print(f"备选方案也失败: {fallback_error}")
            
            self.ui.root.after(0, 
                lambda: self.ui.append_to_chat(f"流式聊天失败: {error_msg}", "系统"))
        finally:
            self.ui.root.after(0, self.ui.enable_buttons)
    
    async def _cloud_chat_async(self, message: str):
        """异步云端流式聊天 - 使用新的音频处理逻辑"""
        try:
            # 使用新的流式消息处理器
            await self.network_handler.cloud_chat_async(
                message, 
                on_data_received=self.message_handler.handle_message_line
            )
        except Exception as e:
            error_msg = str(e)
            print(f"云端流式聊天异常: {error_msg}")
            self.ui.root.after(0, 
                lambda: self.ui.append_to_chat(f"云端流式聊天失败: {error_msg}", "系统"))
        finally:
            self.ui.root.after(0, self.ui.enable_buttons)
    
    def _normal_chat(self, message: str):
        """普通聊天请求"""
        try:
            data = self.network_handler.normal_chat_request(message)
            
            # 记录第一个响应时间
            self._record_first_response()
            
            text_response = data.get("text", "")
            audio_path = data.get("audio", "")
            
            # 更新UI
            self.ui.root.after(0, lambda: self.ui.append_to_chat(text_response, "Elysia"))
            
            # 播放音频文件
            if audio_path:
                self.ui.root.after(0, 
                    lambda: self.audio_manager.play_audio_file(audio_path, self.ui.append_to_chat))
            
            self.ui.root.after(0, lambda: self.ui.set_status("响应完成"))
            
        except Exception as e:
            print(f"普通聊天异常: {e}")
            error_msg = str(e)
            self.ui.root.after(0, 
                lambda: self.ui.append_to_chat(f"普通聊天失败: {error_msg}", "系统"))
        finally:
            self.ui.root.after(0, self.ui.enable_buttons)
    
    def _upload_audio_file(self, audio_file: str):
        """上传音频文件到服务器"""
        try:
            response = self.network_handler.upload_audio_file_sync(audio_file)
            
            # 检查响应类型
            content_type = response.headers.get('content-type', '').lower()
            print(f"响应类型: {content_type}")
            
            if 'application/json' in content_type:
                # 如果是JSON响应，按原来的方式处理
                try:
                    data = response.json()
                    print(f"JSON响应数据: {data}")
                    
                    # 提取响应内容
                    transcription = data.get("transcription", "")
                    text_response = data.get("text", "")
                    audio_path = data.get("audio", "")
                    
                    # 更新UI显示转录结果
                    if transcription:
                        self.ui.root.after(0, 
                            lambda: self.ui.append_to_chat(f"🎤 语音转录: {transcription}", "系统"))
                    
                    # 显示AI响应
                    if text_response:
                        self.ui.root.after(0, 
                            lambda: self.ui.append_to_chat(text_response, "Elysia"))
                    
                    # 播放响应音频
                    if audio_path:
                        self.ui.root.after(0, 
                            lambda: self.audio_manager.play_audio_file(audio_path, self.ui.append_to_chat))
                        
                except Exception as e:
                    print(f"JSON解析失败: {e}")
                    # 尝试处理为流式响应
                    self._process_audio_streaming_response(response)
                    return
            else:
                # 处理流式响应
                print("检测到流式响应，开始处理...")
                self._process_audio_streaming_response(response)
                return
            
            self.ui.root.after(0, lambda: self.ui.set_status("音频处理完成"))
            
        except Exception as e:
            error_msg = str(e)
            print(f"音频上传异常: {error_msg}")
            
            # 检查是否是JSON解析错误
            if "Extra data" in error_msg or "JSON" in error_msg:
                print("检测到JSON解析错误，尝试异步流式处理")
                try:
                    self._upload_audio_file_async(audio_file)
                    return
                except Exception as stream_error:
                    print(f"异步流式处理也失败: {stream_error}")
            
            self.ui.root.after(0, 
                lambda: self.ui.append_to_chat(f"音频处理失败: {error_msg}", "系统"))
        finally:
            self.ui.root.after(0, self.ui.enable_buttons)
    
    def _process_audio_streaming_response(self, response):
        """处理音频上传的流式响应"""
        current_response = ""
        transcription_shown = False
        
        def on_data_received(data: Dict[str, Any]):
            nonlocal current_response, transcription_shown
            
            # 处理转录结果
            if data.get("type") == "transcription" or "transcription" in data:
                # 记录第一个响应时间（转录结果）
                self._record_first_response()
                
                transcription = data.get("transcription", "")
                if transcription and not transcription_shown:
                    self.ui.root.after(0, 
                        lambda t=transcription: self.ui.append_to_chat(f"🎤 语音转录: {t}", "系统"))
                    transcription_shown = True
            
            # 处理文本响应
            elif data.get("type") == "text":
                # 记录第一个响应时间（如果转录还没记录的话）
                self._record_first_response()
                
                content = data.get("content", "")
                current_response += content
                
                # 更新UI
                self.ui.root.after(0, 
                    lambda c=current_response: self.streaming_manager.update_audio_response(c))
            
            # 处理音频流
            elif data.get("type") == "audio_start":
                # 使用新的流式音频消息处理方法
                message_data = {"type": "audio_start", "audio_format": data.get("audio_format", "wav")}
                self.ui.root.after(0, 
                    lambda md=message_data: 
                    self.audio_manager.handle_streaming_audio_message(md, self.ui.set_status))
            
            elif data.get("type") == "audio_chunk":
                # 记录第一个音频块的时间
                self._record_first_audio()
                
                audio_data = data.get("audio_data", "")
                chunk_size = data.get("chunk_size", 0)
                if audio_data:
                    # 使用新的流式音频消息处理方法
                    message_data = {
                        "type": "audio_chunk",
                        "audio_data": audio_data,
                        "chunk_size": chunk_size
                    }
                    self.ui.root.after(0, 
                        lambda md=message_data: 
                        self.audio_manager.handle_streaming_audio_message(md, self.ui.set_status))
            
            elif data.get("type") == "audio_end":
                self.ui.root.after(0, 
                    lambda: self.audio_manager.finalize_streaming_audio(
                        lambda msg: None, self._schedule_cleanup))  # 隐藏调试消息
            
            elif data.get("type") == "done":
                self.ui.root.after(0, lambda: self.ui.set_status("音频处理完成"))
                self.ui.root.after(0, 
                    lambda: self.streaming_manager.finalize_response("audio", current_response))
                self.ui.root.after(0, self.streaming_manager.reset_streaming_response)
            
            elif data.get("type") == "timing":
                # 处理计时信息
                timing_info = data.get("timing", {})
                if timing_info:
                    self.ui.root.after(0, 
                        lambda t=timing_info: self.ui.show_timing_info(t))
            
            elif data.get("type") == "error":
                error_msg = data.get("error", "未知错误")
                self.ui.root.after(0, 
                    lambda msg=error_msg: self.ui.append_to_chat(f"音频处理错误: {msg}", "系统"))
        
        # 重置流式响应状态
        self.streaming_manager.reset_streaming_response()
        
        try:
            self.network_handler.process_streaming_response(response, on_data_received)
        except Exception as e:
            print(f"处理音频流式响应异常: {e}")
            self.ui.root.after(0, 
                lambda: self.ui.append_to_chat(f"处理音频流式响应失败: {e}", "系统"))
    
    def _upload_audio_file_async(self, audio_file: str):
        """使用异步方式上传音频文件"""
        thread = threading.Thread(target=self._run_async_audio_upload, args=(audio_file,))
        thread.daemon = True
        thread.start()
    
    def _run_async_audio_upload(self, audio_file: str):
        """在新线程中运行异步音频上传"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._audio_upload_async(audio_file))
        finally:
            loop.close()
    
    async def _audio_upload_async(self, audio_file: str):
        """异步音频上传和流式响应处理"""
        current_response = ""
        transcription_shown = False
        
        def on_data_received(data: Dict[str, Any]):
            nonlocal current_response, transcription_shown
            
            # 处理转录结果
            if data.get("type") == "transcription" or "transcription" in data:
                # 记录第一个响应时间（转录结果）
                self._record_first_response()
                
                transcription = data.get("transcription", "")
                if transcription and not transcription_shown:
                    self.ui.root.after(0, 
                        lambda t=transcription: self.ui.append_to_chat(f"🎤 语音转录: {t}", "系统"))
                    transcription_shown = True
            
            # 处理文本响应
            elif data.get("type") == "text":
                # 记录第一个响应时间（如果转录还没记录的话）
                self._record_first_response()
                
                content = data.get("content", "")
                current_response += content
                
                # 更新UI
                self.ui.root.after(0, 
                    lambda c=current_response: self.streaming_manager.update_audio_response(c))
            
            # 处理音频流
            elif data.get("type") == "audio_start":
                # 使用新的流式音频消息处理方法
                message_data = {"type": "audio_start", "audio_format": data.get("audio_format", "wav")}
                self.ui.root.after(0, 
                    lambda md=message_data: 
                    self.audio_manager.handle_streaming_audio_message(md, self.ui.set_status))
            
            elif data.get("type") == "audio_chunk":
                # 记录第一个音频块的时间
                self._record_first_audio()
                
                audio_data = data.get("audio_data", "")
                chunk_size = data.get("chunk_size", 0)
                if audio_data:
                    # 使用新的流式音频消息处理方法
                    message_data = {
                        "type": "audio_chunk",
                        "audio_data": audio_data,
                        "chunk_size": chunk_size
                    }
                    self.ui.root.after(0, 
                        lambda md=message_data: 
                        self.audio_manager.handle_streaming_audio_message(md, self.ui.set_status))
            
            elif data.get("type") == "audio_end":
                self.ui.root.after(0, 
                    lambda: self.audio_manager.finalize_streaming_audio(
                        lambda msg: None, self._schedule_cleanup))  # 隐藏调试消息
            
            elif data.get("type") == "done":
                self.ui.root.after(0, lambda: self.ui.set_status("音频处理完成"))
                self.ui.root.after(0, 
                    lambda: self.streaming_manager.finalize_response("audio", current_response))
                self.ui.root.after(0, self.streaming_manager.reset_streaming_response)
            
            elif data.get("type") == "timing":
                # 处理计时信息
                timing_info = data.get("timing", {})
                if timing_info:
                    self.ui.root.after(0, 
                        lambda t=timing_info: self.ui.show_timing_info(t))
            
            elif data.get("type") == "error":
                error_msg = data.get("error", "未知错误")
                self.ui.root.after(0, 
                    lambda msg=error_msg: self.ui.append_to_chat(f"音频处理错误: {msg}", "系统"))
        
        # 重置流式响应状态
        self.ui.root.after(0, self.streaming_manager.reset_streaming_response)
        
        try:
            await self.network_handler.audio_upload_async(audio_file, on_data_received)
        except Exception as e:
            error_msg = str(e)
            print(f"异步音频上传异常: {error_msg}")
            self.ui.root.after(0, 
                lambda: self.ui.append_to_chat(f"异步音频上传失败: {error_msg}", "系统"))
        finally:
            self.ui.root.after(0, self.ui.enable_buttons)
    
    def _show_history(self):
        """获取并显示历史记录"""
        try:
            history = self.network_handler.get_chat_history()
            
            self.ui.root.after(0, lambda: self.ui.append_to_chat("=== 聊天历史 ===", "系统"))
            for record in history:
                self.ui.root.after(0, lambda r=record: self.ui.append_to_chat(r, "历史"))
            self.ui.root.after(0, lambda: self.ui.append_to_chat("=== 历史结束 ===", "系统"))
            
            self.ui.root.after(0, lambda: self.ui.set_status("历史记录获取完成"))
            
        except Exception as e:
            error_msg = str(e)
            self.ui.root.after(0, 
                lambda: self.ui.append_to_chat(f"获取历史失败: {error_msg}", "系统"))
    
    def _schedule_cleanup(self, delay: int, cleanup_func):
        """安排延迟清理"""
        self.ui.root.after(delay, cleanup_func)
    
    def _start_request_timer(self):
        """开始请求计时"""
        self.request_start_time = time.time() * 1000  # 转换为毫秒
        self.first_response_received = False
        self.first_audio_received = False
        self.audio_playback_start_time = None  # 重置音频播放开始时间
        self.request_type = None  # 记录请求类型
        print(f"开始请求计时: {self.request_start_time}")
    
    def _start_chat_request_timer(self):
        """开始聊天请求计时"""
        self.request_start_time = time.time() * 1000  # 转换为毫秒
        self.first_response_received = False
        self.first_audio_received = False
        self.audio_playback_start_time = None  # 重置音频播放开始时间
        self.request_type = "chat"  # 标记为聊天请求
        print(f"开始聊天请求计时: {self.request_start_time}")
    
    def _on_audio_playback_start(self):
        """音频播放开始回调"""
        if self.request_start_time is not None:
            self.audio_playback_start_time = time.time() * 1000
            total_time = self.audio_playback_start_time - self.request_start_time
            print(f"音频播放开始，从请求开始总耗时: {total_time:.0f}ms")
            
            # 在UI中显示总音频响应时间
            self.ui.root.after(0, lambda: self.ui.show_total_audio_time(total_time))
    
    def _record_first_response(self):
        """记录第一个响应的时间"""
        if not self.first_response_received and self.request_start_time is not None:
            current_time = time.time() * 1000
            response_time = current_time - self.request_start_time
            self.first_response_received = True
            print(f"收到第一个响应，耗时: {response_time:.0f}ms")
            
            # 在UI中显示请求时间
            self.ui.root.after(0, lambda: self.ui.show_request_time(response_time))
    
    def _record_first_audio(self):
        """记录第一个音频块的时间"""
        if not self.first_audio_received and self.request_start_time is not None:
            current_time = time.time() * 1000
            self.audio_time = current_time - self.request_start_time  # 存储时间，稍后显示
            self.first_audio_received = True
            print(f"收到第一个音频块，耗时: {self.audio_time:.0f}ms")
            
            # 不在这里立即显示时间，而是在流式响应完成后显示
    
    def on_closing(self):
        """窗口关闭事件处理"""
        try:
            # 清理临时文件
            self.audio_manager.cleanup_all_temp_files()
            # 停止音频播放
            self.audio_manager.stop_all_audio()
        except Exception as e:
            print(f"关闭清理失败: {e}")
        finally:
            self.ui.quit()
    
    def run(self):
        """运行客户端"""
        self.ui.run()


if __name__ == "__main__":
    """直接运行此文件时的入口"""
    try:
        print("正在启动 Elysia 客户端...")
        client = ElysiaClient()
        client.run()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行异常: {e}")
        import traceback
        traceback.print_exc()
