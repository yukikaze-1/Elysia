"""
音频处理模块 - 简化版
只保留基于 PyAudio 的 WAV 实时流式播放功能
"""

import os
import time
from typing import List, Optional
from .config import Config

# 尝试导入WAV流式播放模块
try:
    from .wav_stream_player import WavStreamAudioManager
    WAV_STREAM_AVAILABLE = True
    print("✅ WAV流式播放模块已加载")
except ImportError as e:
    WAV_STREAM_AVAILABLE = False
    print(f"⚠️ WAV流式播放模块不可用: {e}")
    WavStreamAudioManager = None


class AudioManager:
    """音频管理器 - 简化版，只保留WAV流式播放"""
    
    def __init__(self):
        self.temp_audio_files: List[str] = []
        
        # WAV流式播放器
        self.wav_stream_manager = None
        self.use_wav_streaming = False
        
        # 音频播放开始回调
        self.on_audio_playback_start = None
        self.audio_playback_started = False  # 标记音频是否已开始播放
        
        # 初始化WAV流式播放器
        if WAV_STREAM_AVAILABLE and WavStreamAudioManager:
            try:
                self.wav_stream_manager = WavStreamAudioManager(self)
                self.use_wav_streaming = True
                print("✅ WAV流式播放器初始化成功")
            except Exception as e:
                print(f"WAV流式播放器初始化失败: {e}")
                self.use_wav_streaming = False
    
    def set_audio_playback_start_callback(self, callback):
        """设置音频播放开始回调"""
        self.on_audio_playback_start = callback
    
    def _notify_audio_playback_start(self):
        """通知音频播放开始"""
        if not self.audio_playback_started and self.on_audio_playback_start:
            self.audio_playback_started = True
            try:
                self.on_audio_playback_start()
            except Exception as e:
                print(f"音频播放开始回调执行失败: {e}")
    
    def play_wav_stream_direct(self, text: str, on_status_update=None) -> bool:
        """
        直接播放WAV流式音频 - 基于ref.py的实现
        
        Args:
            text: 要转换为语音的文本
            on_status_update: 状态更新回调函数
            
        Returns:
            bool: 是否成功启动播放
        """
        if not self.use_wav_streaming or not self.wav_stream_manager:
            print("WAV流式播放不可用")
            return False
        
        try:
            # 重置播放开始状态
            self.audio_playback_started = False
            
            # 设置状态回调
            if on_status_update:
                self.wav_stream_manager.set_status_callback(on_status_update)
            
            # 设置播放开始回调
            self.wav_stream_manager.set_playback_start_callback(self._notify_audio_playback_start)
            
            # 构建TTS URL
            server_url = f"{Config.API_BASE_URL}/tts/generate"
            
            # 启动WAV流式播放
            success = self.wav_stream_manager.handle_wav_stream_request(text, server_url)
            
            if success:
                print(f"✅ WAV流式播放已启动: {text[:50]}...")
                if on_status_update:
                    on_status_update("🎵 WAV流式播放已启动")
                return True
            else:
                print("❌ WAV流式播放启动失败")
                return False
                
        except Exception as e:
            error_msg = f"WAV流式播放失败: {e}"
            print(error_msg)
            if on_status_update:
                on_status_update(f"❌ {error_msg}")
            return False
    
    def stop_all_audio(self):
        """停止所有音频播放"""
        # 重置播放开始状态
        self.audio_playback_started = False
        
        # 停止WAV流式播放
        if self.use_wav_streaming and self.wav_stream_manager:
            try:
                self.wav_stream_manager.stop_all()
                print("WAV流式播放已停止")
            except Exception as e:
                print(f"停止WAV流式播放失败: {e}")
    
    def toggle_wav_streaming(self, enable: bool):
        """切换WAV流式播放模式"""
        if WAV_STREAM_AVAILABLE and self.wav_stream_manager:
            self.use_wav_streaming = enable
            self.wav_stream_manager.enable_wav_streaming(enable)
            print(f"WAV流式播放模式: {'启用' if enable else '禁用'}")
        else:
            self.use_wav_streaming = False
            print("WAV流式播放不可用")
    
    def get_wav_stream_stats(self) -> dict:
        """获取WAV流式播放统计信息"""
        if self.use_wav_streaming and self.wav_stream_manager:
            return self.wav_stream_manager.get_stats()
        return {"wav_stream_available": False}
    
    def cleanup_all_temp_files(self):
        """清理所有临时音频文件"""
        try:
            for temp_file in self.temp_audio_files[:]:  # 使用切片复制避免迭代时修改
                self._cleanup_audio_file(temp_file)
        except Exception as e:
            print(f"清理临时文件总体失败: {e}")
    
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
