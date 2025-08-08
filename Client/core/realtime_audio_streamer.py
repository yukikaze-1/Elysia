"""
实时音频流播放器
支持真正的流式音频播放，边接收边播放
"""

import sounddevice as sd
import numpy as np
import threading
import queue
import base64
import io
import wave
import time
import tempfile
import os
from typing import Optional, Callable
from .config import Config


class RealTimeAudioStreamer:
    """实时音频流播放器"""
    
    def __init__(self):
        self.audio_queue = queue.Queue(maxsize=100)  # 音频数据队列
        self.playing = False
        self.stream = None
        self.play_thread = None
        
        # 音频参数
        self.sample_rate = Config.REALTIME_AUDIO_CONFIG['sample_rate']
        self.channels = Config.REALTIME_AUDIO_CONFIG['channels']
        self.chunk_size = Config.REALTIME_AUDIO_CONFIG['chunk_size']
        self.dtype = np.int16
        
        # 缓冲区管理
        self.buffer = bytearray()
        self.min_buffer_size = Config.REALTIME_AUDIO_CONFIG['min_buffer_size']
        self.max_buffer_size = Config.REALTIME_AUDIO_CONFIG['max_buffer_size']
        
        # 状态回调
        self.status_callback: Optional[Callable] = None
        
        # 统计信息
        self.total_received = 0
        self.total_played = 0
        self.start_time = None
        
        print(f"初始化实时音频流播放器: {self.sample_rate}Hz, {self.channels}声道, 块大小{self.chunk_size}")
    
    def set_status_callback(self, callback: Callable):
        """设置状态回调函数"""
        self.status_callback = callback
    
    def _update_status(self, message: str):
        """更新状态"""
        if self.status_callback:
            self.status_callback(message)
        print(f"[实时音频] {message}")
    
    def start_streaming(self):
        """开始流式播放"""
        if self.playing:
            return
        
        try:
            self.playing = True
            self.start_time = time.time()
            self.total_received = 0
            self.total_played = 0
            self.buffer = bytearray()
            
            # 初始化音频流
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.chunk_size,
                callback=self._audio_callback,
                latency='low'  # 低延迟模式
            )
            
            self.stream.start()
            self._update_status("🎵 实时音频流开始播放")
            
            print(f"实时音频流启动成功: {self.sample_rate}Hz, {self.channels}声道")
            
        except Exception as e:
            self.playing = False
            error_msg = f"启动实时音频流失败: {e}"
            print(error_msg)
            self._update_status(f"❌ {error_msg}")
    
    def _audio_callback(self, outdata, frames, time_info, status):
        """音频播放回调函数"""
        if status:
            print(f"音频回调状态: {status}")
        
        try:
            # 初始化输出为静音
            outdata.fill(0)
            
            # 累积所需的音频数据
            bytes_needed = frames * self.channels * 2  # 2 bytes per sample (int16)
            accumulated_data = bytearray()
            
            # 从队列中获取足够的数据
            while len(accumulated_data) < bytes_needed and not self.audio_queue.empty():
                try:
                    chunk = self.audio_queue.get_nowait()
                    accumulated_data.extend(chunk)
                except queue.Empty:
                    break
            
            if len(accumulated_data) > 0:
                # 确保数据长度不超过需要的长度
                if len(accumulated_data) > bytes_needed:
                    # 如果数据过多，将多余部分放回队列
                    excess_data = accumulated_data[bytes_needed:]
                    accumulated_data = accumulated_data[:bytes_needed]
                    
                    # 将多余数据放回队列前端
                    try:
                        temp_queue = queue.Queue(maxsize=self.audio_queue.maxsize)
                        temp_queue.put(bytes(excess_data))
                        
                        # 将原队列中的数据也加入
                        while not self.audio_queue.empty():
                            try:
                                temp_queue.put(self.audio_queue.get_nowait())
                            except (queue.Empty, queue.Full):
                                break
                        
                        self.audio_queue = temp_queue
                    except Exception as queue_error:
                        print(f"队列重组失败: {queue_error}")
                
                # 处理数据长度不足的情况
                if len(accumulated_data) < bytes_needed:
                    # 用零填充
                    padding_needed = bytes_needed - len(accumulated_data)
                    accumulated_data.extend(bytes(padding_needed))
                
                try:
                    # 转换为numpy数组
                    audio_array = np.frombuffer(accumulated_data, dtype=self.dtype)
                    
                    # 处理声道配置
                    if self.channels == 1:
                        # 单声道
                        audio_array = audio_array.reshape(-1, 1)
                    elif self.channels == 2:
                        # 立体声 - 确保样本数是偶数
                        if len(audio_array) % 2 != 0:
                            audio_array = audio_array[:-1]  # 移除最后一个样本使其为偶数
                        audio_array = audio_array.reshape(-1, 2)
                    
                    # 确保输出帧数正确
                    output_frames = min(frames, audio_array.shape[0])
                    outdata[:output_frames] = audio_array[:output_frames]
                    
                    # 更新统计
                    self.total_played += output_frames * self.channels * 2
                    
                except Exception as array_error:
                    print(f"音频数组处理错误: {array_error}")
                    outdata.fill(0)
            
        except Exception as e:
            print(f"音频回调错误: {e}")
            outdata.fill(0)
    
    def add_raw_audio_chunk(self, audio_chunk: bytes):
        """添加原始音频数据块"""
        if not self.playing:
            return
        
        try:
            self.total_received += len(audio_chunk)
            
            # 验证音频数据大小（应该是采样大小的倍数）
            sample_size = self.channels * 2  # int16 = 2 bytes
            if len(audio_chunk) % sample_size != 0:
                # 截断到最近的采样边界
                aligned_size = (len(audio_chunk) // sample_size) * sample_size
                if aligned_size > 0:
                    audio_chunk = audio_chunk[:aligned_size]
                    print(f"音频数据对齐: {len(audio_chunk)} -> {aligned_size}")
                else:
                    print(f"音频块太小，跳过: {len(audio_chunk)} 字节")
                    return
            
            # 检查队列是否有空间
            max_queue_items = 50  # 限制队列大小防止延迟累积
            
            # 如果队列接近满，清除一些旧数据
            if self.audio_queue.qsize() >= max_queue_items:
                cleared_count = 0
                while self.audio_queue.qsize() > max_queue_items // 2 and not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                        cleared_count += 1
                    except queue.Empty:
                        break
                if cleared_count > 0:
                    print(f"清理队列: 移除 {cleared_count} 个旧音频块")
            
            # 将数据加入队列
            try:
                self.audio_queue.put_nowait(audio_chunk)
            except queue.Full:
                # 队列满了，尝试清除最旧的数据
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(audio_chunk)
                except queue.Empty:
                    pass
            
            # 更新状态（降低频率）
            queue_size = self.audio_queue.qsize()
            if self.total_received % (8192 * 5) == 0:  # 每40KB更新一次状态
                self._update_status(f"🎵 实时播放中... 队列: {queue_size}, 接收: {self.total_received//1024}KB, 播放: {self.total_played//1024}KB")
        
        except Exception as e:
            print(f"添加音频块失败: {e}")
    
    def add_base64_audio_chunk(self, audio_data_base64: str):
        """添加base64编码的音频数据块"""
        try:
            audio_chunk = base64.b64decode(audio_data_base64)
            self.add_raw_audio_chunk(audio_chunk)
        except Exception as e:
            print(f"解码base64音频数据失败: {e}")
    
    def add_pcm_audio_chunk(self, pcm_data: bytes, convert_from_format: Optional[str] = None):
        """添加PCM音频数据块"""
        try:
            if convert_from_format == "ogg_to_pcm":
                # 如果是从OGG转换来的，可能需要特殊处理
                # 这里简化处理，直接使用原始数据
                self.add_raw_audio_chunk(pcm_data)
            else:
                # 直接添加PCM数据
                self.add_raw_audio_chunk(pcm_data)
        except Exception as e:
            print(f"添加PCM音频数据失败: {e}")
    
    def stop_streaming(self):
        """停止流式播放"""
        if not self.playing:
            return
        
        try:
            self.playing = False
            
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            # 清空队列
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except:
                    break
            
            # 显示统计信息
            if self.start_time:
                duration = time.time() - self.start_time
                self._update_status(f"🎵 实时播放结束 - 时长: {duration:.1f}s, 接收: {self.total_received//1024}KB, 播放: {self.total_played//1024}KB")
            
            print("实时音频流播放结束")
            
        except Exception as e:
            error_msg = f"停止实时音频流失败: {e}"
            print(error_msg)
            self._update_status(f"❌ {error_msg}")
    
    def is_playing(self) -> bool:
        """检查是否正在播放"""
        return self.playing
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self.audio_queue.qsize()
    
    def get_stats(self) -> dict:
        """获取播放统计信息"""
        return {
            "playing": self.playing,
            "queue_size": self.audio_queue.qsize(),
            "total_received": self.total_received,
            "total_played": self.total_played,
            "duration": time.time() - self.start_time if self.start_time else 0
        }


class AudioFormatConverter:
    """音频格式转换器"""
    
    @staticmethod
    def ogg_to_pcm(ogg_data: bytes, target_sample_rate: int = 22050, target_channels: int = 1) -> bytes:
        """将OGG数据转换为PCM（改进版本）"""
        try:
            # 检查OGG数据是否完整
            if len(ogg_data) < 10:  # 至少需要一些基本数据
                print(f"OGG数据太小: {len(ogg_data)} 字节")
                # 返回短暂静音数据
                silence_samples = target_sample_rate // 20  # 0.05秒的静音
                return np.zeros(silence_samples, dtype=np.int16).tobytes()
            
            # 检查是否包含OGG魔数 - 更宽松的检测
            has_ogg_signature = False
            if ogg_data.startswith(b'OggS'):
                has_ogg_signature = True
                print(f"检测到OGG头部: {len(ogg_data)} 字节")
            elif b'OggS' in ogg_data:
                has_ogg_signature = True
                print(f"检测到OGG标识在数据中: {len(ogg_data)} 字节")
            
            if has_ogg_signature:
                # 尝试使用pygame处理OGG数据
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(suffix='.ogg', delete=False)
                try:
                    temp_file.write(ogg_data)
                    temp_file.close()
                    
                    # 使用pygame加载
                    import pygame
                    try:
                        # 确保pygame mixer已初始化
                        if not pygame.mixer.get_init():
                            pygame.mixer.pre_init(frequency=target_sample_rate, size=-16, channels=target_channels, buffer=512)
                            pygame.mixer.init()
                        
                        sound = pygame.mixer.Sound(temp_file.name)
                        raw_data = pygame.sndarray.array(sound)
                        
                        # 处理声道转换
                        if raw_data.ndim > 1 and target_channels == 1:
                            # 转为单声道（取平均值）
                            raw_data = np.mean(raw_data, axis=1)
                        elif raw_data.ndim == 1 and target_channels == 2:
                            # 转为立体声（复制单声道）
                            raw_data = np.column_stack([raw_data, raw_data])
                        
                        # 确保数据类型正确
                        if raw_data.dtype != np.int16:
                            # 归一化并转换为int16
                            if raw_data.dtype in [np.float32, np.float64]:
                                # 音频数据通常在[-1, 1]范围内
                                raw_data = np.clip(raw_data, -1.0, 1.0)
                                raw_data = (raw_data * 32767).astype(np.int16)
                            else:
                                raw_data = raw_data.astype(np.int16)
                        
                        print(f"OGG转换成功: {len(raw_data)} 样本, {raw_data.dtype}")
                        return raw_data.tobytes()
                    
                    except Exception as pygame_error:
                        print(f"pygame OGG解码失败: {pygame_error}")
                        # 继续尝试其他方法
                        pass
                
                finally:
                    # 清理临时文件
                    if os.path.exists(temp_file.name):
                        try:
                            os.unlink(temp_file.name)
                        except:
                            pass
            
            # 如果OGG处理失败，尝试作为原始音频数据处理
            print(f"尝试作为原始音频数据处理: {len(ogg_data)} 字节")
            
            # 检查数据是否看起来像音频
            if len(ogg_data) % 2 == 0:  # 16位音频应该是偶数字节
                try:
                    # 尝试作为PCM数据处理
                    pcm_array = np.frombuffer(ogg_data, dtype=np.int16)
                    
                    # 检查数据范围是否合理（避免噪声）
                    if len(pcm_array) > 0:
                        max_val = np.max(np.abs(pcm_array))
                        mean_val = np.mean(np.abs(pcm_array))
                        
                        print(f"音频数据分析: 最大值={max_val}, 平均值={mean_val:.1f}, 样本数={len(pcm_array)}")
                        
                        # 如果数据看起来像随机噪声，降低音量或生成安全的音频
                        if max_val > 32767:
                            # 数据超出范围，归一化
                            pcm_array = (pcm_array.astype(np.float32) / max_val * 16383).astype(np.int16)
                            print(f"音频数据归一化到50%音量")
                        elif mean_val > 8000:  # 平均值过高，可能是噪声
                            # 降低音量到安全水平
                            pcm_array = (pcm_array.astype(np.float32) * 0.2).astype(np.int16)
                            print(f"检测到可能的噪声，降低音量到20%")
                        elif mean_val < 50:  # 平均值过低，可能是静音
                            print(f"检测到低音量或静音数据")
                        
                        return pcm_array.tobytes()
                
                except Exception as pcm_error:
                    print(f"作为PCM处理失败: {pcm_error}")
            
            # 最后的fallback：生成短暂的静音或低音量测试音
            print("所有处理方法都失败，生成安全的回退音频")
            duration_samples = min(target_sample_rate // 4, 4410)  # 最多0.25秒
            
            # 生成低音量的测试音而不是完全静音
            t = np.linspace(0, duration_samples / target_sample_rate, duration_samples, False)
            frequency = 220  # 较低的频率
            test_wave = np.sin(frequency * 2.0 * np.pi * t) * 0.1  # 10%音量
            test_audio = (test_wave * 32767).astype(np.int16)
            
            return test_audio.tobytes()
                        
        except Exception as e:
            print(f"OGG到PCM转换异常: {e}")
            # 最终的安全fallback
            silence_samples = target_sample_rate // 10  # 0.1秒静音
            return np.zeros(silence_samples, dtype=np.int16).tobytes()
    
    @staticmethod
    def resample_pcm(pcm_data: bytes, 
                     from_sample_rate: int, 
                     to_sample_rate: int, 
                     channels: int = 1) -> bytes:
        """重采样PCM数据"""
        try:
            if from_sample_rate == to_sample_rate:
                return pcm_data
            
            # 转换为numpy数组
            audio_array = np.frombuffer(pcm_data, dtype=np.int16)
            
            # 计算重采样比例
            ratio = to_sample_rate / from_sample_rate
            new_length = int(len(audio_array) * ratio)
            
            # 简单的线性插值重采样
            old_indices = np.linspace(0, len(audio_array) - 1, new_length)
            new_audio = np.interp(old_indices, np.arange(len(audio_array)), audio_array)
            
            return new_audio.astype(np.int16).tobytes()
            
        except Exception as e:
            print(f"PCM重采样失败: {e}")
            return pcm_data
