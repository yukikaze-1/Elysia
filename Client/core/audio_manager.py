"""
音频处理模块
处理音频播放、流式音频、临时文件管理等
"""

import pygame
import base64
import tempfile
import platform
import os
import time
import threading
import queue
import asyncio
from typing import List, Optional
from .config import Config

# 尝试导入实时音频模块
try:
    from .realtime_audio_streamer import RealTimeAudioStreamer as _RealTimeAudioStreamer, AudioFormatConverter as _AudioFormatConverter
    REALTIME_AUDIO_AVAILABLE = True
    print("✅ 实时音频模块已加载")
except ImportError as e:
    REALTIME_AUDIO_AVAILABLE = False
    print(f"⚠️ 实时音频模块不可用，将使用传统音频播放: {e}")
    _RealTimeAudioStreamer = None
    _AudioFormatConverter = None


class StreamAudioBuffer:
    """流式音频缓冲区管理器 - 类似 MediaSource API 的概念"""
    
    def __init__(self):
        # 使用配置文件中的参数
        config = Config.STREAM_BUFFER_CONFIG
        self.buffer = queue.Queue(maxsize=500)  # 增加队列大小到500
        self.max_buffer_size = config['max_buffer_size']
        self.auto_play_threshold = config['auto_play_threshold']
        self.target_utilization = config['buffer_utilization_target']
        
        self.current_size = 0
        self.is_ready = False
        self.lock = threading.Lock()
        self.total_chunks_received = 0
        
    def append_chunk(self, chunk: bytes) -> bool:
        """添加音频块到缓冲区"""
        with self.lock:
            # 如果队列接近满，先清理一些旧数据
            if self.buffer.qsize() >= 450:  # 90%容量时开始清理
                self._remove_old_chunks_from_queue()
            
            if self.current_size + len(chunk) > self.max_buffer_size:
                # 缓冲区满，移除最旧的数据
                self._remove_old_chunks()
            
            try:
                self.buffer.put_nowait(chunk)
                self.current_size += len(chunk)
                self.total_chunks_received += 1
                
                # 检查是否达到播放就绪状态
                if not self.is_ready and self.current_size >= self.auto_play_threshold:
                    self.is_ready = True
                    print(f"🎵 流式缓冲区就绪 - 大小: {self.current_size} 字节")
                
                return True
            except queue.Full:
                # 最后的清理尝试
                self._emergency_cleanup()
                try:
                    self.buffer.put_nowait(chunk)
                    self.current_size += len(chunk)
                    self.total_chunks_received += 1
                    return True
                except queue.Full:
                    print("⚠️ 缓冲区队列已满且无法清理")
                    return False
    
    def _remove_old_chunks_from_queue(self):
        """从队列中移除一些旧块"""
        removed_count = 0
        target_remove = min(50, self.buffer.qsize() // 4)  # 移除25%或最多50个
        
        for _ in range(target_remove):
            try:
                old_chunk = self.buffer.get_nowait()
                self.current_size -= len(old_chunk)
                removed_count += 1
            except queue.Empty:
                break
        
        if removed_count > 0:
            print(f"🗑️ 预防性清理: 移除 {removed_count} 个队列块")
    
    def _emergency_cleanup(self):
        """紧急清理队列"""
        removed_count = 0
        target_remove = self.buffer.qsize() // 2  # 移除50%
        
        for _ in range(target_remove):
            try:
                old_chunk = self.buffer.get_nowait()
                self.current_size -= len(old_chunk)
                removed_count += 1
            except queue.Empty:
                break
        
        if removed_count > 0:
            print(f"🚨 紧急清理: 移除 {removed_count} 个队列块")
    
    def get_chunk(self) -> Optional[bytes]:
        """获取音频块"""
        try:
            chunk = self.buffer.get_nowait()
            with self.lock:
                self.current_size -= len(chunk)
            return chunk
        except queue.Empty:
            return None
    
    def _remove_old_chunks(self):
        """移除旧的音频块以腾出空间"""
        target_size = int(self.max_buffer_size * self.target_utilization)
        removed_count = 0
        
        while self.current_size > target_size and not self.buffer.empty():
            try:
                old_chunk = self.buffer.get_nowait()
                self.current_size -= len(old_chunk)
                removed_count += 1
            except queue.Empty:
                break
        
        if removed_count > 0:
            print(f"🗑️ 清理缓冲区: 移除 {removed_count} 个旧音频块")
    
    def clear(self):
        """清空缓冲区"""
        with self.lock:
            while not self.buffer.empty():
                try:
                    self.buffer.get_nowait()
                except queue.Empty:
                    break
            self.current_size = 0
            self.is_ready = False
            self.total_chunks_received = 0
            print("🔄 流式缓冲区已清空")
    
    def get_stats(self) -> dict:
        """获取缓冲区统计信息"""
        return {
            "size": self.current_size,
            "chunks": self.buffer.qsize(),
            "ready": self.is_ready,
            "utilization": min(100, (self.current_size / self.max_buffer_size) * 100),
            "total_received": self.total_chunks_received,
            "threshold_reached": self.current_size >= self.auto_play_threshold
        }


class AudioManager:
    """音频管理器 - 增强版实时流处理"""
    
    def __init__(self):
        self.audio_buffer = bytearray()
        self.current_audio_file: Optional[str] = None
        self.audio_playing = False
        self.temp_audio_files: List[str] = []
        
        # 音频格式跟踪
        self.current_audio_format = "pcm"  # 默认PCM，可以是 "ogg", "wav", "pcm"
        
        # 实时音频流播放器
        self.realtime_streamer = None
        self.use_realtime_streaming = False
        self.realtime_streaming_active = False
        
        # 新增：流式音频缓冲区管理
        self.stream_buffer = StreamAudioBuffer()
        self.auto_play_threshold = 4096  # 4KB自动播放阈值
        
        if REALTIME_AUDIO_AVAILABLE and _RealTimeAudioStreamer:
            try:
                self.realtime_streamer = _RealTimeAudioStreamer()
                self.use_realtime_streaming = True
            except Exception as e:
                print(f"实时音频初始化失败: {e}")
                self.use_realtime_streaming = False
        
        # 初始化pygame音频
        self.init_pygame_audio()
    
    def init_pygame_audio(self) -> bool:
        """初始化pygame音频系统 - 强制匹配服务端配置"""
        try:
            config = Config.PYGAME_AUDIO_CONFIG
            
            # 先完全清理pygame音频
            try:
                pygame.mixer.quit()
            except:
                pass
            
            # 强制初始化为单声道以匹配服务端
            print(f"🔧 强制初始化pygame音频: {config['frequency']}Hz, {config['channels']}声道")
            
            pygame.mixer.pre_init(
                frequency=config['frequency'],
                size=config['size'], 
                channels=config['channels'],  # 强制单声道
                buffer=config['buffer']
            )
            pygame.mixer.init()
            
            # 验证实际设置
            actual_settings = pygame.mixer.get_init()
            if actual_settings:
                actual_freq, actual_size, actual_channels = actual_settings
                print(f"📊 pygame实际设置: {actual_freq}Hz, {actual_channels}声道, {actual_size}位")
                
                # 检查关键设置是否匹配
                if actual_freq != config['frequency']:
                    print(f"⚠️ 警告: 采样率不匹配 (配置: {config['frequency']}, 实际: {actual_freq})")
                
                if actual_channels != config['channels']:
                    print(f"⚠️ 警告: 声道数不匹配 (配置: {config['channels']}, 实际: {actual_channels})")
                    # 如果pygame强制使用双声道，我们需要在音频处理时进行转换
                    if actual_channels == 2 and config['channels'] == 1:
                        print(f"🔄 将在音频处理时进行单声道到双声道转换")
                
                print("✅ pygame音频初始化成功")
                return True
            else:
                print("❌ 无法获取pygame实际设置")
                return False
                
        except Exception as e:
            print(f"❌ pygame音频初始化失败: {e}")
            return False
    
    def play_audio_file(self, audio_path: str, on_status_update=None) -> bool:
        """播放音频文件"""
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            
            if on_status_update:
                on_status_update(f"🎵 播放音频: {audio_path}")
            
            print(f"播放音频文件: {audio_path}")
            return True
            
        except Exception as e:
            error_msg = f"音频播放失败: {str(e)}"
            print(error_msg)
            if on_status_update:
                on_status_update(error_msg)
            return False
    
    def init_streaming_audio_new(self, audio_format: str = "ogg", sample_rate: int = 32000, 
                                channels: int = 1, bit_depth: int = 16):
        """新的流式音频初始化 - 专门针对服务端格式优化"""
        try:
            print(f"🎵 初始化新流式音频: {audio_format}, {sample_rate}Hz, {channels}声道, {bit_depth}bit")
            
            # 记录当前音频格式和参数
            self.current_audio_format = audio_format.lower()
            self.stream_sample_rate = sample_rate
            self.stream_channels = channels
            self.stream_bit_depth = bit_depth
            
            # 清空所有缓冲区
            self.audio_buffer = bytearray()
            self.stream_buffer.clear()
            
            # 重置状态
            self.audio_playing = False
            self.realtime_streaming_active = False
            
            # 验证pygame音频设置是否匹配
            pygame_settings = pygame.mixer.get_init()
            if pygame_settings:
                actual_freq, actual_size, actual_channels = pygame_settings
                print(f"📊 pygame设置: {actual_freq}Hz, {actual_channels}声道, {actual_size}位")
                
                # 检查是否需要重新初始化pygame
                if actual_freq != sample_rate or actual_channels != channels:
                    print(f"🔧 pygame设置不匹配，重新初始化...")
                    self._reinit_pygame_for_streaming(sample_rate, channels, bit_depth)
            
            # 为OGG格式准备临时文件
            if self.current_audio_format == "ogg":
                timestamp = int(time.time() * 1000)
                temp_dir = tempfile.gettempdir()
                self.current_audio_file = os.path.join(temp_dir, f"elysia_ogg_stream_{timestamp}.ogg")
                self.temp_audio_files.append(self.current_audio_file)
                print(f"📁 OGG流式文件: {self.current_audio_file}")
            
            print("✅ 新流式音频初始化完成")
            
        except Exception as e:
            print(f"❌ 新流式音频初始化失败: {e}")
            raise
    
    def _reinit_pygame_for_streaming(self, sample_rate: int, channels: int, bit_depth: int):
        """为流式播放重新初始化pygame"""
        try:
            # 停止当前播放
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            
            # 重新初始化
            pygame.mixer.pre_init(
                frequency=sample_rate,
                size=-bit_depth,  # 负数表示有符号
                channels=channels,
                buffer=1024
            )
            pygame.mixer.init()
            
            # 验证设置
            actual_settings = pygame.mixer.get_init()
            if actual_settings:
                actual_freq, actual_size, actual_channels = actual_settings
                print(f"✅ pygame重新初始化: {actual_freq}Hz, {actual_channels}声道, {actual_size}位")
            
        except Exception as e:
            print(f"pygame重新初始化失败: {e}")
    
    async def try_start_ogg_streaming_playback(self, audio_data: bytes, partial: bool = True):
        """尝试开始OGG流式播放 - 修复文件权限问题"""
        try:
            print(f"🎵 尝试OGG流式播放: {len(audio_data)}字节, 部分数据: {partial}")
            
            if not self.current_audio_file:
                print("❌ 没有OGG流式文件")
                return False
            
            # 创建新的临时文件用于播放，避免权限冲突
            timestamp = int(time.time() * 1000)
            temp_dir = tempfile.gettempdir()
            playback_file = os.path.join(temp_dir, f"elysia_playback_{timestamp}.ogg")
            
            # 写入数据到播放文件
            with open(playback_file, 'wb') as f:
                f.write(audio_data)
            
            # 添加到临时文件列表
            self.temp_audio_files.append(playback_file)
            
            # 验证文件大小
            file_size = os.path.getsize(playback_file)
            print(f"📁 OGG播放文件大小: {file_size}字节")
            
            # 尝试pygame播放
            if file_size >= 16384:  # 至少16KB
                try:
                    # 停止当前播放
                    pygame.mixer.music.stop()
                    
                    pygame.mixer.music.load(playback_file)
                    pygame.mixer.music.play()
                    self.audio_playing = True
                    print("✅ OGG流式播放已开始")
                    return True
                except Exception as play_error:
                    print(f"pygame播放失败: {play_error}")
                    return False
            
            return False
            
        except Exception as e:
            print(f"OGG流式播放失败: {e}")
            return False
    
    async def update_ogg_streaming_playback(self, complete_audio_data: bytes):
        """更新OGG流式播放数据 - 为播放更完整的音频"""
        try:
            print(f"🔄 更新OGG播放文件: {len(complete_audio_data)}字节")
            
            # 停止当前播放
            try:
                pygame.mixer.music.stop()
            except:
                pass
            
            # 创建新的播放文件
            timestamp = int(time.time() * 1000)
            temp_dir = tempfile.gettempdir()
            updated_playback_file = os.path.join(temp_dir, f"elysia_updated_{timestamp}.ogg")
            
            # 写入完整数据
            with open(updated_playback_file, 'wb') as f:
                f.write(complete_audio_data)
            
            # 添加到临时文件列表
            self.temp_audio_files.append(updated_playback_file)
            
            # 验证文件大小
            file_size = os.path.getsize(updated_playback_file)
            print(f"📁 更新后播放文件大小: {file_size}字节")
            
            # 重新开始播放
            try:
                pygame.mixer.music.load(updated_playback_file)
                pygame.mixer.music.play()
                print("✅ OGG更新播放已启动")
                return True
            except Exception as play_error:
                print(f"更新播放失败: {play_error}")
                return False
                
        except Exception as e:
            print(f"更新OGG播放失败: {e}")
            return False
    
    async def append_ogg_streaming_data(self, audio_chunk: bytes):
        """追加OGG流式数据 - 修复文件写入问题"""
        try:
            if not self.current_audio_file:
                print("❌ 没有活动的OGG流式文件")
                return
            
            # 检查文件是否被占用，如果被占用就跳过写入
            try:
                with open(self.current_audio_file, 'ab') as f:
                    f.write(audio_chunk)
                
                file_size = os.path.getsize(self.current_audio_file)
                print(f"📝 OGG数据追加: +{len(audio_chunk)}字节, 总计: {file_size}字节")
            except PermissionError:
                print(f"⚠️ 文件被占用，跳过数据追加: {len(audio_chunk)}字节")
                # 文件被占用时，仍然添加到内存缓冲区
                self.audio_buffer.extend(audio_chunk)
            
        except Exception as e:
            print(f"OGG数据追加失败: {e}")
            # 确保数据至少保存在内存中
            self.audio_buffer.extend(audio_chunk)
    
    async def process_pcm_chunk_streaming(self, audio_chunk: bytes):
        """处理PCM块流式播放"""
        try:
            print(f"🎧 处理PCM块: {len(audio_chunk)}字节")
            
            # 对于PCM，可以直接使用实时播放器
            if self.use_realtime_streaming and self.realtime_streamer:
                if not self.realtime_streaming_active:
                    self.realtime_streamer.start_streaming()
                    self.realtime_streaming_active = True
                
                # 处理声道转换
                processed_chunk = self._convert_audio_channels(audio_chunk)
                self.realtime_streamer.add_raw_audio_chunk(processed_chunk)
                return True
            
            # 否则使用传统方式
            return False
            
        except Exception as e:
            print(f"PCM流式处理失败: {e}")
            return False
    
    async def finalize_streaming_audio_new(self, audio_data: bytes, audio_format: str, 
                                         chunks_received: int, total_bytes: int):
        """完成新的流式音频处理"""
        try:
            print(f"🎵 完成流式音频: {audio_format}, {chunks_received}块, {total_bytes}字节")
            
            if audio_format.lower() == "ogg":
                await self._finalize_ogg_streaming(audio_data, chunks_received, total_bytes)
            else:
                await self._finalize_pcm_streaming(audio_data, chunks_received, total_bytes)
            
            # 重置状态
            self.current_audio_file = None
            self.audio_buffer = bytearray()
            self.stream_buffer.clear()
            
            print("✅ 流式音频处理完成")
            
        except Exception as e:
            print(f"完成流式音频失败: {e}")
    
    async def _finalize_ogg_streaming(self, audio_data: bytes, chunks_received: int, total_bytes: int):
        """完成OGG流式处理"""
        try:
            if not self.current_audio_file:
                # 创建完整的OGG文件
                timestamp = int(time.time() * 1000)
                temp_dir = tempfile.gettempdir()
                complete_file = os.path.join(temp_dir, f"elysia_complete_ogg_{timestamp}.ogg")
                
                with open(complete_file, 'wb') as f:
                    f.write(audio_data)
                
                self.current_audio_file = complete_file
                self.temp_audio_files.append(complete_file)
                print(f"📁 创建完整OGG文件: {complete_file}")
            else:
                # 确保文件包含所有数据
                with open(self.current_audio_file, 'wb') as f:
                    f.write(audio_data)
                print(f"📁 更新OGG文件: {self.current_audio_file}")
            
            # 最终播放尝试
            file_size = os.path.getsize(self.current_audio_file)
            print(f"📊 最终OGG文件大小: {file_size}字节")
            
            if not self.audio_playing and file_size > 0:
                try:
                    pygame.mixer.music.load(self.current_audio_file)
                    pygame.mixer.music.play()
                    self.audio_playing = True
                    print("🎵 最终OGG播放已开始")
                except Exception as final_play_error:
                    print(f"最终OGG播放失败: {final_play_error}")
                    # 尝试系统播放器
                    if platform.system() == "Windows":
                        try:
                            os.startfile(self.current_audio_file)
                            print("🎵 使用系统播放器播放OGG")
                        except Exception as sys_error:
                            print(f"系统播放器播放失败: {sys_error}")
            
        except Exception as e:
            print(f"OGG流式完成处理失败: {e}")
    
    async def _finalize_pcm_streaming(self, audio_data: bytes, chunks_received: int, total_bytes: int):
        """完成PCM流式处理"""
        try:
            print(f"🎧 完成PCM流式处理: {len(audio_data)}字节")
            
            # 停止实时流播放
            if self.realtime_streaming_active and self.realtime_streamer:
                # 添加剩余数据
                if len(audio_data) > 0:
                    processed_data = self._convert_audio_channels(audio_data)
                    self.realtime_streamer.add_raw_audio_chunk(processed_data)
                
                # 获取统计信息
                stats = self.realtime_streamer.get_stats()
                print(f"📊 实时播放统计: 接收{stats.get('total_received', 0)//1024}KB, 播放{stats.get('total_played', 0)//1024}KB")
                
                # 延迟停止，让音频播放完成
                def delayed_stop():
                    try:
                        if self.realtime_streamer:
                            self.realtime_streamer.stop_streaming()
                        self.realtime_streaming_active = False
                        print("实时PCM播放已停止")
                    except Exception as e:
                        print(f"停止实时播放失败: {e}")
                
                # 3秒后停止
                import threading
                timer = threading.Timer(3.0, delayed_stop)
                timer.start()
            
        except Exception as e:
            print(f"PCM流式完成处理失败: {e}")
    
    def init_streaming_audio(self, audio_format: str = "ogg", on_status_update=None):
        """初始化流式音频播放 - 增强版"""
        try:
            print(f"初始化流式音频播放，格式: {audio_format}")
            
            # 记录当前音频格式
            self.current_audio_format = audio_format.lower()
            
            # 清空音频缓冲区和重置状态
            self.audio_buffer = bytearray()
            self.audio_playing = False
            self.realtime_streaming_active = False
            
            # 清空流式缓冲区
            self.stream_buffer.clear()
            
            # 如果启用实时流播放
            if self.use_realtime_streaming and self.realtime_streamer:
                # 设置状态回调
                if on_status_update:
                    self.realtime_streamer.set_status_callback(on_status_update)
                
                # 开始实时流播放
                self.realtime_streamer.start_streaming()
                self.realtime_streaming_active = True
                
                print("🎵 实时流式音频播放已启动（使用缓冲区管理）")
                if on_status_update:
                    on_status_update("🎵 实时音频流已启动")
                
                return
            
            # 传统方式：创建临时文件用于流式写入
            timestamp = int(time.time() * 1000)
            temp_dir = tempfile.gettempdir()
            
            # 根据格式选择文件扩展名
            file_extension = ".ogg" if audio_format.lower() == "ogg" else ".wav" if audio_format.lower() == "wav" else ".ogg"
            
            self.current_audio_file = os.path.join(temp_dir, f"elysia_stream_{timestamp}{file_extension}")
            print(f"创建流式音频文件: {self.current_audio_file}")
            
            # 添加到临时文件列表
            self.temp_audio_files.append(self.current_audio_file)
            
        except Exception as e:
            error_msg = f"初始化流式音频失败: {e}"
            print(error_msg)
            if on_status_update:
                on_status_update(error_msg)
    
    def handle_streaming_audio_message(self, message_data: dict, on_status_update=None):
        """处理服务端发送的流式音频消息"""
        try:
            message_type = message_data.get("type")
            
            if message_type == "audio_start":
                # 开始音频流
                audio_format = message_data.get("audio_format", "ogg")
                print(f"🎵 开始接收TTS音频流，格式: {audio_format}")
                self.init_streaming_audio(audio_format, on_status_update)
                
                if on_status_update:
                    on_status_update("🎵 开始接收语音...")
                    
            elif message_type == "audio_chunk":
                # 处理音频块
                audio_data_base64 = message_data.get("audio_data")
                chunk_size = message_data.get("chunk_size", 0)
                
                if audio_data_base64:
                    self._handle_audio_chunk_optimized(audio_data_base64, chunk_size, on_status_update)
                    
            elif message_type == "audio_end":
                # 结束音频流
                print("🎵 TTS音频流结束")
                self.finalize_streaming_audio(on_status_update)
                
                if on_status_update:
                    on_status_update("🎵 语音播放完成")
                    
        except Exception as e:
            error_msg = f"处理流式音频消息失败: {e}"
            print(error_msg)
            if on_status_update:
                on_status_update(error_msg)
    
    def _handle_audio_chunk_optimized(self, audio_data_base64: str, chunk_size: int, on_status_update=None):
        """处理音频块 - 使用流式缓冲区并处理声道转换"""
        try:
            # 解码音频数据
            audio_chunk = base64.b64decode(audio_data_base64)
            
            if len(audio_chunk) != chunk_size:
                print(f"⚠️ 音频块大小不匹配: 期望{chunk_size}, 实际{len(audio_chunk)}")
            
            print(f"📥 接收音频块: {len(audio_chunk)} 字节")
            
            # 添加到流式缓冲区（声道转换将在播放时进行）
            if self.stream_buffer.append_chunk(audio_chunk):
                # 添加到总缓冲区（用于最终文件生成）
                self.audio_buffer.extend(audio_chunk)
                
                # 检查是否可以开始实时播放
                if self.stream_buffer.is_ready and self._try_realtime_playback_from_buffer(on_status_update):
                    return
                
                # 传统流式播放处理
                self._handle_traditional_streaming(audio_chunk, on_status_update)
            else:
                print("⚠️ 缓冲区已满，跳过音频块")
            
        except Exception as e:
            error_msg = f"音频块处理失败: {e}"
            print(error_msg)
            if on_status_update:
                on_status_update(error_msg)
    
    def _convert_audio_channels(self, audio_data: bytes) -> bytes:
        """转换音频声道以匹配pygame设置"""
        try:
            # 获取pygame实际设置
            pygame_settings = pygame.mixer.get_init()
            if not pygame_settings:
                return audio_data
            
            actual_freq, actual_size, actual_channels = pygame_settings
            config_channels = Config.PYGAME_AUDIO_CONFIG['channels']
            
            # 如果声道数匹配，直接返回
            if actual_channels == config_channels:
                return audio_data
            
            # 如果pygame使用双声道，但服务端发送单声道
            if actual_channels == 2 and config_channels == 1:
                return self._mono_to_stereo(audio_data)
            
            # 如果pygame使用单声道，但服务端发送双声道  
            elif actual_channels == 1 and config_channels == 2:
                return self._stereo_to_mono(audio_data)
            
            return audio_data
            
        except Exception as e:
            print(f"声道转换失败: {e}")
            return audio_data
    
    def _mono_to_stereo(self, mono_data: bytes) -> bytes:
        """单声道转双声道"""
        try:
            # 确保数据长度是偶数（16位样本）
            if len(mono_data) % 2 != 0:
                mono_data = mono_data[:-1]
            
            # 转换为numpy数组
            import numpy as np
            mono_samples = np.frombuffer(mono_data, dtype=np.int16)
            
            # 创建立体声数据（左右声道相同）
            stereo_samples = np.zeros((len(mono_samples), 2), dtype=np.int16)
            stereo_samples[:, 0] = mono_samples  # 左声道
            stereo_samples[:, 1] = mono_samples  # 右声道
            
            # 转换回字节
            stereo_data = stereo_samples.tobytes()
            
            print(f"🔄 单声道转双声道: {len(mono_data)} -> {len(stereo_data)} 字节")
            return stereo_data
            
        except Exception as e:
            print(f"单声道转双声道失败: {e}")
            return mono_data
    
    def _stereo_to_mono(self, stereo_data: bytes) -> bytes:
        """双声道转单声道"""
        try:
            # 确保数据长度是4的倍数（双声道16位样本）
            if len(stereo_data) % 4 != 0:
                stereo_data = stereo_data[:-(len(stereo_data) % 4)]
            
            # 转换为numpy数组
            import numpy as np
            stereo_samples = np.frombuffer(stereo_data, dtype=np.int16)
            
            # 重新组织为双声道格式
            stereo_samples = stereo_samples.reshape(-1, 2)
            
            # 混合左右声道
            mono_samples = np.mean(stereo_samples, axis=1).astype(np.int16)
            
            # 转换回字节
            mono_data = mono_samples.tobytes()
            
            print(f"🔄 双声道转单声道: {len(stereo_data)} -> {len(mono_data)} 字节")
            return mono_data
            
        except Exception as e:
            print(f"双声道转单声道失败: {e}")
            return stereo_data
    
    def _try_realtime_playback_from_buffer(self, on_status_update):
        """从缓冲区尝试实时播放 - 使用配置化参数"""
        if not (self.use_realtime_streaming and self.realtime_streaming_active and self.realtime_streamer):
            return False
        
        # 对于OGG格式，跳过逐块实时播放，等待完整数据
        if self.current_audio_format == "ogg":
            print("🔄 OGG格式：跳过逐块播放，等待完整数据处理")
            return False
        
        try:
            # 从配置获取参数
            config = Config.STREAM_BUFFER_CONFIG
            max_chunks_per_cycle = config['max_chunks_per_cycle']
            status_interval = config['status_update_interval']
            
            # 从缓冲区获取音频块进行播放
            chunk_count = 0
            
            while chunk_count < max_chunks_per_cycle:
                audio_chunk = self.stream_buffer.get_chunk()
                if not audio_chunk:
                    break
                
                processed_chunk = self._process_audio_chunk_for_realtime(audio_chunk)
                if processed_chunk:
                    self.realtime_streamer.add_raw_audio_chunk(processed_chunk)
                    chunk_count += 1
            
            if chunk_count > 0:
                # 显示缓冲区状态（按配置的间隔）
                stats = self.stream_buffer.get_stats()
                if on_status_update and stats["total_received"] % status_interval == 0:
                    on_status_update(f"🎧 实时播放中... 缓冲区: {stats['utilization']:.1f}% ({stats['chunks']} 块)")
                
                return True
                
        except Exception as e:
            print(f"缓冲区实时播放失败: {e}")
            self._fallback_to_traditional_playback()
        
        return False
    
    def _try_realtime_playback(self, audio_chunk, on_status_update):
        """尝试实时播放 - 改进版本"""
        if not (self.use_realtime_streaming and self.realtime_streaming_active and self.realtime_streamer):
            return False
        
        try:
            # 使用更高效的音频块处理
            processed_chunk = self._process_audio_chunk_for_realtime(audio_chunk)
            
            if processed_chunk:
                self.realtime_streamer.add_raw_audio_chunk(processed_chunk)
                
                # 减少状态更新频率，提高性能
                if len(self.audio_buffer) % 8192 == 0:  # 每8KB更新一次
                    if on_status_update:
                        on_status_update("🎧 实时播放中...")
                
                return True
                
        except Exception as e:
            print(f"实时播放失败: {e}")
            # 失败时优雅降级到传统播放
            self._fallback_to_traditional_playback()
        
        return False
    
    def _process_audio_chunk_for_realtime(self, audio_chunk):
        """处理音频块用于实时播放"""
        try:
            # 对于OGG格式，不应该逐块处理，因为OGG头部信息只在第一个块
            if self.current_audio_format == "ogg":
                # OGG格式需要完整解码，不适合逐块处理
                # 直接返回None，让系统积累完整数据后统一处理
                print(f"🔄 OGG格式块暂存: {len(audio_chunk)} 字节 (等待完整数据)")
                return None
            
            # 只对PCM格式进行逐块处理
            # PCM格式直接使用，但需要声道转换
            elif len(audio_chunk) % 2 == 0 and len(audio_chunk) > 100:
                return self._convert_audio_channels(audio_chunk)
            
            return None
            
        except Exception as e:
            print(f"音频块处理失败: {e}")
            return None
    
    def _fallback_to_traditional_playback(self):
        """降级到传统播放模式"""
        try:
            self.realtime_streaming_active = False
            if self.realtime_streamer:
                self.realtime_streamer.stop_streaming()
            print("⚠️ 已切换到传统播放模式")
        except Exception as e:
            print(f"降级失败: {e}")
    
    def _handle_traditional_streaming(self, audio_chunk, on_status_update):
        """处理传统流式播放"""
        if not self.current_audio_file:
            print("❌ 没有活动的音频文件")
            return
        
        try:
            # 写入音频数据到文件
            with open(self.current_audio_file, 'ab') as f:
                f.write(audio_chunk)
            
            total_size = os.path.getsize(self.current_audio_file)
            print(f"📝 写入传统流式文件: +{len(audio_chunk)} 字节, 总计: {total_size} 字节")
            
            if on_status_update:
                on_status_update(f"接收音频: {total_size} 字节")
            
            # 尝试开始播放
            if not self.audio_playing:
                self._try_start_traditional_playback(on_status_update)
            
        except Exception as e:
            print(f"传统流式处理失败: {e}")
    
    def _try_start_traditional_playback(self, on_status_update):
        """尝试开始传统播放"""
        try:
            if not self.current_audio_file or not os.path.exists(self.current_audio_file):
                return
            
            file_size = os.path.getsize(self.current_audio_file)
            
            # 当有足够数据时开始播放
            if file_size >= 8192:  # 8KB阈值
                print(f"🎵 开始传统流式播放: {file_size} 字节")
                
                try:
                    # 尝试pygame播放
                    if pygame.mixer.get_init():
                        pygame.mixer.music.load(self.current_audio_file)
                        pygame.mixer.music.play()
                        self.audio_playing = True
                        
                        if on_status_update:
                            on_status_update("🎵 开始播放...")
                        
                        print("✅ pygame播放已开始")
                        return
                        
                except Exception as e:
                    print(f"pygame播放失败: {e}")
                
                # 播放失败，继续等待更多数据
                
        except Exception as e:
            print(f"传统播放启动失败: {e}")
    
    def try_start_streaming_playback(self, on_status_update=None):
        """尝试开始流式播放"""
        try:
            if not self.current_audio_file or self.audio_playing:
                return
            
            # 检查文件是否存在且有内容
            if not os.path.exists(self.current_audio_file):
                return
            
            file_size = os.path.getsize(self.current_audio_file)
            if file_size < 4096:  # 至少4KB才尝试播放
                return
            
            print(f"尝试开始流式播放，当前文件大小: {file_size} 字节")
            
            # 尝试使用pygame播放
            try:
                pygame.mixer.music.load(self.current_audio_file)
                pygame.mixer.music.play()
                self.audio_playing = True
                if on_status_update:
                    on_status_update("🎵 开始流式播放...")
                print("流式播放已开始")
            except Exception as e:
                print(f"pygame流式播放失败: {e}")
                # 如果pygame失败，我们继续等待更多数据
                
        except Exception as e:
            print(f"尝试流式播放异常: {e}")
    
    def finalize_streaming_audio(self, on_status_update=None, on_cleanup_schedule=None):
        """完成流式音频播放"""
        try:
            print(f"完成流式音频接收，总大小: {len(self.audio_buffer)} 字节")
            
            # 如果使用实时流播放
            if self.realtime_streaming_active:
                # 处理剩余的音频数据
                if len(self.audio_buffer) > 0:
                    try:
                        # 根据音频格式处理
                        if self.current_audio_format == "ogg" and REALTIME_AUDIO_AVAILABLE and _AudioFormatConverter:
                            # 获取pygame实际设置以确定输出声道
                            import pygame
                            pygame_settings = pygame.mixer.get_init()
                            target_channels = pygame_settings[2] if pygame_settings else 2
                            
                            # ⚠️ 重要：服务端使用32000Hz，必须匹配解码采样率
                            # 使用pygame的采样率确保匹配服务端
                            target_sample_rate = pygame_settings[0] if pygame_settings else 32000
                            
                            # OGG格式：使用正确的采样率解码，匹配服务端32000Hz
                            pcm_data = _AudioFormatConverter.ogg_to_pcm(
                                bytes(self.audio_buffer),
                                target_sample_rate=target_sample_rate,  # 匹配服务端32000Hz
                                target_channels=target_channels
                            )
                            print(f"🎵 OGG完整解码: {len(self.audio_buffer)} -> {len(pcm_data)} 字节 ({target_sample_rate}Hz {target_channels}声道)")
                            
                            # ✅ 采样率匹配服务端，确保正确语速
                        else:
                            # PCM格式：直接使用，进行声道转换
                            pcm_data = self._convert_audio_channels(bytes(self.audio_buffer))
                            print(f"🎵 PCM格式处理: {len(self.audio_buffer)} -> {len(pcm_data)} 字节")
                        
                        # 添加到实时播放器
                        if self.realtime_streamer and pcm_data:
                            self.realtime_streamer.add_raw_audio_chunk(pcm_data)
                            print(f"实时播放: 处理剩余 {len(pcm_data)} 字节PCM数据")
                        
                    except Exception as final_convert_error:
                        print(f"最终转换失败: {final_convert_error}")
                
                # 显示统计信息
                if self.realtime_streamer:
                    stats = self.realtime_streamer.get_stats()
                    if on_status_update:
                        on_status_update(f"🎵 实时播放统计 - 接收: {stats['total_received']//1024}KB, 播放: {stats['total_played']//1024}KB")
                
                # 设置延迟停止（让音频播放完成）
                if on_cleanup_schedule:
                    on_cleanup_schedule(5000, self._stop_realtime_streaming)  # 5秒后停止
                
                # 重置状态
                self.realtime_streaming_active = False
                self.audio_buffer = bytearray()
                
                if on_status_update:
                    on_status_update("🎵 实时流式音频处理完成")
                return
            
            # 传统方式处理
            if not self.audio_playing or len(self.audio_buffer) > 0:
                complete_audio_file = self._create_complete_audio_file(on_status_update)
                
                if complete_audio_file and on_cleanup_schedule:
                    on_cleanup_schedule(
                        Config.TEMP_FILE_CLEANUP_DELAY,
                        lambda: self._cleanup_audio_file(complete_audio_file)
                    )
            
            # 清理流式音频文件
            if self.current_audio_file and on_cleanup_schedule:
                current_file = self.current_audio_file
                on_cleanup_schedule(
                    Config.STREAMING_FILE_CLEANUP_DELAY,
                    lambda: self._cleanup_audio_file(current_file)
                )
            
            # 重置状态
            self.current_audio_file = None
            self.audio_buffer = bytearray()
            self.audio_playing = False
            
        except Exception as e:
            error_msg = f"完成流式音频失败: {e}"
            print(error_msg)
            if on_status_update:
                on_status_update(error_msg)
    
    def _create_complete_audio_file(self, on_status_update=None) -> Optional[str]:
        """创建完整的音频文件"""
        try:
            timestamp = int(time.time() * 1000)
            temp_dir = tempfile.gettempdir()
            complete_audio_file = os.path.join(temp_dir, f"elysia_complete_{timestamp}.ogg")
            
            # 将完整的缓冲区写入新文件
            with open(complete_audio_file, 'wb') as f:
                f.write(self.audio_buffer)
            
            print(f"创建完整音频文件: {complete_audio_file}")
            file_size = os.path.getsize(complete_audio_file)
            print(f"完整音频文件大小: {file_size} 字节")
            
            if file_size > 0:
                # 停止当前播放（如果有的话）
                try:
                    pygame.mixer.music.stop()
                except:
                    pass
                
                # 播放完整版本
                success = self._play_complete_audio(complete_audio_file, on_status_update)
                
                if success:
                    self.temp_audio_files.append(complete_audio_file)
                    return complete_audio_file
                else:
                    if on_status_update:
                        on_status_update(f"🎵 自动播放失败，请手动播放: {complete_audio_file}")
                    return complete_audio_file
            else:
                if on_status_update:
                    on_status_update("❌ 完整音频文件为空")
                return None
                
        except Exception as create_error:
            error_msg = f"创建完整音频文件失败: {create_error}"
            print(error_msg)
            if on_status_update:
                on_status_update(error_msg)
            return None
    
    def _play_complete_audio(self, audio_file: str, on_status_update=None) -> bool:
        """播放完整音频文件"""
        # 方法1: pygame播放
        try:
            print(f"尝试pygame播放: {audio_file}")
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            return True
        except Exception as e:
            print(f"pygame播放失败: {e}")
        
        # 方法2: 系统播放器（仅Windows）
        try:
            if platform.system() == "Windows":
                print(f"尝试系统播放器播放: {audio_file}")
                os.startfile(audio_file)
                return True
        except Exception as e:
            print(f"系统播放器播放失败: {e}")
        
        return False
    
    def _cleanup_audio_file(self, file_path: str):
        """清理音频文件"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                print(f"清理音频文件: {file_path}")
                if file_path in self.temp_audio_files:
                    self.temp_audio_files.remove(file_path)
        except Exception as e:
            print(f"清理音频文件失败 {file_path}: {e}")
    
    def cleanup_all_temp_files(self):
        """清理所有临时音频文件"""
        try:
            for temp_file in self.temp_audio_files[:]:  # 使用切片复制避免迭代时修改
                self._cleanup_audio_file(temp_file)
        except Exception as e:
            print(f"清理临时文件总体失败: {e}")
    
    def stop_all_audio(self):
        """停止所有音频播放"""
        try:
            pygame.mixer.music.stop()
        except Exception as e:
            print(f"停止音频播放失败: {e}")
        
        # 停止实时流播放
        self._stop_realtime_streaming()
        
        # 清空缓冲区
        self.stream_buffer.clear()
    
    def _stop_realtime_streaming(self):
        """停止实时流播放"""
        try:
            if self.realtime_streaming_active and self.realtime_streamer:
                self.realtime_streamer.stop_streaming()
                self.realtime_streaming_active = False
                print("实时流播放已停止")
            
            # 清空流式缓冲区
            self.stream_buffer.clear()
            
        except Exception as e:
            print(f"停止实时流播放失败: {e}")
    
    def toggle_realtime_streaming(self, enable: bool):
        """切换实时流播放模式"""
        if REALTIME_AUDIO_AVAILABLE:
            self.use_realtime_streaming = enable
            print(f"实时流播放模式: {'启用' if enable else '禁用'}")
        else:
            self.use_realtime_streaming = False
            print("实时流播放不可用，使用传统音频播放")
    
    def get_realtime_stats(self) -> dict:
        """获取实时播放统计信息"""
        stats = {"playing": False, "buffer_stats": None}
        
        if self.realtime_streaming_active and self.realtime_streamer:
            stats.update(self.realtime_streamer.get_stats())
        
        # 添加缓冲区统计信息
        stats["buffer_stats"] = self.stream_buffer.get_stats()
        
        return stats
    
    def get_stream_buffer_info(self) -> dict:
        """获取流式缓冲区详细信息"""
        return {
            "buffer_stats": self.stream_buffer.get_stats(),
            "total_received": len(self.audio_buffer),
            "realtime_active": self.realtime_streaming_active,
            "traditional_active": self.audio_playing
        }
    
    async def play_complete_ogg_audio(self, audio_data: bytes):
        """播放完整的OGG音频数据 - 用于audio_end时的最终播放"""
        print(f"🎵 开始播放完整OGG音频: {len(audio_data)}字节")
        
        try:
            # 停止之前的播放
            self.stop_all_audio()
            
            # 创建唯一的临时文件名
            timestamp = int(time.time() * 1000000)
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"complete_ogg_{timestamp}.ogg")
            
            # 写入完整音频数据
            with open(temp_file, 'wb') as f:
                f.write(audio_data)
            
            print(f"📁 完整OGG文件已保存: {temp_file}")
            
            # 直接使用pygame播放OGG文件
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            self.audio_playing = True
            
            print(f"▶️ 完整OGG音频播放已启动")
            
            # 等待播放完成（可选）
            import asyncio
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            print(f"✅ 完整OGG音频播放完成")
            
        except Exception as e:
            print(f"❌ 完整OGG音频播放失败: {e}")
        finally:
            self.audio_playing = False
            # 延迟清理临时文件，等待文件释放
            if 'temp_file' in locals() and os.path.exists(temp_file):
                asyncio.create_task(self._delayed_cleanup(temp_file))
    
    async def _delayed_cleanup(self, temp_file: str):
        """延迟清理临时文件"""
        try:
            # 等待一段时间让文件完全释放
            await asyncio.sleep(1.0)
            
            # 尝试删除文件，最多重试3次
            for attempt in range(3):
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        print(f"🗑️ 临时文件已清理: {temp_file}")
                        break
                except (PermissionError, OSError) as e:
                    if attempt < 2:  # 如果不是最后一次尝试
                        await asyncio.sleep(2.0)  # 等待更长时间
                    else:
                        print(f"⚠️ 临时文件清理最终失败: {e}")
                        # 记录文件路径，稍后手动清理
                        print(f"📝 需要手动清理的文件: {temp_file}")
        except Exception as e:
            print(f"❌ 延迟清理异常: {e}")
