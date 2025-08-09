"""
WAV流式音频播放器
基于 ref.py 的实现，支持真正的边接收边播放
"""

import pyaudio
import threading
import queue
import time
import requests
from typing import Optional, Callable, Dict, Any
from .config import Config


class WavStreamPlayer:
    """WAV流式音频播放器 - 参考 ref.py 实现"""
    
    def __init__(self):
        # PyAudio 配置 - 匹配服务端参数
        self.CHUNK = 2048
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 32000
        
        # PyAudio 对象
        self.p = None
        self.stream = None
        
        # 流式播放状态
        self.is_playing = False
        self.is_streaming = False
        
        # 数据缓冲
        self.audio_data_buffer = b""
        self.header_skipped = False
        
        # 状态回调
        self.status_callback: Optional[Callable] = None
        self.playback_start_callback: Optional[Callable] = None  # 新增：播放开始回调
        
        # 统计信息
        self.total_received = 0
        self.total_played = 0
        self.start_time = None
        self.first_chunk_time = None
        
        print(f"初始化WAV流式播放器: {self.RATE}Hz, {self.CHANNELS}声道, 块大小{self.CHUNK}")
    
    def set_status_callback(self, callback: Callable):
        """设置状态回调函数"""
        self.status_callback = callback
    
    def set_playback_start_callback(self, callback: Callable):
        """设置播放开始回调函数"""
        self.playback_start_callback = callback
    
    def _update_status(self, message: str):
        """更新状态"""
        if self.status_callback:
            self.status_callback(message)
        print(f"[WAV流播放] {message}")
    
    def init_audio_stream(self):
        """初始化音频流"""
        try:
            if self.p is None:
                self.p = pyaudio.PyAudio()
            
            if self.stream is None:
                self.stream = self.p.open(
                    format=self.FORMAT,
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    output=True,
                    frames_per_buffer=self.CHUNK
                )
            
            print("WAV音频流初始化成功")
            return True
            
        except Exception as e:
            print(f"WAV音频流初始化失败: {e}")
            return False
    
    def start_streaming(self):
        """开始流式播放"""
        if self.is_streaming:
            return
        
        try:
            # 初始化音频流
            if not self.init_audio_stream():
                raise Exception("音频流初始化失败")
            
            # 重置状态
            self.is_streaming = True
            self.is_playing = False
            self.audio_data_buffer = b""
            self.header_skipped = False
            self.total_received = 0
            self.total_played = 0
            self.start_time = time.time()
            self.first_chunk_time = None
            
            self._update_status("🎵 WAV流式播放器准备就绪")
            print("WAV流式播放已启动")
            
        except Exception as e:
            self.is_streaming = False
            error_msg = f"启动WAV流式播放失败: {e}"
            print(error_msg)
            self._update_status(f"❌ {error_msg}")
    
    def add_audio_chunk(self, chunk: bytes):
        """添加音频数据块 - 基于 ref.py 的逻辑"""
        if not self.is_streaming:
            return
        
        try:
            self.total_received += len(chunk)
            self.audio_data_buffer += chunk
            
            # 跳过WAV文件头（前44字节）
            if not self.header_skipped and len(self.audio_data_buffer) >= 44:
                self.audio_data_buffer = self.audio_data_buffer[44:]
                self.header_skipped = True
                print("WAV文件头已跳过")
            
            # 开始播放音频数据
            if self.header_skipped and len(self.audio_data_buffer) >= self.CHUNK:
                if not self.is_playing:
                    self.is_playing = True
                    if self.first_chunk_time is None:
                        self.first_chunk_time = time.time()
                        if self.start_time is not None:
                            elapsed = self.first_chunk_time - self.start_time
                            print(f"首个音频块播放，延迟: {elapsed:.2f}秒")
                            self._update_status(f"🎵 开始播放 (延迟: {elapsed:.2f}s)")
                        
                        # 触发播放开始回调
                        if self.playback_start_callback:
                            try:
                                self.playback_start_callback()
                            except Exception as e:
                                print(f"播放开始回调执行失败: {e}")
                
                # 播放可用的完整块
                while len(self.audio_data_buffer) >= self.CHUNK:
                    if self.stream:
                        chunk_to_play = self.audio_data_buffer[:self.CHUNK]
                        self.stream.write(chunk_to_play)
                        self.audio_data_buffer = self.audio_data_buffer[self.CHUNK:]
                        self.total_played += len(chunk_to_play)
                    else:
                        break
                
                # 更新播放状态
                if self.total_received % (8192) == 0:  # 每8KB更新一次
                    self._update_status(f"🎵 播放中... 接收: {self.total_received//1024}KB, 播放: {self.total_played//1024}KB")
        
        except Exception as e:
            print(f"添加音频块失败: {e}")
    
    def finalize_playback(self):
        """完成播放 - 播放剩余数据"""
        if not self.is_streaming:
            return
        
        try:
            # 播放剩余的音频数据
            if self.audio_data_buffer and self.stream:
                self.stream.write(self.audio_data_buffer)
                self.total_played += len(self.audio_data_buffer)
                print(f"播放剩余数据: {len(self.audio_data_buffer)} 字节")
            
            # 显示统计信息
            if self.start_time:
                duration = time.time() - self.start_time
                self._update_status(f"🎵 播放完成 - 时长: {duration:.1f}s, 接收: {self.total_received//1024}KB, 播放: {self.total_played//1024}KB")
            
            print("WAV流式播放完成")
            
        except Exception as e:
            print(f"完成WAV播放失败: {e}")
            self._update_status(f"❌ 播放完成时出错: {e}")
    
    def stop_streaming(self):
        """停止流式播放"""
        if not self.is_streaming:
            return
        
        try:
            self.is_streaming = False
            self.is_playing = False
            
            # 停止和关闭音频流
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            if self.p:
                self.p.terminate()
                self.p = None
            
            # 清空缓冲区
            self.audio_data_buffer = b""
            self.header_skipped = False
            
            print("WAV流式播放已停止")
            
        except Exception as e:
            error_msg = f"停止WAV流式播放失败: {e}"
            print(error_msg)
            self._update_status(f"❌ {error_msg}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取播放统计信息"""
        return {
            "streaming": self.is_streaming,
            "playing": self.is_playing,
            "total_received": self.total_received,
            "total_played": self.total_played,
            "buffer_size": len(self.audio_data_buffer),
            "header_skipped": self.header_skipped,
            "duration": time.time() - self.start_time if self.start_time else 0,
            "first_chunk_delay": self.first_chunk_time - self.start_time if self.first_chunk_time and self.start_time else None
        }


class WavStreamClient:
    """WAV流式客户端 - 完整的请求和播放流程"""
    
    def __init__(self):
        self.player = WavStreamPlayer()
        self.is_active = False
    
    def set_status_callback(self, callback: Callable):
        """设置状态回调函数"""
        self.player.set_status_callback(callback)
    
    def set_playback_start_callback(self, callback: Callable):
        """设置播放开始回调函数"""
        self.player.set_playback_start_callback(callback)
    
    def stream_tts_audio(self, text: str, server_url: str = "http://192.168.1.17:11100/tts/generate"):
        """
        流式TTS音频播放 - 基于 ref.py 的完整实现，增强错误处理
        
        Args:
            text: 要转换为语音的文本
            server_url: TTS服务器URL
        """
        if self.is_active:
            print("已有活动的流式播放，忽略新请求")
            return
        
        try:
            self.is_active = True
            
            # 准备请求
            payload = {"text": text}
            
            # 启动播放器
            self.player.start_streaming()
            
            # 发送流式请求，增强错误处理
            start_time = time.time()
            print(f"发送WAV流式请求到: {server_url}")
            print(f"请求数据: {payload}")
            
            # 设置更合适的超时和连接参数
            session = requests.Session()
            session.headers.update({
                'Content-Type': 'application/json',
                'Connection': 'keep-alive'
            })
            
            # 发送请求，设置适当的超时
            resp = session.post(
                server_url, 
                json=payload, 
                stream=True,
                timeout=(10, 120),  # 增加读取超时到120秒
                headers={
                    'Accept': 'audio/wav, */*',
                    'Connection': 'keep-alive'
                }
            )
            
            print(f"收到响应状态: {resp.status_code}")
            print(f"响应头: {dict(resp.headers)}")
            
            # 检查响应状态
            resp.raise_for_status()
            
            # 检查内容类型
            content_type = resp.headers.get('content-type', '')
            print(f"响应内容类型: {content_type}")
            
            # 检查是否为chunked编码
            transfer_encoding = resp.headers.get('Transfer-Encoding', '')
            if 'chunked' in transfer_encoding.lower():
                print("检测到chunked编码，使用适配处理")
            
            # 处理流式响应，增加错误检测和更好的chunk处理
            total_received = 0
            chunk_count = 0
            last_progress_time = time.time()
            
            try:
                # 使用iter_content处理chunked编码
                for chunk in resp.iter_content(chunk_size=1024, decode_unicode=False):
                    if not chunk:
                        # 空chunk可能是正常的，继续处理
                        continue
                        
                    chunk_count += 1
                    total_received += len(chunk)
                    
                    # 每隔2秒或每隔20个块输出进度
                    current_time = time.time()
                    if (current_time - last_progress_time > 2.0) or (chunk_count % 20 == 0):
                        print(f"已接收 {chunk_count} 块, 总计 {total_received//1024}KB")
                        last_progress_time = current_time
                    
                    # 添加音频块到播放器
                    self.player.add_audio_chunk(chunk)
                    
                    # 检查播放器状态
                    if not self.player.is_streaming:
                        print("播放器已停止，中断数据接收")
                        break
                
                print(f"数据接收完成: {chunk_count} 块, 总计 {total_received//1024}KB")
                
                # 检查是否接收到足够的数据
                if total_received < 1024:
                    print(f"⚠️ 接收到的数据很少: {total_received} 字节")
                
            except requests.exceptions.ChunkedEncodingError as chunk_error:
                print(f"Chunked编码错误: {chunk_error}")
                # 如果已经接收到一些数据，继续尝试播放
                if total_received > 44:  # 至少有WAV头部
                    print(f"尝试播放已接收的 {total_received//1024}KB 数据")
                else:
                    raise chunk_error
            except requests.exceptions.ConnectionError as conn_error:
                print(f"连接错误: {conn_error}")
                if total_received > 44:
                    print(f"连接中断，但已接收 {total_received//1024}KB 数据，尝试播放")
                else:
                    raise conn_error
            except Exception as chunk_error:
                print(f"数据块处理错误: {chunk_error}")
                # 如果已经接收到一些数据，继续尝试播放
                if total_received > 44:
                    print(f"尝试播放已接收的 {total_received//1024}KB 数据")
                else:
                    raise chunk_error
            
            finally:
                # 确保响应连接关闭
                resp.close()
                session.close()
            
            # 完成播放
            print("完成WAV流式播放...")
            self.player.finalize_playback()
            
            # 显示总体统计
            total_time = time.time() - start_time
            stats = self.player.get_stats()
            print(f"流式播放总结 - 总时长: {total_time:.2f}s, 接收: {stats['total_received']//1024}KB")
            
        except requests.exceptions.RequestException as req_error:
            error_msg = f"网络请求错误: {req_error}"
            print(error_msg)
            self.player._update_status(f"❌ {error_msg}")
        except Exception as e:
            error_msg = f"WAV流式播放失败: {e}"
            print(error_msg)
            self.player._update_status(f"❌ 流式播放失败: {e}")
        finally:
            self.is_active = False
            # 延迟停止播放器，让音频播放完成
            threading.Timer(2.0, self.player.stop_streaming).start()
    
    def stream_tts_audio_async(self, text: str, server_url: str = "http://192.168.1.17:11100/tts/generate"):
        """异步方式启动流式TTS音频播放，支持重试机制"""
        thread = threading.Thread(target=self._stream_with_retry, args=(text, server_url))
        thread.daemon = True
        thread.start()
        return thread
    
    def _stream_with_retry(self, text: str, server_url: str, max_retries: int = 2):
        """带重试机制的流式播放"""
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    print(f"重试WAV流式播放 (第{attempt}次)...")
                    time.sleep(1)  # 重试前等待1秒
                
                self.stream_tts_audio(text, server_url)
                return  # 成功则退出
                
            except Exception as e:
                print(f"WAV流式播放尝试 {attempt + 1} 失败: {e}")
                if attempt == max_retries:
                    print(f"WAV流式播放最终失败，已重试 {max_retries} 次")
                    self.player._update_status(f"❌ 流式播放最终失败 (重试{max_retries}次)")
                    break
    
    def stop(self):
        """停止所有播放"""
        self.is_active = False
        self.player.stop_streaming()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.player.get_stats()
        stats["client_active"] = self.is_active
        return stats


class WavStreamAudioManager:
    """WAV流式音频管理器 - 集成到现有系统"""
    
    def __init__(self, audio_manager):
        """
        Args:
            audio_manager: 现有的AudioManager实例
        """
        self.audio_manager = audio_manager
        self.wav_client = WavStreamClient()
        self.enabled = True
    
    def set_status_callback(self, callback: Callable):
        """设置状态回调"""
        self.wav_client.set_status_callback(callback)
    
    def set_playback_start_callback(self, callback: Callable):
        """设置播放开始回调"""
        self.wav_client.set_playback_start_callback(callback)
    
    def enable_wav_streaming(self, enabled: bool = True):
        """启用/禁用WAV流式播放"""
        self.enabled = enabled
        print(f"WAV流式播放: {'启用' if enabled else '禁用'}")
    
    def handle_wav_stream_request(self, text: str, server_url: Optional[str] = None):
        """处理WAV流式请求"""
        if not self.enabled:
            print("WAV流式播放已禁用，使用传统方式")
            return False
        
        try:
            # 使用默认URL如果未提供
            if server_url is None:
                server_url = f"{Config.API_BASE_URL}/tts/generate"
            
            # 启动异步流式播放
            self.wav_client.stream_tts_audio_async(text, server_url)
            return True
            
        except Exception as e:
            print(f"WAV流式请求失败: {e}")
            return False
    
    def stop_all(self):
        """停止所有WAV流式播放"""
        self.wav_client.stop()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.wav_client.get_stats()


# 简单的测试函数
def test_wav_streaming():
    """测试WAV流式播放功能"""
    test_text = "大概率是没有的，我也希望如此，毕竟自己的故事还是应当由自己来诉说。"
    
    client = WavStreamClient()
    client.set_status_callback(lambda msg: print(f"状态: {msg}"))
    
    print("开始WAV流式播放测试...")
    client.stream_tts_audio(test_text)
    print("测试完成")


if __name__ == "__main__":
    test_wav_streaming()
