"""
主应用程序类
整合所有模块，处理业务逻辑
"""
import threading
import asyncio
import os
import time
from typing import Dict, Any, Optional

from core.config import Config
from core.audio_manager import AudioManager
from ui.main_window import MainUI
from handlers.network_handler import NetworkHandler
from handlers.streaming_manager import StreamingResponseManager
from handlers.streaming_message_handler import StreamingMessageHandler

# 导入控制器
from controllers.chat_controller import ChatController
from controllers.audio_controller import AudioController

# 导入优化工具类
from utils.event_bus import EventBus
from utils.state_manager import StateManager
from utils.thread_manager import ThreadManager
from utils.error_handler import ErrorHandler, handle_errors, set_global_error_handler
from utils.ui_helpers import UIHelper, CallbackManager, RequestHelper
from utils.performance_optimizer import PerformanceOptimizer


class ElysiaClient:
    """Elysia 聊天客户端主类 - 重构版本"""
    
    def __init__(self):
        # 初始化核心工具类
        self._init_core_tools()
        
        # 初始化基础组件
        self._init_base_components()
        
        # 初始化控制器
        self._init_controllers()
        
        # 设置消息处理回调
        self._setup_message_callbacks()
        
        # 设置事件监听器
        self._setup_event_listeners()
        
        # 设置UI事件回调
        self._setup_ui_callbacks()
        
        # 设置窗口关闭事件
        self.ui.set_window_close_callback(self.on_closing)
        
        # 设置WAV流式播放状态回调
        if self.audio_manager.use_wav_streaming and self.audio_manager.wav_stream_manager:
            self.audio_manager.wav_stream_manager.set_status_callback(self.ui.set_status)
    
    def _init_core_tools(self):
        """初始化核心工具类"""
        self.performance_optimizer = PerformanceOptimizer()
        self.event_bus = EventBus()
        self.state_manager = StateManager()
        self.thread_manager = ThreadManager(max_workers=3)
        self.error_handler = ErrorHandler(self.event_bus)
        
        # 设置全局错误处理器
        set_global_error_handler(self.error_handler)
        
        # 设置事件总线的异步发送方法
        self.event_bus.emit_async = self._emit_ui_event
    
    def _init_base_components(self):
        """初始化基础组件"""
        self.ui = MainUI()
        
        # 创建UI助手类
        self.ui_helper = UIHelper(self.ui)
        self.callback_manager = CallbackManager()
        self.request_helper = RequestHelper(self)
        
        self.audio_manager = AudioManager()
        self.network_handler = NetworkHandler()
        self.streaming_manager = StreamingResponseManager(self.ui, self)
        
        # 流式消息处理器
        self.message_handler = StreamingMessageHandler(self.audio_manager)
    
    def _init_controllers(self):
        """初始化控制器"""
        # 聊天控制器
        self.chat_controller = ChatController(
            self.network_handler,
            self.message_handler,
            self.streaming_manager,
            self.state_manager,
            self.ui_helper,
            self.thread_manager,
            self.request_helper
        )
        
        # 音频控制器
        self.audio_controller = AudioController(
            self.audio_manager,
            self.network_handler,
            self.ui_helper,
            self.performance_optimizer,
            self.state_manager,
            self.thread_manager,
            self.request_helper
        )
    
    def _setup_message_callbacks(self):
        """设置流式消息处理回调"""
        callbacks = self.callback_manager.create_message_callbacks(self)
        
        for event_name, callback_func in callbacks.items():
            self.message_handler.set_callback(event_name, callback_func)
        
        # 添加早期TTS回调
        self.message_handler.set_callback("early_tts", self._on_early_tts)
        
        print("✅ 新的优化回调系统已启用 + 早期TTS触发（包含语气）")
    
    def _emit_ui_event(self, event_type: str, data: Any = None):
        """在UI线程中发送事件"""
        def emit_in_ui():
            self.event_bus.emit(event_type, data)
        self.ui.root.after(0, emit_in_ui)
    
    def _setup_event_listeners(self):
        """设置事件监听器"""
        # 状态更新事件
        self.event_bus.on('status_update', self.ui.set_status)
        
        # 聊天消息事件
        def handle_chat_message(data):
            message, sender = data['message'], data['sender']
            self.ui.append_to_chat(message, sender)
        self.event_bus.on('chat_message', handle_chat_message)
        
        # 错误事件
        def handle_error(data):
            title = data.get('title', '错误')
            message = data.get('message', '未知错误')
            self.ui.show_error(title, message)
        self.event_bus.on('error', handle_error)
        
        # 警告事件
        def handle_warning(data):
            title = data.get('title', '警告')
            message = data.get('message', '未知警告')
            self.ui.show_warning(title, message)
        self.event_bus.on('warning', handle_warning)
        
        # 请求时间显示事件
        self.event_bus.on('show_request_time', self.ui.show_request_time)
        self.event_bus.on('show_total_audio_time', self.ui.show_total_audio_time)
        
        # 计时信息事件
        self.event_bus.on('show_timing_info', self.ui.show_timing_info)
    
    async def _on_text_update(self, content, full_text):
        """文本更新回调"""
        self._record_first_response()
        print(f"🔍 UI文本更新: '{full_text}' (长度: {len(full_text)})")
        self.ui_helper.schedule_ui_update(
            self.streaming_manager.update_local_response, full_text
        )
    
    async def _on_text_complete(self, full_text):
        """文本完成回调"""
        print(f"✅ 文本完成: '{full_text}' (长度: {len(full_text)})")
        print(f"🔍 文本完成回调调试 - 文本长度: {len(full_text)}, 去空格后: '{full_text.strip()}'")
        
        # 完成流式响应显示
        self.ui_helper.schedule_ui_update(
            self.streaming_manager.update_local_response, full_text
        )
        
        # 重要：只有在没有触发早期TTS的情况下才触发常规TTS
        if full_text and full_text.strip() and not self.message_handler._has_triggered_early_tts:
            print(f"🎵 文本完成后自动触发TTS（无早期TTS）...")
            self.ui_helper.schedule_ui_update(
                self.audio_controller.handle_auto_tts, full_text.strip(), delay=100
            )
        else:
            print(f"⚠️ 跳过TTS - 已触发早期TTS或文本为空")
            print(f"   has_triggered_early_tts: {self.message_handler._has_triggered_early_tts}")
            print(f"   full_text: {repr(full_text)}")
            print(f"   full_text.strip(): {repr(full_text.strip() if full_text else None)}")
    
    async def _on_early_tts(self, dialogue_text):
        """早期TTS回调 - 当检测到语气描述结束时触发"""
        print(f"🎵🎵🎵 早期TTS触发! 对话内容+语气: '{dialogue_text[:50]}...'")
        print(f"🎵 开始早期TTS生成，包含语气的对话内容: '{dialogue_text[:50]}...'")
        
        # 在UI中显示对话内容部分（包含语气）
        self.ui_helper.schedule_ui_update(
            self.streaming_manager.update_local_response, dialogue_text
        )
        
        # 触发TTS
        self.ui_helper.schedule_ui_update(
            self.audio_controller.handle_auto_tts, dialogue_text.strip(), delay=50
        )
    
    async def _on_audio_start(self, message):
        """音频开始回调"""
        self._record_first_audio()
        print(f"🎵 开始接收语音: {message}")
        self.ui_helper.debounced_status_update("🎵 开始接收语音...")
    
    async def _on_audio_status(self, status):
        """音频状态回调"""
        self.ui_helper.debounced_status_update(status)
    
    async def _on_audio_chunk(self, message):
        """音频块回调"""
        # 在当前实现中，音频数据处理是通过_create_audio_data_handler动态创建的
        # 这里主要记录日志，实际处理在其他地方
        print(f"🎵 收到音频数据块: {message}")
    
    async def _on_audio_end(self, message):
        """音频结束回调"""
        print(f"🎵 语音接收完成: {message}")
        self.ui_helper.schedule_ui_update(self._finish_current_request)
    
    async def _on_token_usage(self, message):
        """Token使用统计回调"""
        print(f"📊 Token使用统计: {message}")
        self.ui_helper.schedule_ui_update(self.ui.show_timing_info, message)
    
    async def _on_error(self, message):
        """错误回调"""
        print(f"❌ 错误: {message}")
        self.ui_helper.show_error_safe("请求失败", str(message))
    
    async def _on_done(self, message):
        """完成回调"""
        print(f"✅ 完成: {message}")
        self.ui_helper.schedule_ui_update(self._finish_current_request)
        
    def _record_first_response(self):
        """记录第一个响应的时间"""
        response_time = self.state_manager.record_first_response()
        if response_time > 0:
            print(f"收到第一个响应，耗时: {response_time:.0f}ms")
            
            # 在UI中显示请求时间
            self.ui_helper.schedule_ui_update(
                lambda: self.ui.show_request_time(response_time))
    
    def _record_first_audio(self):
        """记录第一个音频块的时间"""
        audio_time = self.state_manager.record_first_audio()
        if audio_time > 0:
            print(f"收到第一个音频块，耗时: {audio_time:.0f}ms")
    
    def _setup_ui_callbacks(self):
        """设置UI事件回调"""
        self.ui.on_send_message_callback = self.on_send_message
        self.ui.on_stream_chat_callback = self.on_stream_chat
        self.ui.on_cloud_chat_callback = self.on_cloud_chat
        self.ui.on_normal_chat_callback = self.on_normal_chat
        self.ui.on_upload_audio_callback = self.on_upload_audio
        self.ui.on_show_history_callback = self.on_show_history
        self.ui.on_test_wav_stream_callback = self.on_test_wav_stream
        self.ui.on_clear_chat_callback = self.on_clear_chat
    

    
    def _finish_current_request(self):
        """完成当前请求"""
        self.ui.enable_buttons()
        self.ui.set_status("就绪")
        
        # 重置消息处理器状态
        self.message_handler.reset()
    
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
        if message:
            self.chat_controller.handle_stream_chat(message)
    
    def on_cloud_chat(self):
        """云端流式聊天"""
        message = self.ui.get_last_user_message()
        if message:
            self.chat_controller.handle_cloud_chat(message)
    
    def on_normal_chat(self):
        """普通聊天"""
        message = self.ui.get_last_user_message()
        if message:
            # 获取聊天结果并触发TTS
            result = self.chat_controller.handle_normal_chat(message)
            if result:
                self.ui_helper.schedule_ui_update(
                    self.audio_controller.handle_auto_tts, result, delay=100)
    
    def on_upload_audio(self):
        """上传音频文件"""
        audio_file = self.ui.show_file_dialog("选择音频文件")
        if audio_file:
            self.audio_controller.handle_upload_audio(audio_file)
    
    def on_test_wav_stream(self):
        """测试WAV流式播放"""
        if not self.audio_manager.use_wav_streaming:
            self.ui_helper.show_warning_safe("提示", "WAV流式播放功能不可用")
            return
        
        test_text = "大概率是没有的，我也希望如此，毕竟自己的故事还是应当由自己来诉说。"
        self.audio_controller.handle_wav_stream_test(test_text)
    
    def on_show_history(self):
        """显示聊天历史"""
        self.ui_helper.debounced_status_update("正在获取历史记录...")
        self.thread_manager.submit_task(self._show_history, task_name="show_history")
    
    def on_clear_chat(self):
        """清空聊天记录"""
        self.ui.clear_chat_display()
        self.ui_helper.safe_append_chat("🗑️ 聊天记录已清空", "系统")
        self.performance_optimizer.cache_manager.clear_all_caches()
    
    # 保留必要的回调方法 - 已经在上面定义过的都删除重复
    
    def _show_history(self):
        """获取并显示历史记录"""
        try:
            history = self.network_handler.get_chat_history()
            
            self.ui_helper.schedule_ui_update(
                lambda: self.ui.append_to_chat("=== 聊天历史 ===", "系统"))
            for record in history:
                self.ui_helper.schedule_ui_update(
                    lambda r=record: self.ui.append_to_chat(r, "历史"))
            self.ui_helper.schedule_ui_update(
                lambda: self.ui.append_to_chat("=== 历史结束 ===", "系统"))
            
            self.ui_helper.schedule_ui_update(
                lambda: self.ui.set_status("历史记录获取完成"))
            
        except Exception as e:
            error_msg = str(e)
            self.ui_helper.show_error_safe("获取历史失败", error_msg)
    
    def on_closing(self):
        """窗口关闭事件处理"""
        try:
            # 生成性能报告
            performance_report = self.performance_optimizer.get_comprehensive_report()
            print("=== 性能报告 ===")
            print(f"运行时间: {performance_report['performance']['runtime']:.2f}秒")
            print(f"缓存命中率: {performance_report['performance']['cache_hit_rate']:.2%}")
            
            # 清理性能优化器
            self.performance_optimizer.cleanup()
            
            # 关闭线程管理器
            self.thread_manager.shutdown(wait=True)
            # 清理临时文件
            self.audio_manager.cleanup_all_temp_files()
            # 停止音频播放
            self.audio_manager.stop_all_audio()
            # 清理事件总线
            self.event_bus.clear()
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
