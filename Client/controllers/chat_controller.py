"""
聊天功能控制器
"""
import asyncio
from typing import Callable, Optional


class ChatController:
    """聊天功能控制器"""
    
    def __init__(self, network_handler, message_handler, streaming_manager, 
                 state_manager, ui_helper, thread_manager, request_helper):
        self.network_handler = network_handler
        self.message_handler = message_handler
        self.streaming_manager = streaming_manager
        self.state_manager = state_manager
        self.ui_helper = ui_helper
        self.thread_manager = thread_manager
        self.request_helper = request_helper
    
    def handle_stream_chat(self, message: str):
        """处理流式聊天"""
        try:
            # 重置流式响应状态
            self.streaming_manager.reset_streaming_response()
            
            # 开始计时
            self.state_manager.start_request_timer("流式")
            
            # UI状态更新
            self.ui_helper.debounced_status_update("正在发送流式请求...")
            self.ui_helper.safe_disable_buttons()
            
            # 提交任务到线程管理器
            task_wrapper = self.request_helper.execute_request_with_cleanup(
                self._run_async_stream_chat, message
            )
            
            self.thread_manager.submit_task(task_wrapper, task_name="stream_chat")
            
        except Exception as e:
            error_msg = str(e)
            print(f"流式聊天启动异常: {error_msg}")
            self.ui_helper.show_error_safe("流式聊天启动失败", error_msg)
    
    def handle_cloud_chat(self, message: str):
        """处理云端流式聊天"""
        try:
            # 重置流式响应状态
            self.streaming_manager.reset_streaming_response()
            
            # 开始计时
            self.state_manager.start_request_timer("云端流式")
            
            # UI状态更新
            self.ui_helper.debounced_status_update("正在发送云端流式请求...")
            self.ui_helper.safe_disable_buttons()
            
            # 提交任务到线程管理器
            task_wrapper = self.request_helper.execute_request_with_cleanup(
                self._run_async_cloud_chat, message
            )
            
            self.thread_manager.submit_task(task_wrapper, task_name="cloud_chat")
            
        except Exception as e:
            error_msg = str(e)
            print(f"云端流式聊天启动异常: {error_msg}")
            self.ui_helper.show_error_safe("云端流式聊天启动失败", error_msg)
    
    def handle_normal_chat(self, message: str):
        """处理普通聊天"""
        try:
            # 重置流式响应状态
            self.streaming_manager.reset_streaming_response()
            
            # 开始计时
            self.state_manager.start_request_timer("普通")
            
            # UI状态更新
            self.ui_helper.debounced_status_update("正在发送普通请求...")
            self.ui_helper.safe_disable_buttons()
            
            # 提交任务到线程管理器
            task_wrapper = self.request_helper.execute_request_with_cleanup(
                self._normal_chat, message
            )
            
            return self.thread_manager.submit_task(task_wrapper, task_name="normal_chat")
            
        except Exception as e:
            error_msg = str(e)
            print(f"普通聊天启动异常: {error_msg}")
            self.ui_helper.show_error_safe("普通聊天启动失败", error_msg)
            return None
    
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
            print(f"🚀 开始流式聊天: {message}")
            
            await self.network_handler.stream_chat_async(
                message, 
                on_data_received=self.message_handler.handle_message_line
            )
            
        except Exception as e:
            error_msg = str(e)
            print(f"流式聊天异常: {error_msg}")
            
            # 检测特定错误类型并尝试备选方案
            if "Chunk too big" in error_msg or "chunk" in error_msg.lower():
                print("检测到chunk错误，尝试使用普通聊天方式...")
                self.ui_helper.schedule_ui_update(
                    lambda: self.ui_helper.safe_append_chat("流式响应失败，尝试普通聊天...", "系统")
                )
                try:
                    self._normal_chat(message)
                    return
                except Exception as fallback_error:
                    print(f"备选方案也失败: {fallback_error}")
            
            self.ui_helper.show_error_safe("流式聊天失败", error_msg)
        finally:
            self.ui_helper.schedule_ui_update(self._finish_current_request)
    
    async def _cloud_chat_async(self, message: str):
        """异步云端流式聊天 - 使用新的音频处理逻辑"""
        try:
            print(f"☁️ 开始云端流式聊天: {message}")
            
            await self.network_handler.cloud_chat_async(
                message, 
                on_data_received=self.message_handler.handle_message_line
            )
            
        except Exception as e:
            error_msg = str(e)
            print(f"云端流式聊天异常: {error_msg}")
            self.ui_helper.show_error_safe("云端流式聊天失败", error_msg)
        finally:
            self.ui_helper.schedule_ui_update(self._finish_current_request)
    
    def _normal_chat(self, message: str):
        """普通聊天请求"""
        try:
            print(f"💬 开始普通聊天: {message}")
            
            data = self.network_handler.normal_chat_request(message)
            
            # 记录第一个响应时间
            response_time = self.state_manager.record_first_response()
            if response_time > 0:
                self.ui_helper.schedule_ui_update(
                    lambda: self.ui_helper.ui.show_request_time(response_time))
            
            text_response = data.get("text", "")
            
            # 更新UI显示响应
            if text_response:
                self.ui_helper.schedule_ui_update(
                    lambda: self.ui_helper.safe_append_chat(text_response, "Elysia"))
                
                print(f"✅ 普通聊天完成，准备启动TTS...")
                return text_response.strip()
            else:
                self.ui_helper.schedule_ui_update(
                    lambda: self.ui_helper.ui.set_status("收到空响应"))
                
        except Exception as e:
            print(f"普通聊天异常: {e}")
            error_msg = str(e)
            self.ui_helper.show_error_safe("普通聊天失败", error_msg)
        finally:
            self.ui_helper.schedule_ui_update(self._finish_current_request)
        
        return None
    
    def _finish_current_request(self):
        """完成当前请求"""
        # 使用 UI helper 的安全方法
        self.ui_helper.schedule_ui_update(lambda: self.ui_helper.ui.enable_buttons())
        self.ui_helper.schedule_ui_update(lambda: self.ui_helper.ui.set_status("就绪"))
        
        # 重置消息处理器状态
        self.message_handler.reset()
