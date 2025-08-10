"""
音频功能控制器
"""
import os
import time
from core.config import Config


class AudioController:
    """音频功能控制器"""
    
    def __init__(self, audio_manager, network_handler, ui_helper, 
                 performance_optimizer, state_manager, thread_manager, request_helper):
        self.audio_manager = audio_manager
        self.network_handler = network_handler
        self.ui_helper = ui_helper
        self.performance_optimizer = performance_optimizer
        self.state_manager = state_manager
        self.thread_manager = thread_manager
        self.request_helper = request_helper
        
        # 缓存文件大小计算
        self._get_file_size_mb = performance_optimizer.cache_manager.cached_method(
            maxsize=32, ttl=300
        )(self._get_file_size_mb_impl)
        
        # 设置音频播放开始回调
        self.audio_manager.set_audio_playback_start_callback(self._on_audio_playback_start)
    
    def handle_upload_audio(self, audio_file: str):
        """处理音频上传"""
        if not audio_file:
            return False
            
        if not self._validate_audio_file(audio_file):
            return False
        
        self._prepare_audio_upload(audio_file)
        
        # 使用线程管理器处理音频上传
        task_wrapper = self.request_helper.execute_request_with_cleanup(
            self._upload_audio_file, audio_file
        )
        
        self.thread_manager.submit_task(task_wrapper, task_name="audio_upload")
        return True
    
    def handle_wav_stream_test(self, test_text: str):
        """处理WAV流式播放测试"""
        self.ui_helper.safe_append_chat(f"🎵 开始WAV流式播放测试: {test_text}", "系统")
        self.ui_helper.debounced_status_update("正在启动WAV流式播放测试...")
        self.ui_helper.safe_disable_buttons()
        
        # 注意：此处不启动状态管理器计时，因为WAV流播放有自己的时间统计
        # 避免显示不一致的时间信息
        
        task_wrapper = self.request_helper.execute_request_with_cleanup(
            self._test_wav_stream, test_text
        )
        
        self.thread_manager.submit_task(task_wrapper, task_name="wav_stream_test")
    
    def handle_auto_tts(self, text: str):
        """处理自动TTS"""
        print(f"🎵🎵🎵 handle_auto_tts 被调用了! 文本: '{text[:50]}...'")
        try:
            print(f"🎵 开始自动TTS生成，文本: '{text[:50]}...'")
            self.ui_helper.schedule_ui_update(
                lambda: self.ui_helper.ui.set_status("🎵 正在生成语音...")
            )
            
            # 直接使用现有的WAV流式播放功能
            success = self.audio_manager.play_wav_stream_direct(text)
            
            if success:
                print("✅ 自动TTS启动成功")
                # 设置一个定时器检查播放状态
                self.ui_helper.schedule_ui_update(
                    lambda: self.ui_helper.ui.root.after(1000, self._check_tts_status), 
                    delay=0
                )
            else:
                print("❌ 自动TTS启动失败")
                self.ui_helper.schedule_ui_update(
                    lambda: self.ui_helper.ui.set_status("❌ TTS启动失败")
                )
            
        except Exception as e:
            error_msg = f"自动TTS启动异常: {e}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            self.ui_helper.schedule_ui_update(
                lambda: self.ui_helper.safe_append_chat(f"❌ {error_msg}", "系统")
            )
            self.ui_helper.schedule_ui_update(
                lambda: self.ui_helper.ui.set_status("就绪")
            )
    
    def _validate_audio_file(self, audio_file: str) -> bool:
        """验证音频文件"""
        try:
            file_size_mb = self._get_file_size_mb(audio_file)
            max_size_mb = Config.MAX_AUDIO_FILE_SIZE / 1024 / 1024
            
            if file_size_mb > max_size_mb:
                self.ui_helper.show_error_safe("错误", 
                    f"文件太大（{file_size_mb:.1f}MB），最大支持{max_size_mb}MB")
                return False
            return True
        except Exception as e:
            self.ui_helper.show_error_safe("错误", f"无法读取文件信息: {e}")
            return False
    
    def _get_file_size_mb_impl(self, file_path: str) -> float:
        """获取文件大小（MB）实现"""
        return os.path.getsize(file_path) / 1024 / 1024
    
    def _prepare_audio_upload(self, audio_file: str):
        """准备音频上传"""
        file_size_mb = self._get_file_size_mb(audio_file)
        
        self.ui_helper.safe_append_chat(
            f"📎 正在上传音频文件: {os.path.basename(audio_file)} ({file_size_mb:.1f}MB)", 
            "用户"
        )
        
        self.state_manager.start_request_timer("audio_upload")
        self.ui_helper.debounced_status_update("正在上传音频文件...")
        self.ui_helper.safe_disable_buttons()
    
    def _upload_audio_file(self, audio_file: str):
        """上传音频文件到服务器"""
        try:
            print(f"📤 开始上传音频文件: {audio_file}")
            
            response = self.network_handler.upload_audio_file(audio_file)
            
            if response:
                print("✅ 音频上传成功，开始处理响应")
                self.ui_helper.schedule_ui_update(
                    lambda: self.ui_helper.ui.set_status("🎵 正在处理音频响应...")
                )
                
                # 处理音频上传的流式响应
                self._process_audio_streaming_response(response)
            else:
                error_msg = "音频上传失败：服务器无响应"
                print(f"❌ {error_msg}")
                self.ui_helper.show_error_safe("上传失败", error_msg)
                
        except Exception as e:
            error_msg = f"音频上传异常: {e}"
            print(f"❌ {error_msg}")
            import traceback
            print(traceback.format_exc())
            self.ui_helper.show_error_safe("上传失败", error_msg)
        finally:
            self.ui_helper.schedule_ui_update(self._finish_audio_request)
    
    def _test_wav_stream(self, text: str):
        """在后台线程中执行WAV流式播放测试"""
        try:
            print(f"🎵 开始WAV流式播放测试: {text}")
            self.ui_helper.schedule_ui_update(
                lambda: self.ui_helper.ui.set_status("🎵 正在生成测试语音...")
            )
            
            # 使用音频管理器的WAV流式播放功能
            success = self.audio_manager.play_wav_stream_direct(text)
            
            if success:
                print("✅ WAV流式播放测试启动成功")
                self.ui_helper.schedule_ui_update(
                    lambda: self.ui_helper.safe_append_chat("✅ WAV流式播放测试启动成功", "系统")
                )
                # 设置状态检查
                self.ui_helper.schedule_ui_update(
                    lambda: self.ui_helper.ui.root.after(1000, self._check_tts_status),
                    delay=0
                )
            else:
                print("❌ WAV流式播放测试启动失败")
                self.ui_helper.schedule_ui_update(
                    lambda: self.ui_helper.safe_append_chat("❌ WAV流式播放测试启动失败", "系统")
                )
                
        except Exception as e:
            error_msg = f"WAV流式播放测试异常: {e}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            self.ui_helper.schedule_ui_update(
                lambda: self.ui_helper.safe_append_chat(f"❌ {error_msg}", "系统")
            )
        finally:
            self.ui_helper.schedule_ui_update(self._finish_audio_request)
    
    def _process_audio_streaming_response(self, response):
        """处理音频上传的流式响应"""
        # 使用统一的音频数据处理器
        on_data_received = self._create_audio_data_handler()
        
        try:
            # 处理流式响应
            self.network_handler.process_streaming_response(response, on_data_received)
        except Exception as e:
            error_msg = f"处理音频响应异常: {e}"
            print(f"❌ {error_msg}")
            self.ui_helper.show_error_safe("处理失败", error_msg)
    
    def _create_audio_data_handler(self):
        """创建统一的音频数据处理器"""
        current_response = ""
        transcription_shown = False
        
        def on_data_received(data):
            nonlocal current_response, transcription_shown
            
            try:
                if isinstance(data, dict):
                    if data.get("type") == "transcription" and not transcription_shown:
                        transcription = data.get("text", "")
                        if transcription:
                            self.ui_helper.schedule_ui_update(
                                lambda: self.ui_helper.safe_append_chat(f"🎤 音频转录: {transcription}", "系统")
                            )
                            transcription_shown = True
                    
                    elif data.get("type") == "response":
                        content = data.get("content", "")
                        if content:
                            current_response += content
                            # 更新UI显示
                            self.ui_helper.schedule_ui_update(
                                lambda: self.ui_helper.safe_append_chat(current_response, "Elysia")
                            )
                
            except Exception as e:
                print(f"❌ 处理音频数据异常: {e}")
        
        return on_data_received
    
    def _check_tts_status(self):
        """检查TTS播放状态"""
        try:
            if hasattr(self.audio_manager, 'wav_stream_manager') and self.audio_manager.wav_stream_manager:
                if self.audio_manager.wav_stream_manager.is_playing():
                    # 仍在播放，继续检查
                    self.ui_helper.schedule_ui_update(
                        lambda: self.ui_helper.ui.root.after(1000, self._check_tts_status),
                        delay=0
                    )
                else:
                    # 播放完成
                    self.ui_helper.schedule_ui_update(
                        lambda: self.ui_helper.ui.set_status("🎵 语音播放完成")
                    )
                    # 2秒后重置状态
                    self.ui_helper.schedule_ui_update(
                        lambda: self.ui_helper.ui.root.after(2000, 
                            lambda: self.ui_helper.ui.set_status("就绪")),
                        delay=0
                    )
            else:
                self.ui_helper.schedule_ui_update(
                    lambda: self.ui_helper.ui.set_status("就绪")
                )
                
        except Exception as e:
            print(f"检查TTS状态异常: {e}")
            self.ui_helper.schedule_ui_update(
                lambda: self.ui_helper.ui.set_status("就绪")
            )
    
    def _on_audio_playback_start(self):
        """音频播放开始回调"""
        total_time = self.state_manager.record_audio_playback_start()
        # 只有在有有效的请求开始时间时才显示总音频响应时间
        # 这避免了WAV流测试时显示不准确的时间统计
        if total_time > 0 and self.state_manager.state.request_start_time:
            self.ui_helper.schedule_ui_update(
                lambda: self.ui_helper.ui.show_total_audio_time(total_time)
            )
    
    def _finish_audio_request(self):
        """完成音频请求"""
        self.ui_helper.schedule_ui_update(lambda: self.ui_helper.ui.enable_buttons())
        self.ui_helper.schedule_ui_update(lambda: self.ui_helper.ui.set_status("就绪"))
