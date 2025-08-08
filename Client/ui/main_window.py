"""
主UI界面模块
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from datetime import datetime
from typing import Optional, Callable
from core.config import Config


class MainUI:
    """主界面类"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Elysia 聊天客户端")
        self.root.geometry(Config.WINDOW_SIZE)
        
        # UI组件
        self.chat_display: Optional[scrolledtext.ScrolledText] = None
        self.message_entry: Optional[ttk.Entry] = None
        self.status_var: Optional[tk.StringVar] = None
        
        # 按钮组件
        self.stream_button: Optional[ttk.Button] = None
        self.cloud_button: Optional[ttk.Button] = None
        self.normal_button: Optional[ttk.Button] = None
        self.audio_button: Optional[ttk.Button] = None
        self.history_button: Optional[ttk.Button] = None
        self.clear_button: Optional[ttk.Button] = None
        self.send_button: Optional[ttk.Button] = None
        
        # 事件回调
        self.on_send_message_callback: Optional[Callable] = None
        self.on_stream_chat_callback: Optional[Callable] = None
        self.on_cloud_chat_callback: Optional[Callable] = None
        self.on_normal_chat_callback: Optional[Callable] = None
        self.on_upload_audio_callback: Optional[Callable] = None
        self.on_show_history_callback: Optional[Callable] = None
        self.on_clear_chat_callback: Optional[Callable] = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="Elysia 聊天客户端", 
                               font=("Arial", Config.TITLE_FONT_SIZE, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # 聊天显示区域
        self._setup_chat_area(main_frame)
        
        # 输入区域
        self._setup_input_area(main_frame)
        
        # 控制按钮区域
        self._setup_control_buttons(main_frame)
        
        # 状态栏
        self._setup_status_bar(main_frame)
    
    def _setup_chat_area(self, parent):
        """设置聊天显示区域"""
        chat_frame = ttk.LabelFrame(parent, text="聊天记录", padding="5")
        chat_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(0, 10))
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=20,
            font=(Config.FONT_FAMILY, Config.FONT_SIZE)
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew")
    
    def _setup_input_area(self, parent):
        """设置输入区域"""
        input_frame = ttk.Frame(parent)
        input_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        
        self.message_entry = ttk.Entry(input_frame, font=(Config.FONT_FAMILY, Config.FONT_SIZE))
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.message_entry.bind("<Return>", self._on_send_message)
        
        self.send_button = ttk.Button(input_frame, text="发送", command=self._on_send_message)
        self.send_button.grid(row=0, column=1)
    
    def _setup_control_buttons(self, parent):
        """设置控制按钮区域"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=3, column=0, columnspan=3, sticky="ew")
        
        self.stream_button = ttk.Button(control_frame, text="流式聊天", command=self._on_stream_chat)
        self.stream_button.grid(row=0, column=0, padx=(0, 10))
        
        self.cloud_button = ttk.Button(control_frame, text="云端聊天", command=self._on_cloud_chat)
        self.cloud_button.grid(row=0, column=1, padx=(0, 10))
        
        self.normal_button = ttk.Button(control_frame, text="普通聊天", command=self._on_normal_chat)
        self.normal_button.grid(row=0, column=2, padx=(0, 10))
        
        self.audio_button = ttk.Button(control_frame, text="上传音频", command=self._on_upload_audio)
        self.audio_button.grid(row=0, column=3, padx=(0, 10))
        
        self.history_button = ttk.Button(control_frame, text="查看历史", command=self._on_show_history)
        self.history_button.grid(row=0, column=4, padx=(0, 10))
        
        self.clear_button = ttk.Button(control_frame, text="清空聊天", command=self._on_clear_chat)
        self.clear_button.grid(row=0, column=5)
    
    def _setup_status_bar(self, parent):
        """设置状态栏"""
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(parent, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 0))
    
    # 事件处理方法
    def _on_send_message(self, event=None):
        """发送消息事件处理"""
        if self.on_send_message_callback:
            self.on_send_message_callback()
    
    def _on_stream_chat(self):
        """流式聊天事件"""
        if self.on_stream_chat_callback:
            self.on_stream_chat_callback()
    
    def _on_cloud_chat(self):
        """云端聊天事件"""
        if self.on_cloud_chat_callback:
            self.on_cloud_chat_callback()
    
    def _on_normal_chat(self):
        """普通聊天事件"""
        if self.on_normal_chat_callback:
            self.on_normal_chat_callback()
    
    def _on_upload_audio(self):
        """上传音频事件"""
        if self.on_upload_audio_callback:
            self.on_upload_audio_callback()
    
    def _on_show_history(self):
        """显示历史事件"""
        if self.on_show_history_callback:
            self.on_show_history_callback()
    
    def _on_clear_chat(self):
        """清空聊天事件"""
        if self.on_clear_chat_callback:
            self.on_clear_chat_callback()
    
    # 公共方法
    def append_to_chat(self, message: str, sender: str = ""):
        """向聊天区域添加消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if sender:
            formatted_message = f"[{timestamp}] {sender}: {message}\n"
        else:
            formatted_message = f"[{timestamp}] {message}\n"
        
        if self.chat_display:
            self.chat_display.insert(tk.END, formatted_message)
            self.chat_display.see(tk.END)
            self.root.update_idletasks()
    
    def get_message_text(self) -> str:
        """获取输入框中的消息"""
        if self.message_entry:
            return self.message_entry.get().strip()
        return ""
    
    def clear_message_text(self):
        """清空输入框"""
        if self.message_entry:
            self.message_entry.delete(0, tk.END)
    
    def set_status(self, status: str):
        """设置状态栏文本"""
        if self.status_var:
            self.status_var.set(status)
    
    def show_timing_info(self, timing_data: dict):
        """在聊天界面显示计时信息"""
        if not Config.SHOW_TIMING_INFO:
            return
            
        timing_info = "⏱️ 各阶段耗时:\n"
        
        # 格式化计时信息
        for stage, time_ms in timing_data.items():
            if isinstance(time_ms, (int, float)):
                # 转换为秒并格式化
                time_s = time_ms / 1000.0
                if time_s >= 1.0:
                    time_str = f"{time_s:.{Config.TIMING_PRECISION}f}s"
                else:
                    time_str = f"{time_ms:.0f}ms"
            else:
                time_str = str(time_ms)
            
            timing_info += f"  • {stage}: {time_str}\n"
        
        self.append_to_chat(timing_info.strip(), "系统")
    
    def show_request_time(self, request_time_ms: float):
        """显示请求响应时间"""
        if not Config.SHOW_REQUEST_TIME:
            return
            
        time_s = request_time_ms / 1000.0
        if time_s >= 1.0:
            time_str = f"{time_s:.{Config.REQUEST_TIME_PRECISION}f}s"
        else:
            time_str = f"{request_time_ms:.0f}ms"
        
        self.append_to_chat(f"🚀 请求响应时间: {time_str}", "系统")
    
    def show_audio_time(self, audio_time_ms: float):
        """显示音频响应时间"""
        if not Config.SHOW_AUDIO_TIME:
            return
            
        time_s = audio_time_ms / 1000.0
        if time_s >= 1.0:
            time_str = f"{time_s:.{Config.AUDIO_TIME_PRECISION}f}s"
        else:
            time_str = f"{audio_time_ms:.0f}ms"
        
        self.append_to_chat(f"🎵 音频响应时间: {time_str}", "系统")
    
    def show_chat_audio_time(self, audio_time_ms: float):
        """显示聊天音频响应时间"""
        if not Config.SHOW_CHAT_AUDIO_TIME:
            return
            
        time_s = audio_time_ms / 1000.0
        if time_s >= 1.0:
            time_str = f"{time_s:.{Config.CHAT_AUDIO_TIME_PRECISION}f}s"
        else:
            time_str = f"{audio_time_ms:.0f}ms"
        
        self.append_to_chat(f"🗣️ 聊天音频响应时间: {time_str}", "系统")
    
    def get_last_user_message(self) -> str:
        """获取最后一条用户消息"""
        if not self.chat_display:
            return ""
            
        content = self.chat_display.get("1.0", tk.END)
        lines = content.split('\n')
        
        print(f"聊天内容: {content}")
        print(f"分割后的行数: {len(lines)}")
        
        for line in reversed(lines):
            print(f"检查行: {line}")
            if "用户:" in line:
                # 提取消息内容
                parts = line.split("用户:", 1)
                if len(parts) > 1:
                    message = parts[1].strip()
                    print(f"找到用户消息: {message}")
                    return message
        print("未找到用户消息")
        return ""
    
    def clear_chat_display(self):
        """清空聊天显示区域"""
        if self.chat_display:
            self.chat_display.delete("1.0", tk.END)
        self.set_status("聊天记录已清空")
    
    def disable_buttons(self):
        """禁用按钮"""
        buttons = [
            self.stream_button, self.cloud_button, self.normal_button,
            self.audio_button, self.send_button
        ]
        for button in buttons:
            if button:
                button.configure(state="disabled")
    
    def enable_buttons(self):
        """启用按钮"""
        buttons = [
            self.stream_button, self.cloud_button, self.normal_button,
            self.audio_button, self.send_button
        ]
        for button in buttons:
            if button:
                button.configure(state="normal")
    
    def show_file_dialog(self, title: str = "选择音频文件") -> str:
        """显示文件选择对话框"""
        return filedialog.askopenfilename(
            title=title,
            filetypes=Config.SUPPORTED_AUDIO_FORMATS
        )
    
    def show_error(self, title: str, message: str):
        """显示错误消息框"""
        messagebox.showerror(title, message)
    
    def show_warning(self, title: str, message: str):
        """显示警告消息框"""
        messagebox.showwarning(title, message)
    
    def update_chat_line(self, line_number: int, content: str):
        """更新聊天记录中的特定行"""
        if not self.chat_display:
            return
            
        try:
            # 使用1基的行号系统（Tkinter使用1基）
            line_start = f"{line_number + 1}.0"
            line_end = f"{line_number + 1}.end"
            
            # 获取当前内容以验证行号有效性
            try:
                current_content = self.chat_display.get(line_start, line_end)
                if not current_content:
                    print(f"警告：行 {line_number + 1} 为空或不存在")
                    return
            except Exception as e:
                print(f"无法访问行 {line_number + 1}: {e}")
                return
            
            # 删除旧内容并插入新内容
            self.chat_display.delete(line_start, line_end)
            self.chat_display.insert(line_start, content)
            
            # 确保滚动到最新内容
            self.chat_display.see("end")
            
        except Exception as e:
            print(f"更新聊天行失败: {e}")
            # 作为fallback，在末尾添加新行
            self.append_to_chat(f"[更新失败，补充] {content}", "系统")
    
    def get_chat_content(self) -> str:
        """获取聊天显示区域的全部内容"""
        if self.chat_display:
            return self.chat_display.get("1.0", tk.END)
        return ""
    
    def get_chat_lines(self) -> list:
        """获取聊天内容的行列表"""
        content = self.get_chat_content()
        return content.strip().split('\n')
    
    def set_window_close_callback(self, callback: Callable):
        """设置窗口关闭回调"""
        self.root.protocol("WM_DELETE_WINDOW", callback)
    
    def run(self):
        """运行主循环"""
        self.root.mainloop()
    
    def quit(self):
        """退出应用"""
        self.root.destroy()
