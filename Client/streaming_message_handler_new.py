#!/usr/bin/env python3
"""
重写的流式消息处理器 - 专门处理服务端发送的流式消息
针对服务端OGG格式(32000Hz,1声道,16bit)音频流进行优化
"""

import json
import asyncio
import base64
import time
from typing import Dict, Any, Callable, Optional
from core.audio_manager import AudioManager


class StreamingMessageHandler:
    """重写的流式消息处理器 - 专门针对OGG流式音频优化"""
    
    def __init__(self, audio_manager: AudioManager):
        self.audio_manager = audio_manager
        self.current_text_content = ""
        self.is_audio_streaming = False
        self.message_callbacks = {}
        
        # OGG流式音频缓冲区
        self.audio_buffer = bytearray()
        
        # 流式状态管理
        self._stream_type = None  # "text" 或 "audio"
        self._last_activity_time = time.time()
        
        print("🎵 StreamingMessageHandler初始化完成 - OGG流式音频优化版本")
    
    def set_callback(self, message_type: str, callback: Callable):
        """设置特定消息类型的回调函数"""
        self.message_callbacks[message_type] = callback
        print(f"📝 设置回调: {message_type}")
    
    def set_message_callback(self, message_type: str, callback: Callable):
        """设置特定消息类型的回调函数（向后兼容）"""
        return self.set_callback(message_type, callback)
    
    async def handle_message_line(self, raw_line: str) -> bool:
        """向后兼容的消息处理方法"""
        return await self.process_message_line(raw_line)
    
    async def process_message_line(self, raw_line: str) -> bool:
        """
        处理单行流式消息 - 新的入口函数
        返回True表示消息处理完成，False表示需要继续处理
        """
        if not raw_line or not raw_line.strip():
            return False
        
        line = raw_line.strip()
        self._last_activity_time = time.time()
        
        # 尝试解析JSON消息
        try:
            message = json.loads(line)
            message_type = message.get("type", "")
            
            if message_type == "text":
                return await self._handle_text_message(message)
            elif message_type == "audio":
                return await self._handle_audio_message(message)
            elif message_type == "audio_chunk":
                return await self._handle_audio_chunk_new(message)
            elif message_type == "audio_start":
                return await self._handle_audio_start(message)
            elif message_type == "audio_end":
                return await self._handle_audio_end(message)
            elif message_type == "error":
                return await self._handle_error_message(message)
            elif message_type == "token_usage":
                return await self._handle_token_usage_message(message)
            elif message_type == "done":
                return await self._handle_done_message(message)
            else:
                print(f"⚠️ 未知消息类型: {message_type}")
                return False
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"原始数据: {line[:100]}...")
            return False
        except Exception as e:
            print(f"❌ 消息处理异常: {e}")
            return False
    
    async def _handle_text_message(self, message: Dict[str, Any]) -> bool:
        """处理文本消息"""
        try:
            content = message.get("content", "")
            if content:
                self.current_text_content += content
                print(f"📝 文本内容: {content}")
                
                # 调用文本更新回调 - 传递content和完整文本
                if "text_update" in self.message_callbacks:
                    try:
                        await self.message_callbacks["text_update"](content, self.current_text_content)
                        print(f"✅ 文本更新回调成功执行: '{self.current_text_content[:50]}...'")
                    except Exception as e:
                        print(f"❌ 文本更新回调执行失败: {e}")
                
                return True
        except Exception as e:
            print(f"❌ 处理文本消息失败: {e}")
        
        return False
    
    async def _handle_audio_message(self, message: Dict[str, Any]) -> bool:
        """处理传统音频消息（非流式）"""
        try:
            audio_data = message.get("audio", "")
            if audio_data:
                # 处理传统的完整音频数据
                audio_bytes = base64.b64decode(audio_data)
                # 使用播放完整音频的方法
                await self.audio_manager.play_complete_ogg_audio(audio_bytes)
                return True
        except Exception as e:
            print(f"❌ 处理音频消息失败: {e}")
        
        return False
    
    async def _handle_audio_start(self, message: Dict[str, Any]) -> bool:
        """处理音频开始消息"""
        print("🎵 音频流开始")
        self.is_audio_streaming = True
        self.audio_buffer.clear()
        self._stream_type = "audio"
        
        # 调用音频开始回调
        if "audio_start" in self.message_callbacks:
            try:
                await self.message_callbacks["audio_start"](message)
            except Exception as e:
                print(f"❌ 音频开始回调执行失败: {e}")
        
        return True
    
    async def _handle_audio_chunk_new(self, message: Dict[str, Any]) -> bool:
        """处理音频块消息 - 新的OGG优化版本"""
        if not self.is_audio_streaming:
            print("⚠️ 收到音频块但流未开始")
            return False
        
        try:
            # 尝试多种可能的字段名
            chunk_data = message.get("audio_data", "") or message.get("chunk", "")
            if not chunk_data:
                print("⚠️ 空音频块 - 未找到audio_data或chunk字段")
                return False
            
            # 解码音频块数据
            try:
                audio_chunk = base64.b64decode(chunk_data)
                print(f"🎵 成功解码音频块: {len(audio_chunk)}字节")
            except Exception as e:
                print(f"❌ 音频块解码失败: {e}")
                return False
            
            return await self._process_audio_chunk_streaming(audio_chunk)
            
        except Exception as e:
            print(f"❌ 处理音频块失败: {e}")
            return False
    
    async def _process_audio_chunk_streaming(self, audio_chunk: bytes) -> bool:
        """处理流式音频块的核心逻辑"""
        try:
            # 追加到音频缓冲区
            self.audio_buffer.extend(audio_chunk)
            accumulated_size = len(self.audio_buffer)
            
            print(f"🎵 收到音频块: {len(audio_chunk)}字节 (总计: {accumulated_size}字节)")
            
            # 只积累数据，在audio_end时统一播放
            print(f"📝 积累OGG数据: +{len(audio_chunk)}字节 (总计: {accumulated_size}字节)")
            
            return True
            
        except Exception as e:
            print(f"❌ 音频块流式处理失败: {e}")
            return False
    
    async def _handle_audio_end(self, message: Dict[str, Any]) -> bool:
        """处理音频结束消息 - 播放完整音频"""
        print("🎵 音频流结束")
        
        try:
            final_size = len(self.audio_buffer)
            print(f"🎵 最终音频数据大小: {final_size}字节")
            
            if final_size > 0:
                # 使用完整的音频数据进行最终播放
                print(f"▶️ 开始播放完整OGG音频数据 ({final_size}字节)")
                await self.audio_manager.play_complete_ogg_audio(
                    bytes(self.audio_buffer)
                )
                print(f"✅ 完整OGG音频播放完成")
            
            # 调用音频结束回调
            if "audio_end" in self.message_callbacks:
                try:
                    await self.message_callbacks["audio_end"](message)
                except Exception as e:
                    print(f"❌ 音频结束回调执行失败: {e}")
            
        except Exception as e:
            print(f"❌ 音频结束处理失败: {e}")
        finally:
            # 清理状态
            self.is_audio_streaming = False
            self.audio_buffer.clear()
            self._stream_type = None
            if hasattr(self, '_playback_started'):
                delattr(self, '_playback_started')
        
        return True
    
    async def _handle_error_message(self, message: Dict[str, Any]) -> bool:
        """处理错误消息"""
        error_msg = message.get("error", "未知错误")
        print(f"❌ 服务器错误: {error_msg}")
        
        # 调用错误回调
        if "error" in self.message_callbacks:
            try:
                await self.message_callbacks["error"](message)
            except Exception as e:
                print(f"❌ 错误回调执行失败: {e}")
        
        return True
    
    async def _handle_token_usage_message(self, message: Dict[str, Any]) -> bool:
        """处理token使用统计消息"""
        try:
            model_type = message.get("model_type", "unknown")
            current_turn = message.get("current_turn", {})
            input_tokens = current_turn.get("input_tokens", 0)
            output_tokens = current_turn.get("output_tokens", 0)
            
            print(f"📊 Token使用统计 ({model_type}): 输入={input_tokens}, 输出={output_tokens}")
            
            # 调用token统计回调
            if "token_usage" in self.message_callbacks:
                try:
                    await self.message_callbacks["token_usage"](message)
                except Exception as e:
                    print(f"❌ Token统计回调执行失败: {e}")
            
            return True
        except Exception as e:
            print(f"❌ 处理token统计消息失败: {e}")
            return False
    
    async def _handle_done_message(self, message: Dict[str, Any]) -> bool:
        """处理完成消息"""
        print("✅ 流式响应完成")
        
        # 如果有累积的文本内容，调用文本完成回调
        if self.current_text_content and "text_complete" in self.message_callbacks:
            try:
                await self.message_callbacks["text_complete"](self.current_text_content)
                print(f"✅ 文本完成回调成功执行: '{self.current_text_content[:50]}...'")
            except Exception as e:
                print(f"❌ 文本完成回调执行失败: {e}")
        
        # 调用完成回调
        if "done" in self.message_callbacks:
            try:
                await self.message_callbacks["done"](message)
            except Exception as e:
                print(f"❌ 完成回调执行失败: {e}")
        
        return True
    
    def get_current_text(self) -> str:
        """获取当前累积的文本内容"""
        return self.current_text_content
    
    def clear_text(self):
        """清空文本内容"""
        self.current_text_content = ""
    
    def is_streaming_active(self) -> bool:
        """检查是否有活跃的流"""
        return self.is_audio_streaming or bool(self._stream_type)
    
    def get_stream_stats(self) -> Dict[str, Any]:
        """获取流状态统计"""
        return {
            "is_audio_streaming": self.is_audio_streaming,
            "audio_buffer_size": len(self.audio_buffer),
            "stream_type": self._stream_type,
            "text_length": len(self.current_text_content),
            "last_activity": self._last_activity_time,
            "has_playback_started": hasattr(self, '_playback_started')
        }
    
    def reset(self):
        """重置流式消息处理器状态"""
        print("🔄 重置StreamingMessageHandler状态")
        self.current_text_content = ""
        self.is_audio_streaming = False
        self.audio_buffer.clear()
        self._stream_type = None
        self._last_activity_time = time.time()
        
        # 清理临时属性
        if hasattr(self, '_playback_started'):
            delattr(self, '_playback_started')
        
        print("✅ StreamingMessageHandler状态重置完成")
