"""
流式响应管理模块 - 重新设计
按照用户需求简化流式显示逻辑
"""

import time
from datetime import datetime
from typing import Optional
import tkinter as tk
from core.config import Config
from utils.content_filter import ContentFilter


class StreamingResponseManager:
    """流式响应管理器 - 简化版"""
    
    def __init__(self, ui_manager, client=None):
        self.ui_manager = ui_manager
        self.client = client  # 保存客户端引用，用于访问音频时间
        
        # 当前流式响应状态
        self.current_response_line_start = None  # 当前响应开始位置
        self.current_response_type = None        # 当前响应类型
        self.is_streaming = False                # 是否正在流式输出
        
        # 响应内容缓存
        self._current_text = ""
        
    def reset_streaming_response(self):
        """重置流式响应状态"""
        self.current_response_line_start = None
        self.current_response_type = None
        self.is_streaming = False
        self._current_text = ""
        print("重置了流式响应状态")
    
    def start_streaming_response(self, response_type: str):
        """开始流式响应"""
        try:
            # 重置状态
            self.reset_streaming_response()
            
            # 设置响应类型和状态
            self.current_response_type = response_type
            self.is_streaming = True
            
            # 根据类型设置前缀
            if response_type == "cloud":
                prefix = "☁️Elysia"
            elif response_type == "audio":
                prefix = "🎤Elysia"
            else:  # local
                prefix = "Elysia"
            
            # 创建新的响应行
            timestamp = datetime.now().strftime("%H:%M:%S")
            response_header = f"[{timestamp}] {prefix}: "
            
            if self.ui_manager.chat_display:
                # 在末尾插入响应头
                self.ui_manager.chat_display.insert("end", response_header)
                
                # 记录当前响应的开始位置（用于后续文本插入）
                self.current_response_line_start = self.ui_manager.chat_display.index("end-1c")
                
                # 滚动到最新位置
                self.ui_manager.chat_display.see("end")
                
                print(f"开始{response_type}流式响应，位置: {self.current_response_line_start}")
            
        except Exception as e:
            print(f"开始流式响应失败: {e}")
            import traceback
            traceback.print_exc()
    
    def append_streaming_text(self, new_text: str):
        """追加流式文本（逐字显示）"""
        try:
            if not self.is_streaming or not self.current_response_line_start:
                print("当前不在流式状态，跳过文本追加")
                return
            
            if not new_text:
                return
            
            # 处理转义字符：将 \n 转换为实际换行
            processed_text = new_text.replace('\\n', '\n')
            
            # 使用优化的流式chunk处理
            filtered_text = ContentFilter.process_streaming_chunk(processed_text, self._current_text)
            
            if not filtered_text:  # 如果被过滤掉了
                print(f"Chunk被过滤: {processed_text[:10]}...")
                return
            
            # 将新文本添加到当前内容
            self._current_text += filtered_text
            
            if self.ui_manager.chat_display:
                # 在当前位置插入新文本
                self.ui_manager.chat_display.insert("end", filtered_text)
                
                # 滚动到最新位置
                self.ui_manager.chat_display.see("end")
                
                # 强制更新UI以立即显示
                self.ui_manager.root.update_idletasks()
                
                print(f"追加文本: {filtered_text[:10]}... (总长度: {len(self._current_text)})")
            
        except Exception as e:
            print(f"追加流式文本失败: {e}")
            import traceback
            traceback.print_exc()
    
    def complete_streaming_response(self):
        """完成流式响应"""
        try:
            if not self.is_streaming:
                return
            
            if self.ui_manager.chat_display:
                # 在当前响应末尾添加换行
                self.ui_manager.chat_display.insert("end", "\n")
                self.ui_manager.chat_display.see("end")
            
            print(f"完成{self.current_response_type}流式响应，总长度: {len(self._current_text)}")
            
            # 如果有客户端引用且有音频时间，现在显示它
            if self.client and hasattr(self.client, 'audio_time'):
                print(f"检查音频时间: {self.client.audio_time}, 请求类型: {getattr(self.client, 'request_type', None)}")
                if self.client.audio_time is not None:
                    # 捕获当前的音频时间值，避免lambda延迟执行时值被清空
                    audio_time_value = self.client.audio_time
                    if self.client.request_type == "chat":
                        # 聊天请求的音频响应时间
                        self.ui_manager.root.after(0, lambda t=audio_time_value: self.ui_manager.show_chat_audio_time(t))
                    else:
                        # 普通音频响应时间
                        self.ui_manager.root.after(0, lambda t=audio_time_value: self.ui_manager.show_audio_time(t))
                    
                    # 清除音频时间，避免重复显示
                    self.client.audio_time = None
                else:
                    print("音频时间为None，跳过显示")
            
            # 重置状态
            self.reset_streaming_response()
            
        except Exception as e:
            print(f"完成流式响应失败: {e}")
            import traceback
            traceback.print_exc()
    
    def update_local_response(self, response: str):
        """更新本地响应显示"""
        try:
            if not response:
                return
            
            # 如果还没开始流式响应，先开始
            if not self.is_streaming:
                self.start_streaming_response("local")
            
            # 计算新增的文本（只添加新的部分）
            if len(response) > len(self._current_text):
                new_text = response[len(self._current_text):]
                self.append_streaming_text(new_text)
            
        except Exception as e:
            print(f"更新本地响应失败: {e}")
            import traceback
            traceback.print_exc()
    
    def update_cloud_response(self, response: str):
        """更新云端响应显示"""
        try:
            if not response:
                return
            
            # 如果还没开始流式响应，先开始
            if not self.is_streaming:
                self.start_streaming_response("cloud")
            
            # 计算新增的文本（只添加新的部分）
            if len(response) > len(self._current_text):
                new_text = response[len(self._current_text):]
                self.append_streaming_text(new_text)
            
        except Exception as e:
            print(f"更新云端响应失败: {e}")
            import traceback
            traceback.print_exc()
    
    def update_audio_response(self, response: str):
        """更新音频响应显示"""
        try:
            if not response:
                return
            
            # 如果还没开始流式响应，先开始
            if not self.is_streaming:
                self.start_streaming_response("audio")
            
            # 计算新增的文本（只添加新的部分）
            if len(response) > len(self._current_text):
                new_text = response[len(self._current_text):]
                self.append_streaming_text(new_text)
            
        except Exception as e:
            print(f"更新音频响应失败: {e}")
            import traceback
            traceback.print_exc()
    
    def finalize_response(self, response_type: str, final_response: str):
        """完成响应"""
        try:
            print(f"正在完成{response_type}响应")
            self.complete_streaming_response()
        except Exception as e:
            print(f"完成响应失败: {e}")
            import traceback
            traceback.print_exc()