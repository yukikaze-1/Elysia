import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import requests
import json
import base64
import threading
import pygame
from datetime import datetime
import asyncio
import aiohttp
import tempfile
import platform
import os
import time

class ElysiaClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Elysia 聊天客户端")
        self.root.geometry("800x600")
        
        # 初始化pygame音频（使用更兼容的参数）
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=1024)
            pygame.mixer.init()
            print("pygame音频初始化成功")
        except Exception as e:
            print(f"pygame音频初始化失败: {e}")
        
        # API配置
        self.api_base_url = "http://192.168.1.17:11100"
        
        # 流式音频相关变量
        self.audio_buffer = bytearray()
        self.current_audio_file = None
        self.audio_playing = False
        self.temp_audio_files = []  # 用于管理临时文件
        
        # 流式响应追踪
        self.current_streaming_response_type = None  # "local" 或 "cloud"
        self.current_streaming_response_line = None  # 当前流式响应的行号
        
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
        title_label = ttk.Label(main_frame, text="Elysia 聊天客户端", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # 聊天显示区域
        chat_frame = ttk.LabelFrame(main_frame, text="聊天记录", padding="5")
        chat_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(0, 10))
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=20,
            font=("Microsoft YaHei", 10)
        )
        self.chat_display.grid(row=0, column=0, sticky="nsew")
        
        # 输入区域
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)
        
        self.message_entry = ttk.Entry(input_frame, font=("Microsoft YaHei", 10))
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.message_entry.bind("<Return>", self.on_send_message)
        
        self.send_button = ttk.Button(input_frame, text="发送", command=self.on_send_message)
        self.send_button.grid(row=0, column=1)
        
        # 控制按钮区域
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=3, column=0, columnspan=3, sticky="ew")
        
        self.stream_button = ttk.Button(control_frame, text="流式聊天", command=self.on_stream_chat)
        self.stream_button.grid(row=0, column=0, padx=(0, 10))
        
        self.cloud_button = ttk.Button(control_frame, text="云端聊天", command=self.on_cloud_chat)
        self.cloud_button.grid(row=0, column=1, padx=(0, 10))
        
        self.normal_button = ttk.Button(control_frame, text="普通聊天", command=self.on_normal_chat)
        self.normal_button.grid(row=0, column=2, padx=(0, 10))
        
        self.audio_button = ttk.Button(control_frame, text="上传音频", command=self.on_upload_audio)
        self.audio_button.grid(row=0, column=3, padx=(0, 10))
        
        self.history_button = ttk.Button(control_frame, text="查看历史", command=self.on_show_history)
        self.history_button.grid(row=0, column=4, padx=(0, 10))
        
        self.clear_button = ttk.Button(control_frame, text="清空聊天", command=self.on_clear_chat)
        self.clear_button.grid(row=0, column=5)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        
    def append_to_chat(self, message, sender=""):
        """向聊天区域添加消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if sender:
            formatted_message = f"[{timestamp}] {sender}: {message}\n"
        else:
            formatted_message = f"[{timestamp}] {message}\n"
        
        self.chat_display.insert(tk.END, formatted_message)
        self.chat_display.see(tk.END)
        self.root.update_idletasks()
        
    def on_send_message(self, event=None):
        """发送消息事件处理"""
        message = self.message_entry.get().strip()
        if not message:
            return
        
        self.message_entry.delete(0, tk.END)
        self.append_to_chat(message, "用户")
        
    def on_stream_chat(self):
        """流式聊天"""
        message = self.get_last_user_message()
        if not message:
            messagebox.showwarning("警告", "请先输入消息")
            return
        
        # 重置流式响应状态
        self.reset_streaming_response()
        
        self.status_var.set("正在发送流式请求...")
        self.disable_buttons()
        
        # 在新线程中运行异步函数
        thread = threading.Thread(target=self.run_async_stream_chat, args=(message,))
        thread.daemon = True
        thread.start()
        
    def on_cloud_chat(self):
        """云端流式聊天"""
        message = self.get_last_user_message()
        if not message:
            messagebox.showwarning("警告", "请先输入消息")
            return
        
        # 重置流式响应状态
        self.reset_streaming_response()
        
        self.status_var.set("正在发送云端流式请求...")
        self.disable_buttons()
        
        # 在新线程中运行异步函数
        thread = threading.Thread(target=self.run_async_cloud_chat, args=(message,))
        thread.daemon = True
        thread.start()
        
    def run_async_cloud_chat(self, message):
        """在新线程中运行异步云端流式聊天"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.cloud_chat_async(message))
        finally:
            loop.close()
            
    async def cloud_chat_async(self, message):
        """异步云端流式聊天"""
        try:
            # 设置更大的chunk限制和连接参数
            connector = aiohttp.TCPConnector(
                limit_per_host=100,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(total=120)  # 云端可能需要更长时间
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                read_bufsize=2*1024*1024,  # 2MB buffer
                max_line_size=10*1024*1024,  # 10MB max line size
                max_field_size=10*1024*1024  # 10MB max field size
            ) as session:
                url = f"{self.api_base_url}/chat/stream_text_cloud"
                payload = {"message": message, "user_id": "test_user"}
                
                print(f"发送云端流式请求到: {url}")
                print(f"payload: {payload}")
                
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.root.after(0, lambda: self.append_to_chat(f"云端错误: {error_text}", "系统"))
                        return
                    
                    print(f"收到云端响应: {response.status}")
                    current_response = ""
                    
                    # 使用 content.readline() 而不是逐行迭代
                    while True:
                        try:
                            line = await response.content.readline()
                            if not line:
                                break
                                
                            line_text = line.decode('utf-8').strip()
                            if not line_text:
                                continue
                                
                            print(f"收到云端数据: {line_text[:100]}...")  # 只打印前100个字符
                            
                            try:
                                data = json.loads(line_text)
                                
                                if data.get("type") == "text":
                                    content = data.get("content", "")
                                    current_response += content
                                    
                                    # 应用更强的重复检测和清理
                                    clean_response = self.advanced_duplicate_filter(current_response)
                                    
                                    # 检查是否有实质性的内容变化
                                    if hasattr(self, '_last_cloud_response'):
                                        if self.is_content_similar(clean_response, self._last_cloud_response):
                                            continue
                                    
                                    current_response = clean_response
                                    self._last_cloud_response = clean_response
                                    
                                    # 更新UI（需要在主线程中执行）
                                    response_copy = current_response
                                    self.root.after(0, lambda c=response_copy: self.update_current_cloud_response(c))
                                
                                elif data.get("type") == "audio_start":
                                    # 音频流开始
                                    audio_format = data.get("audio_format", "ogg")
                                    self.root.after(0, lambda: self.init_streaming_audio(audio_format))
                                    
                                elif data.get("type") == "audio_chunk":
                                    # 音频流块
                                    audio_data = data.get("audio_data", "")
                                    chunk_size = data.get("chunk_size", 0)
                                    if audio_data:
                                        self.root.after(0, lambda ad=audio_data, cs=chunk_size: self.handle_audio_chunk(ad, cs))
                                        
                                elif data.get("type") == "audio_end":
                                    # 音频流结束
                                    self.root.after(0, lambda: self.finalize_streaming_audio())
                                    
                                elif data.get("type") == "done":
                                    self.root.after(0, lambda: self.status_var.set("云端流式响应完成"))
                                    # 确保最终响应格式正确
                                    self.root.after(0, lambda: self.finalize_cloud_response(current_response))
                                    # 重置流式响应状态
                                    self.root.after(0, self.reset_streaming_response)
                                    break
                                    
                                elif data.get("type") == "error":
                                    error_msg = data.get("error", "未知错误")
                                    self.root.after(0, lambda msg=error_msg: self.append_to_chat(f"云端错误: {msg}", "系统"))
                                    break
                                    
                            except json.JSONDecodeError as e:
                                print(f"云端JSON解析错误: {e}, 原始数据: {line_text}")
                                continue
                                
                        except Exception as line_error:
                            print(f"云端读取行错误: {line_error}")
                            break
                            
        except Exception as e:
            error_msg = str(e)
            print(f"云端流式聊天异常: {error_msg}")
            self.root.after(0, lambda: self.append_to_chat(f"云端流式聊天失败: {error_msg}", "系统"))
        finally:
            self.root.after(0, self.enable_buttons)
        
    def run_async_stream_chat(self, message):
        """在新线程中运行异步流式聊天"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.stream_chat_async(message))
        finally:
            loop.close()
            
    async def stream_chat_async(self, message):
        """异步流式聊天"""
        try:
            # 设置更大的chunk限制和连接参数
            connector = aiohttp.TCPConnector(
                limit_per_host=100,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(total=60)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                read_bufsize=2*1024*1024,  # 2MB buffer
                max_line_size=10*1024*1024,  # 10MB max line size
                max_field_size=10*1024*1024  # 10MB max field size
            ) as session:
                url = f"{self.api_base_url}/chat/stream_text"
                payload = {"message": message, "user_id": "test_user"}
                
                print(f"发送流式请求到: {url}")
                print(f"payload: {payload}")
                
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.root.after(0, lambda: self.append_to_chat(f"错误: {error_text}", "系统"))
                        return
                    
                    print(f"收到响应: {response.status}")
                    current_response = ""
                    
                    # 使用 content.readline() 而不是逐行迭代
                    while True:
                        try:
                            line = await response.content.readline()
                            if not line:
                                break
                                
                            line_text = line.decode('utf-8').strip()
                            if not line_text:
                                continue
                                
                            print(f"收到数据: {line_text[:100]}...")  # 只打印前100个字符
                            
                            try:
                                data = json.loads(line_text)
                                
                                if data.get("type") == "text":
                                    content = data.get("content", "")
                                    current_response += content
                                    
                                    # 应用更强的重复检测和清理
                                    clean_response = self.advanced_duplicate_filter(current_response)
                                    
                                    # 检查是否有实质性的内容变化
                                    if hasattr(self, '_last_local_response'):
                                        if self.is_content_similar(clean_response, self._last_local_response):
                                            continue
                                    
                                    current_response = clean_response
                                    self._last_local_response = clean_response
                                    
                                    # 更新UI（需要在主线程中执行）
                                    response_copy = current_response
                                    self.root.after(0, lambda c=response_copy: self.update_current_response(c))
                                
                                elif data.get("type") == "audio_start":
                                    # 音频流开始
                                    audio_format = data.get("audio_format", "ogg")
                                    self.root.after(0, lambda: self.init_streaming_audio(audio_format))
                                    
                                elif data.get("type") == "audio_chunk":
                                    # 音频流块
                                    audio_data = data.get("audio_data", "")
                                    chunk_size = data.get("chunk_size", 0)
                                    if audio_data:
                                        self.root.after(0, lambda ad=audio_data, cs=chunk_size: self.handle_audio_chunk(ad, cs))
                                        
                                elif data.get("type") == "audio_end":
                                    # 音频流结束
                                    self.root.after(0, lambda: self.finalize_streaming_audio())
                                    
                                elif data.get("type") == "done":
                                    self.root.after(0, lambda: self.status_var.set("流式响应完成"))
                                    # 确保最终响应格式正确
                                    self.root.after(0, lambda: self.finalize_local_response(current_response))
                                    # 重置流式响应状态
                                    self.root.after(0, self.reset_streaming_response)
                                    break
                                    
                                elif data.get("type") == "error":
                                    error_msg = data.get("error", "未知错误")
                                    self.root.after(0, lambda msg=error_msg: self.append_to_chat(f"错误: {msg}", "系统"))
                                    break
                                    
                            except json.JSONDecodeError as e:
                                print(f"JSON解析错误: {e}, 原始数据: {line_text}")
                                continue
                                
                        except Exception as line_error:
                            print(f"读取行错误: {line_error}")
                            break
                            
        except Exception as e:
            error_msg = str(e)
            print(f"流式聊天异常: {error_msg}")
            
            # 如果是chunk太大的错误，尝试用普通方式获取响应
            if "Chunk too big" in error_msg or "chunk" in error_msg.lower():
                print("检测到chunk错误，尝试使用普通聊天方式...")
                self.root.after(0, lambda: self.append_to_chat("流式响应失败，尝试普通聊天...", "系统"))
                # 调用普通聊天作为备选方案
                try:
                    self.normal_chat(message)
                    return
                except Exception as fallback_error:
                    print(f"备选方案也失败: {fallback_error}")
            
            self.root.after(0, lambda: self.append_to_chat(f"流式聊天失败: {error_msg}", "系统"))
        finally:
            self.root.after(0, self.enable_buttons)
            
    def update_current_response(self, response):
        """更新当前响应显示"""
        try:
            # 调试信息
            print(f"更新本地响应，长度: {len(response)} 字符")
            print(f"响应前50个字符: {response[:50]}...")
            
            # 如果这是第一次更新，创建新的响应行
            if self.current_streaming_response_type != "local" or self.current_streaming_response_line is None:
                # 添加新的响应行
                timestamp = datetime.now().strftime("%H:%M:%S")
                new_content = f"[{timestamp}] Elysia: {response}\n"
                self.chat_display.insert(tk.END, new_content)
                
                # 记录当前流式响应信息
                self.current_streaming_response_type = "local"
                # 获取刚插入行的行号
                content = self.chat_display.get("1.0", tk.END)
                lines = content.strip().split('\n')
                self.current_streaming_response_line = len(lines) - 1  # 最后一行的索引
                print(f"创建了新的本地响应行: {self.current_streaming_response_line}")
            else:
                # 更新现有的响应行
                line_start = f"{self.current_streaming_response_line + 1}.0"
                line_end = f"{self.current_streaming_response_line + 1}.end"
                
                # 删除旧的响应行内容
                self.chat_display.delete(line_start, line_end)
                
                # 插入新的完整响应
                timestamp = datetime.now().strftime("%H:%M:%S")
                new_content = f"[{timestamp}] Elysia: {response}"
                self.chat_display.insert(line_start, new_content)
                print(f"更新了第{self.current_streaming_response_line + 1}行的本地响应")
            
            # 确保滚动到最新内容
            self.chat_display.see(tk.END)
            
        except Exception as e:
            print(f"更新本地响应失败: {e}")
            # 如果更新失败，至少记录错误
            self.append_to_chat(f"显示更新错误: {str(e)}", "系统")
        
    def update_current_cloud_response(self, response):
        """更新当前云端响应显示"""
        try:
            # 调试信息
            print(f"更新云端响应，长度: {len(response)} 字符")
            print(f"响应前50个字符: {response[:50]}...")
            
            # 如果这是第一次更新，创建新的响应行
            if self.current_streaming_response_type != "cloud" or self.current_streaming_response_line is None:
                # 添加新的云端响应行
                timestamp = datetime.now().strftime("%H:%M:%S")
                new_content = f"[{timestamp}] ☁️Elysia: {response}\n"
                self.chat_display.insert(tk.END, new_content)
                
                # 记录当前流式响应信息
                self.current_streaming_response_type = "cloud"
                # 获取刚插入行的行号
                content = self.chat_display.get("1.0", tk.END)
                lines = content.strip().split('\n')
                self.current_streaming_response_line = len(lines) - 1  # 最后一行的索引
                print(f"创建了新的云端响应行: {self.current_streaming_response_line}")
            else:
                # 更新现有的响应行
                line_start = f"{self.current_streaming_response_line + 1}.0"
                line_end = f"{self.current_streaming_response_line + 1}.end"
                
                # 删除旧的响应行内容
                self.chat_display.delete(line_start, line_end)
                
                # 插入新的完整响应
                timestamp = datetime.now().strftime("%H:%M:%S")
                new_content = f"[{timestamp}] ☁️Elysia: {response}"
                self.chat_display.insert(line_start, new_content)
                print(f"更新了第{self.current_streaming_response_line + 1}行的云端响应")
            
            # 确保滚动到最新内容
            self.chat_display.see(tk.END)
            
        except Exception as e:
            print(f"更新云端响应失败: {e}")
            # 如果更新失败，至少记录错误
            self.append_to_chat(f"显示更新错误: {str(e)}", "系统")
        
    def finalize_cloud_response(self, final_response):
        """完成云端响应，确保格式正确"""
        try:
            if not final_response.strip():
                return
            
            # 应用最终的重复内容清理
            clean_final_response = self.advanced_duplicate_filter(final_response)
            
            # 获取当前聊天内容
            content = self.chat_display.get("1.0", tk.END)
            lines = content.strip().split('\n')
            
            # 查找最后一个云端响应并确保格式正确
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() and "☁️Elysia:" in lines[i]:
                    current_line = lines[i]
                    # 检查响应是否需要清理
                    if self.needs_content_cleanup(current_line):
                        # 清理并重新写入正确的响应
                        line_start = f"{i + 1}.0"
                        line_end = f"{i + 1}.end"
                        self.chat_display.delete(line_start, line_end)
                        
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        new_content = f"[{timestamp}] ☁️Elysia: {clean_final_response}"
                        self.chat_display.insert(line_start, new_content)
                        print("清理并修复了云端响应格式")
                    break
                    
        except Exception as e:
            print(f"完成云端响应处理失败: {e}")
    
    def finalize_local_response(self, final_response):
        """完成本地响应，确保格式正确"""
        try:
            if not final_response.strip():
                return
            
            # 应用最终的重复内容清理
            clean_final_response = self.advanced_duplicate_filter(final_response)
            
            # 获取当前聊天内容
            content = self.chat_display.get("1.0", tk.END)
            lines = content.strip().split('\n')
            
            # 查找最后一个本地响应并确保格式正确
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() and "Elysia:" in lines[i] and not "☁️Elysia:" in lines[i]:
                    current_line = lines[i]
                    # 检查响应是否需要清理
                    if self.needs_content_cleanup(current_line):
                        # 清理并重新写入正确的响应
                        line_start = f"{i + 1}.0"
                        line_end = f"{i + 1}.end"
                        self.chat_display.delete(line_start, line_end)
                        
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        new_content = f"[{timestamp}] Elysia: {clean_final_response}"
                        self.chat_display.insert(line_start, new_content)
                        print("清理并修复了本地响应格式")
                    break
                    
        except Exception as e:
            print(f"完成本地响应处理失败: {e}")
    
    def needs_content_cleanup(self, line):
        """检查内容是否需要清理"""
        try:
            # 提取消息内容（去掉时间戳和发送者标识）
            if "Elysia:" in line:
                content_start = line.find("Elysia:") + 7
                content = line[content_start:].strip()
            else:
                content = line
            
            # 检查是否有明显的重复或截断
            lines = content.split('\n')
            if len(lines) > 2:
                # 检查是否有逐渐截断的行
                for i in range(len(lines) - 1):
                    current = lines[i].strip()
                    next_line = lines[i + 1].strip()
                    if current and next_line and current.startswith(next_line) and len(next_line) < len(current) * 0.8:
                        return True
            
            return False
            
        except Exception as e:
            print(f"检查内容清理需求失败: {e}")
            return False
    
    def remove_immediate_duplicates(self, text):
        """移除即时重复的内容"""
        try:
            # 按行分割
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 检查是否和前一行重复
                if cleaned_lines and line == cleaned_lines[-1]:
                    continue
                
                # 检查是否是不完整的重复或截断
                if cleaned_lines:
                    last_line = cleaned_lines[-1]
                    
                    # 如果当前行是上一行的前缀（截断），跳过当前行
                    if last_line.startswith(line) and len(line) < len(last_line):
                        continue
                    
                    # 如果当前行是上一行的扩展，替换上一行
                    elif line.startswith(last_line) and len(line) > len(last_line):
                        cleaned_lines[-1] = line
                        continue
                    
                    # 检查是否是相似的开头但内容不同（可能是重复的句式）
                    # 对于特定的重复句式，只保留第一个完整的
                    if line.startswith("呀～") and last_line.startswith("呀～"):
                        # 如果两行都是以"呀～"开头，保留更完整的那个
                        if len(line) <= len(last_line):
                            continue  # 跳过较短的
                        else:
                            cleaned_lines[-1] = line  # 替换为较长的
                            continue
                
                cleaned_lines.append(line)
            
            # 最后再做一次检查，移除重复的段落
            final_lines = []
            seen_content = set()
            
            for line in cleaned_lines:
                # 对于长句子，检查是否已经有相似的内容
                line_key = line[:50] if len(line) > 50 else line  # 使用前50个字符作为键
                if line_key not in seen_content:
                    final_lines.append(line)
                    seen_content.add(line_key)
            
            return '\n'.join(final_lines)
            
        except Exception as e:
            print(f"移除即时重复失败: {e}")
            return text
    
    def advanced_duplicate_filter(self, text):
        """高级重复内容过滤器"""
        try:
            if not text.strip():
                return text
            
            # 按行分割
            lines = text.split('\n')
            filtered_lines = []
            seen_line_signatures = set()
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 创建行的签名（前30个字符或全部内容）
                line_signature = line[:30] if len(line) > 30 else line
                
                # 检查是否是已存在行的截断版本
                is_truncated = False
                for existing_line in filtered_lines:
                    # 如果当前行是现有行的前缀且明显更短，则跳过
                    if existing_line.startswith(line) and len(line) < len(existing_line) * 0.8:
                        is_truncated = True
                        break
                    # 如果当前行是现有行的扩展版本，替换现有行
                    elif line.startswith(existing_line) and len(line) > len(existing_line) * 1.2:
                        # 找到并替换
                        for i, fl in enumerate(filtered_lines):
                            if fl == existing_line:
                                filtered_lines[i] = line
                                break
                        is_truncated = True
                        break
                
                if not is_truncated and line_signature not in seen_line_signatures:
                    filtered_lines.append(line)
                    seen_line_signatures.add(line_signature)
            
            # 特殊处理：检测和移除逐渐截断的句子
            final_lines = []
            i = 0
            while i < len(filtered_lines):
                current_line = filtered_lines[i]
                
                # 查看后续的行是否是当前行的截断版本
                j = i + 1
                while j < len(filtered_lines):
                    next_line = filtered_lines[j]
                    # 如果下一行是当前行的开始部分且明显更短
                    if current_line.startswith(next_line) and len(next_line) < len(current_line) * 0.9:
                        # 这是一个截断，跳过后续的截断行
                        j += 1
                    else:
                        break
                
                final_lines.append(current_line)
                i = j if j > i + 1 else i + 1
            
            return '\n'.join(final_lines)
            
        except Exception as e:
            print(f"高级重复过滤失败: {e}")
            return text
    
    def is_content_similar(self, content1, content2, threshold=0.95):
        """检查两个内容是否相似"""
        try:
            if not content1 or not content2:
                return False
            
            # 如果完全相同
            if content1 == content2:
                return True
            
            # 如果一个是另一个的子集且差异很小
            shorter = content1 if len(content1) < len(content2) else content2
            longer = content2 if len(content1) < len(content2) else content1
            
            # 如果较短的内容是较长内容的前缀，且长度差异小于5%
            if longer.startswith(shorter) and len(shorter) / len(longer) > threshold:
                return True
            
            return False
            
        except Exception as e:
            print(f"内容相似性检查失败: {e}")
            return False
    
    def reset_streaming_response(self):
        """重置流式响应状态"""
        self.current_streaming_response_type = None
        self.current_streaming_response_line = None
        # 重置响应缓存
        if hasattr(self, '_last_cloud_response'):
            delattr(self, '_last_cloud_response')
        if hasattr(self, '_last_local_response'):
            delattr(self, '_last_local_response')
        if hasattr(self, '_last_audio_response'):
            delattr(self, '_last_audio_response')
        print("重置了流式响应状态")
        
    def on_normal_chat(self):
        """普通聊天"""
        message = self.get_last_user_message()
        if not message:
            messagebox.showwarning("警告", "请先输入消息")
            return
        
        self.status_var.set("正在发送普通请求...")
        self.disable_buttons()
        
        thread = threading.Thread(target=self.normal_chat, args=(message,))
        thread.daemon = True
        thread.start()
        
    def on_upload_audio(self):
        """上传音频文件"""
        # 打开文件选择对话框
        file_types = [
            ("音频文件", "*.wav *.mp3 *.ogg *.m4a *.flac *.aac"),
            ("WAV文件", "*.wav"),
            ("MP3文件", "*.mp3"),
            ("OGG文件", "*.ogg"),
            ("所有文件", "*.*")
        ]
        
        audio_file = filedialog.askopenfilename(
            title="选择音频文件",
            filetypes=file_types
        )
        
        if not audio_file:
            return
        
        # 检查文件大小（限制为50MB）
        try:
            file_size = os.path.getsize(audio_file)
            max_size = 50 * 1024 * 1024  # 50MB
            if file_size > max_size:
                messagebox.showerror("错误", f"文件太大（{file_size / 1024 / 1024:.1f}MB），最大支持50MB")
                return
        except Exception as e:
            messagebox.showerror("错误", f"无法读取文件信息: {e}")
            return
        
        self.append_to_chat(f"📎 正在上传音频文件: {os.path.basename(audio_file)} ({file_size / 1024 / 1024:.1f}MB)", "用户")
        self.status_var.set("正在上传音频文件...")
        self.disable_buttons()
        
        # 在新线程中处理音频上传
        thread = threading.Thread(target=self.upload_audio_file, args=(audio_file,))
        thread.daemon = True
        thread.start()
        
    def upload_audio_file(self, audio_file):
        """上传音频文件到服务器"""
        try:
            url = f"{self.api_base_url}/chat/audio"
            
            print(f"上传音频文件到: {url}")
            print(f"文件路径: {audio_file}")
            
            # 准备文件
            with open(audio_file, 'rb') as f:
                files = {'file': (os.path.basename(audio_file), f, 'audio/*')}
                
                # 发送请求
                response = requests.post(url, files=files, timeout=120, stream=True)  # 启用流式响应
                response.raise_for_status()
                
                print(f"收到响应: {response.status_code}")
                
                # 检查响应类型
                content_type = response.headers.get('content-type', '').lower()
                print(f"响应类型: {content_type}")
                
                if 'application/json' in content_type:
                    # 如果是JSON响应，按原来的方式处理
                    try:
                        data = response.json()
                        print(f"JSON响应数据: {data}")
                        
                        # 提取响应内容
                        transcription = data.get("transcription", "")
                        text_response = data.get("text", "")
                        audio_path = data.get("audio", "")
                        
                        # 更新UI显示转录结果
                        if transcription:
                            self.root.after(0, lambda: self.append_to_chat(f"🎤 语音转录: {transcription}", "系统"))
                        
                        # 显示AI响应
                        if text_response:
                            self.root.after(0, lambda: self.append_to_chat(text_response, "Elysia"))
                        
                        # 播放响应音频
                        if audio_path:
                            self.root.after(0, lambda: self.play_audio_file(audio_path))
                            
                    except json.JSONDecodeError as e:
                        print(f"JSON解析失败: {e}")
                        # 尝试处理为流式响应
                        self.process_audio_streaming_response(response)
                        return
                        
                else:
                    # 处理流式响应
                    print("检测到流式响应，开始处理...")
                    self.process_audio_streaming_response(response)
                    return
                
                self.root.after(0, lambda: self.status_var.set("音频处理完成"))
                
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            print(f"音频上传网络异常: {error_msg}")
            
            # 检查是否是JSON解析错误
            if "Extra data" in error_msg or "JSON" in error_msg:
                print("检测到JSON解析错误，可能是流式响应")
                # 重新尝试作为流式响应处理
                try:
                    self.upload_audio_file_as_stream(audio_file)
                    return
                except Exception as stream_error:
                    print(f"流式处理也失败: {stream_error}")
            
            # 检查是否是超时错误
            if "timeout" in error_msg.lower():
                self.root.after(0, lambda: self.append_to_chat("音频处理超时，请尝试较短的音频文件", "系统"))
            else:
                self.root.after(0, lambda: self.append_to_chat(f"音频上传失败: {error_msg}", "系统"))
                
        except Exception as e:
            error_msg = str(e)
            print(f"音频上传异常: {error_msg}")
            
            # 检查是否是JSON解析错误
            if "Extra data" in error_msg or "JSON" in error_msg:
                print("检测到JSON解析错误，尝试流式处理")
                try:
                    self.upload_audio_file_as_stream(audio_file)
                    return
                except Exception as stream_error:
                    print(f"流式处理也失败: {stream_error}")
            
            self.root.after(0, lambda: self.append_to_chat(f"音频处理失败: {error_msg}", "系统"))
        finally:
            self.root.after(0, self.enable_buttons)
            
    def process_audio_streaming_response(self, response):
        """处理音频上传的流式响应"""
        try:
            print("开始处理音频流式响应...")
            
            # 重置流式响应状态
            self.reset_streaming_response()
            
            current_response = ""
            transcription_shown = False
            
            # 逐行读取流式响应
            for line in response.iter_lines():
                if not line:
                    continue
                    
                line_text = line.decode('utf-8').strip()
                if not line_text:
                    continue
                    
                print(f"收到音频流式数据: {line_text[:100]}...")
                
                try:
                    data = json.loads(line_text)
                    
                    # 处理转录结果
                    if data.get("type") == "transcription" or "transcription" in data:
                        transcription = data.get("transcription", "")
                        if transcription and not transcription_shown:
                            self.root.after(0, lambda t=transcription: self.append_to_chat(f"🎤 语音转录: {t}", "系统"))
                            transcription_shown = True
                    
                    # 处理文本响应
                    elif data.get("type") == "text":
                        content = data.get("content", "")
                        current_response += content
                        
                        # 应用重复检测和清理
                        clean_response = self.advanced_duplicate_filter(current_response)
                        
                        # 检查是否有实质性的内容变化
                        if hasattr(self, '_last_audio_response'):
                            if self.is_content_similar(clean_response, self._last_audio_response):
                                continue
                        
                        current_response = clean_response
                        self._last_audio_response = clean_response
                        
                        # 更新UI
                        response_copy = current_response
                        self.root.after(0, lambda c=response_copy: self.update_current_audio_response(c))
                    
                    # 处理音频流
                    elif data.get("type") == "audio_start":
                        audio_format = data.get("audio_format", "ogg")
                        self.root.after(0, lambda: self.init_streaming_audio(audio_format))
                        
                    elif data.get("type") == "audio_chunk":
                        audio_data = data.get("audio_data", "")
                        chunk_size = data.get("chunk_size", 0)
                        if audio_data:
                            self.root.after(0, lambda ad=audio_data, cs=chunk_size: self.handle_audio_chunk(ad, cs))
                            
                    elif data.get("type") == "audio_end":
                        self.root.after(0, lambda: self.finalize_streaming_audio())
                        
                    elif data.get("type") == "done":
                        self.root.after(0, lambda: self.status_var.set("音频处理完成"))
                        # 确保最终响应格式正确
                        self.root.after(0, lambda: self.finalize_audio_response(current_response))
                        # 重置流式响应状态
                        self.root.after(0, self.reset_streaming_response)
                        break
                        
                    elif data.get("type") == "error":
                        error_msg = data.get("error", "未知错误")
                        self.root.after(0, lambda msg=error_msg: self.append_to_chat(f"音频处理错误: {msg}", "系统"))
                        break
                        
                except json.JSONDecodeError as e:
                    print(f"音频流式JSON解析错误: {e}, 原始数据: {line_text}")
                    continue
                    
        except Exception as e:
            print(f"处理音频流式响应异常: {e}")
            self.root.after(0, lambda: self.append_to_chat(f"处理音频流式响应失败: {e}", "系统"))
    
    def upload_audio_file_as_stream(self, audio_file):
        """使用异步方式上传音频文件并处理流式响应"""
        thread = threading.Thread(target=self.run_async_audio_upload, args=(audio_file,))
        thread.daemon = True
        thread.start()
        
    def run_async_audio_upload(self, audio_file):
        """在新线程中运行异步音频上传"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.audio_upload_async(audio_file))
        finally:
            loop.close()
            
    async def audio_upload_async(self, audio_file):
        """异步音频上传和流式响应处理"""
        try:
            # 设置连接参数
            connector = aiohttp.TCPConnector(
                limit_per_host=100,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(total=120)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                read_bufsize=2*1024*1024,
                max_line_size=10*1024*1024,
                max_field_size=10*1024*1024
            ) as session:
                url = f"{self.api_base_url}/chat/audio"
                
                print(f"异步上传音频文件到: {url}")
                print(f"文件路径: {audio_file}")
                
                # 准备文件数据
                with open(audio_file, 'rb') as f:
                    file_data = aiohttp.FormData()
                    file_data.add_field('file', f, filename=os.path.basename(audio_file), content_type='audio/*')
                    
                    async with session.post(url, data=file_data) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            self.root.after(0, lambda: self.append_to_chat(f"音频上传错误: {error_text}", "系统"))
                            return
                        
                        print(f"收到异步音频响应: {response.status}")
                        
                        # 重置流式响应状态
                        self.root.after(0, self.reset_streaming_response)
                        
                        current_response = ""
                        transcription_shown = False
                        
                        # 使用 content.readline() 读取流式数据
                        while True:
                            try:
                                line = await response.content.readline()
                                if not line:
                                    break
                                    
                                line_text = line.decode('utf-8').strip()
                                if not line_text:
                                    continue
                                    
                                print(f"收到异步音频数据: {line_text[:100]}...")
                                
                                try:
                                    data = json.loads(line_text)
                                    
                                    # 处理转录结果
                                    if data.get("type") == "transcription" or "transcription" in data:
                                        transcription = data.get("transcription", "")
                                        if transcription and not transcription_shown:
                                            self.root.after(0, lambda t=transcription: self.append_to_chat(f"🎤 语音转录: {t}", "系统"))
                                            transcription_shown = True
                                    
                                    # 处理文本响应
                                    elif data.get("type") == "text":
                                        content = data.get("content", "")
                                        current_response += content
                                        
                                        # 应用重复检测和清理
                                        clean_response = self.advanced_duplicate_filter(current_response)
                                        
                                        # 检查是否有实质性的内容变化
                                        if hasattr(self, '_last_audio_response'):
                                            if self.is_content_similar(clean_response, self._last_audio_response):
                                                continue
                                        
                                        current_response = clean_response
                                        self._last_audio_response = clean_response
                                        
                                        # 更新UI
                                        response_copy = current_response
                                        self.root.after(0, lambda c=response_copy: self.update_current_audio_response(c))
                                    
                                    # 处理音频流
                                    elif data.get("type") == "audio_start":
                                        audio_format = data.get("audio_format", "ogg")
                                        self.root.after(0, lambda: self.init_streaming_audio(audio_format))
                                        
                                    elif data.get("type") == "audio_chunk":
                                        audio_data = data.get("audio_data", "")
                                        chunk_size = data.get("chunk_size", 0)
                                        if audio_data:
                                            self.root.after(0, lambda ad=audio_data, cs=chunk_size: self.handle_audio_chunk(ad, cs))
                                            
                                    elif data.get("type") == "audio_end":
                                        self.root.after(0, lambda: self.finalize_streaming_audio())
                                        
                                    elif data.get("type") == "done":
                                        self.root.after(0, lambda: self.status_var.set("音频处理完成"))
                                        # 确保最终响应格式正确
                                        self.root.after(0, lambda: self.finalize_audio_response(current_response))
                                        # 重置流式响应状态
                                        self.root.after(0, self.reset_streaming_response)
                                        break
                                        
                                    elif data.get("type") == "error":
                                        error_msg = data.get("error", "未知错误")
                                        self.root.after(0, lambda msg=error_msg: self.append_to_chat(f"音频处理错误: {msg}", "系统"))
                                        break
                                        
                                except json.JSONDecodeError as e:
                                    print(f"异步音频JSON解析错误: {e}, 原始数据: {line_text}")
                                    continue
                                    
                            except Exception as line_error:
                                print(f"异步音频读取行错误: {line_error}")
                                break
                                
        except Exception as e:
            error_msg = str(e)
            print(f"异步音频上传异常: {error_msg}")
            self.root.after(0, lambda: self.append_to_chat(f"异步音频上传失败: {error_msg}", "系统"))
        finally:
            self.root.after(0, self.enable_buttons)
    
    def update_current_audio_response(self, response):
        """更新当前音频响应显示"""
        try:
            print(f"更新音频响应，长度: {len(response)} 字符")
            print(f"响应前50个字符: {response[:50]}...")
            
            # 如果这是第一次更新，创建新的响应行
            if self.current_streaming_response_type != "audio" or self.current_streaming_response_line is None:
                # 添加新的音频响应行
                timestamp = datetime.now().strftime("%H:%M:%S")
                new_content = f"[{timestamp}] 🎤Elysia: {response}\n"
                self.chat_display.insert(tk.END, new_content)
                
                # 记录当前流式响应信息
                self.current_streaming_response_type = "audio"
                # 获取刚插入行的行号
                content = self.chat_display.get("1.0", tk.END)
                lines = content.strip().split('\n')
                self.current_streaming_response_line = len(lines) - 1
                print(f"创建了新的音频响应行: {self.current_streaming_response_line}")
            else:
                # 更新现有的响应行
                line_start = f"{self.current_streaming_response_line + 1}.0"
                line_end = f"{self.current_streaming_response_line + 1}.end"
                
                # 删除旧的响应行内容
                self.chat_display.delete(line_start, line_end)
                
                # 插入新的完整响应
                timestamp = datetime.now().strftime("%H:%M:%S")
                new_content = f"[{timestamp}] 🎤Elysia: {response}"
                self.chat_display.insert(line_start, new_content)
                print(f"更新了第{self.current_streaming_response_line + 1}行的音频响应")
            
            # 确保滚动到最新内容
            self.chat_display.see(tk.END)
            
        except Exception as e:
            print(f"更新音频响应失败: {e}")
            self.append_to_chat(f"显示更新错误: {str(e)}", "系统")
    
    def finalize_audio_response(self, final_response):
        """完成音频响应，确保格式正确"""
        try:
            if not final_response.strip():
                return
            
            # 应用最终的重复内容清理
            clean_final_response = self.advanced_duplicate_filter(final_response)
            
            # 获取当前聊天内容
            content = self.chat_display.get("1.0", tk.END)
            lines = content.strip().split('\n')
            
            # 查找最后一个音频响应并确保格式正确
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip() and "🎤Elysia:" in lines[i]:
                    current_line = lines[i]
                    # 检查响应是否需要清理
                    if self.needs_content_cleanup(current_line):
                        # 清理并重新写入正确的响应
                        line_start = f"{i + 1}.0"
                        line_end = f"{i + 1}.end"
                        self.chat_display.delete(line_start, line_end)
                        
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        new_content = f"[{timestamp}] 🎤Elysia: {clean_final_response}"
                        self.chat_display.insert(line_start, new_content)
                        print("清理并修复了音频响应格式")
                    break
                    
        except Exception as e:
            print(f"完成音频响应处理失败: {e}")
        
    def normal_chat(self, message):
        """普通聊天请求"""
        try:
            url = f"{self.api_base_url}/chat/text"
            payload = {"message": message, "user_id": "test_user"}
            
            print(f"发送请求到: {url}")
            print(f"payload: {payload}")
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            print(f"收到响应: {response.status_code}")
            
            data = response.json()
            text_response = data.get("text", "")
            audio_path = data.get("audio", "")
            
            print(f"响应数据: {data}")
            
            # 更新UI
            self.root.after(0, lambda: self.append_to_chat(text_response, "Elysia"))
            
            # 播放音频文件
            if audio_path:
                self.root.after(0, lambda: self.play_audio_file(audio_path))
                
            self.root.after(0, lambda: self.status_var.set("响应完成"))
            
        except Exception as e:
            print(f"普通聊天异常: {e}")
            error_msg = str(e)
            self.root.after(0, lambda: self.append_to_chat(f"普通聊天失败: {error_msg}", "系统"))
        finally:
            self.root.after(0, self.enable_buttons)
            
    def on_show_history(self):
        """显示聊天历史"""
        self.status_var.set("正在获取历史记录...")
        
        thread = threading.Thread(target=self.show_history)
        thread.daemon = True
        thread.start()
        
    def show_history(self):
        """获取并显示历史记录"""
        try:
            url = f"{self.api_base_url}/chat/show_history"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            history = response.json()
            
            self.root.after(0, lambda: self.append_to_chat("=== 聊天历史 ===", "系统"))
            for record in history:
                self.root.after(0, lambda r=record: self.append_to_chat(r, "历史"))
            self.root.after(0, lambda: self.append_to_chat("=== 历史结束 ===", "系统"))
            
            self.root.after(0, lambda: self.status_var.set("历史记录获取完成"))
            
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self.append_to_chat(f"获取历史失败: {error_msg}", "系统"))
            
    def on_clear_chat(self):
        """清空聊天记录"""
        self.chat_display.delete("1.0", tk.END)
        self.status_var.set("聊天记录已清空")
        
    def get_last_user_message(self):
        """获取最后一条用户消息"""
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
        
    def play_audio_file(self, audio_path):
        """播放音频文件"""
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            
            self.append_to_chat(f"🎵 播放音频: {audio_path}", "系统")
            
        except Exception as e:
            self.append_to_chat(f"音频播放失败: {str(e)}", "系统")
    
    def init_streaming_audio(self, audio_format="ogg"):
        """初始化流式音频播放"""
        try:
            print(f"初始化流式音频播放，格式: {audio_format}")
            
            # 清空音频缓冲区和重置状态
            self.audio_buffer = bytearray()
            self.audio_playing = False
            
            # 创建临时文件用于流式写入
            timestamp = int(time.time() * 1000)
            temp_dir = tempfile.gettempdir()
            
            # 根据格式选择文件扩展名
            if audio_format.lower() == "ogg":
                file_extension = ".ogg"
            elif audio_format.lower() == "wav":
                file_extension = ".wav"
            else:
                file_extension = ".ogg"  # 默认使用ogg
            
            self.current_audio_file = os.path.join(temp_dir, f"elysia_stream_{timestamp}{file_extension}")
            print(f"创建流式音频文件: {self.current_audio_file}")
            
            # 添加到临时文件列表
            self.temp_audio_files.append(self.current_audio_file)
            
            self.append_to_chat("🎵 开始接收流式音频...", "系统")
            
        except Exception as e:
            print(f"初始化流式音频失败: {e}")
            self.append_to_chat(f"初始化流式音频失败: {e}", "系统")
    
    def handle_audio_chunk(self, audio_data_base64, chunk_size):
        """处理音频流块"""
        try:
            # 解码音频数据
            audio_chunk = base64.b64decode(audio_data_base64)
            
            # 验证chunk大小
            if len(audio_chunk) != chunk_size:
                print(f"警告: 音频块大小不匹配，期望{chunk_size}，实际{len(audio_chunk)}")
            
            # 添加到缓冲区
            self.audio_buffer.extend(audio_chunk)
            
            # 如果有当前音频文件，追加写入
            if self.current_audio_file:
                try:
                    # 只有在还没开始播放时才写入文件
                    if not self.audio_playing:
                        with open(self.current_audio_file, 'ab') as f:
                            f.write(audio_chunk)
                        
                        print(f"写入音频块: {len(audio_chunk)} 字节，总大小: {len(self.audio_buffer)} 字节")
                        
                        # 更新状态
                        self.status_var.set(f"接收音频数据: {len(self.audio_buffer)} 字节")
                        
                        # 检查是否可以开始播放（当缓冲区达到一定大小时）
                        # 注意：一旦开始播放，我们就不再写入文件，而是将数据保存在内存中
                        if len(self.audio_buffer) >= 16384:  # 16KB缓冲，给更多数据再播放
                            try:
                                # 尝试播放当前的部分音频
                                self.try_start_streaming_playback()
                            except Exception as play_error:
                                print(f"尝试流式播放失败: {play_error}")
                    else:
                        # 如果已经开始播放，只更新状态和缓冲区
                        print(f"音频播放中，继续缓冲: {len(audio_chunk)} 字节，总大小: {len(self.audio_buffer)} 字节")
                        self.status_var.set(f"播放中，继续接收: {len(self.audio_buffer)} 字节")
                    
                except Exception as write_error:
                    print(f"写入音频块失败: {write_error}")
                    # 如果写入失败，可能是文件被锁定，继续缓冲
                    if not self.audio_playing:
                        print("文件可能被锁定，暂停写入")
            
        except Exception as e:
            print(f"处理音频块失败: {e}")
            self.append_to_chat(f"处理音频块失败: {e}", "系统")
    
    def try_start_streaming_playback(self):
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
                self.append_to_chat("🎵 开始流式播放...", "系统")
                print("流式播放已开始")
            except Exception as e:
                print(f"pygame流式播放失败: {e}")
                # 如果pygame失败，我们继续等待更多数据
                
        except Exception as e:
            print(f"尝试流式播放异常: {e}")
    
    def finalize_streaming_audio(self):
        """完成流式音频播放"""
        try:
            print(f"完成流式音频接收，总大小: {len(self.audio_buffer)} 字节")
            
            # 如果还没开始播放，或者需要播放完整版本
            if not self.audio_playing or len(self.audio_buffer) > 0:
                # 创建完整的音频文件
                timestamp = int(time.time() * 1000)
                temp_dir = tempfile.gettempdir()
                complete_audio_file = os.path.join(temp_dir, f"elysia_complete_{timestamp}.ogg")
                
                try:
                    # 将完整的缓冲区写入新文件
                    with open(complete_audio_file, 'wb') as f:
                        f.write(self.audio_buffer)
                    
                    print(f"创建完整音频文件: {complete_audio_file}")
                    file_size = os.path.getsize(complete_audio_file)
                    print(f"完整音频文件大小: {file_size} 字节")
                    
                    if file_size > 0:
                        self.append_to_chat(f"🎵 播放完整流式音频 ({file_size} 字节)", "系统")
                        
                        # 停止当前播放（如果有的话）
                        try:
                            pygame.mixer.music.stop()
                        except:
                            pass
                        
                        # 播放完整版本
                        success = False
                        
                        # 方法1: pygame播放
                        try:
                            print(f"尝试pygame播放完整版本: {complete_audio_file}")
                            pygame.mixer.music.load(complete_audio_file)
                            pygame.mixer.music.play()
                            self.append_to_chat("🎵 完整音频播放中... (pygame)", "系统")
                            success = True
                        except Exception as e:
                            print(f"pygame播放完整版本失败: {e}")
                        
                        # 方法2: 系统播放器
                        if not success:
                            try:
                                if platform.system() == "Windows":
                                    print(f"尝试系统播放器播放完整版本: {complete_audio_file}")
                                    os.startfile(complete_audio_file)
                                    self.append_to_chat("🎵 完整音频播放中... (系统播放器)", "系统")
                                    success = True
                            except Exception as e:
                                print(f"系统播放器播放完整版本失败: {e}")
                        
                        if success:
                            self.append_to_chat(f"📁 完整音频文件: {complete_audio_file}", "系统")
                            self.temp_audio_files.append(complete_audio_file)
                        else:
                            self.append_to_chat(f"🎵 自动播放失败，请手动播放: {complete_audio_file}", "系统")
                        
                        # 设置延迟清理（60秒后清理，给播放留出时间）
                        def cleanup_complete_audio():
                            try:
                                if os.path.exists(complete_audio_file):
                                    os.unlink(complete_audio_file)
                                    print(f"清理完整音频文件: {complete_audio_file}")
                                    if complete_audio_file in self.temp_audio_files:
                                        self.temp_audio_files.remove(complete_audio_file)
                            except Exception as e:
                                print(f"清理完整音频文件失败: {e}")
                        
                        self.root.after(60000, cleanup_complete_audio)  # 60秒后清理
                        
                    else:
                        self.append_to_chat("❌ 完整音频文件为空", "系统")
                        
                except Exception as create_error:
                    print(f"创建完整音频文件失败: {create_error}")
                    self.append_to_chat(f"创建完整音频文件失败: {create_error}", "系统")
            
            # 清理流式音频文件（如果存在且没被锁定）
            if self.current_audio_file:
                try:
                    if os.path.exists(self.current_audio_file):
                        # 延迟清理流式文件，避免播放冲突
                        def cleanup_streaming_file():
                            try:
                                if self.current_audio_file and os.path.exists(self.current_audio_file):
                                    os.unlink(self.current_audio_file)
                                    print(f"清理流式音频文件: {self.current_audio_file}")
                                    if self.current_audio_file in self.temp_audio_files:
                                        self.temp_audio_files.remove(self.current_audio_file)
                            except Exception as e:
                                print(f"清理流式音频文件失败: {e}")
                        
                        self.root.after(30000, cleanup_streaming_file)  # 30秒后清理流式文件
                        
                except Exception as e:
                    print(f"处理流式文件清理失败: {e}")
            
            # 重置状态
            self.current_audio_file = None
            self.audio_buffer = bytearray()
            self.audio_playing = False
            self.status_var.set("流式音频处理完成")
            
        except Exception as e:
            print(f"完成流式音频失败: {e}")
            self.append_to_chat(f"完成流式音频失败: {e}", "系统")
    
    def cleanup_temp_files(self):
        """清理所有临时音频文件"""
        try:
            for temp_file in self.temp_audio_files[:]:  # 使用切片复制避免迭代时修改
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                        print(f"清理临时文件: {temp_file}")
                    self.temp_audio_files.remove(temp_file)
                except Exception as e:
                    print(f"清理临时文件失败 {temp_file}: {e}")
        except Exception as e:
            print(f"清理临时文件总体失败: {e}")
            
    def on_closing(self):
        """窗口关闭事件处理"""
        try:
            # 清理临时文件
            self.cleanup_temp_files()
            # 停止音频播放
            pygame.mixer.music.stop()
        except Exception as e:
            print(f"关闭清理失败: {e}")
        finally:
            self.root.destroy()
            
    def disable_buttons(self):
        """禁用按钮"""
        self.stream_button.configure(state="disabled")
        self.cloud_button.configure(state="disabled")
        self.normal_button.configure(state="disabled")
        self.audio_button.configure(state="disabled")
        self.send_button.configure(state="disabled")
        
    def enable_buttons(self):
        """启用按钮"""
        self.stream_button.configure(state="normal")
        self.cloud_button.configure(state="normal")
        self.normal_button.configure(state="normal")
        self.audio_button.configure(state="normal")
        self.send_button.configure(state="normal")
        
    def run(self):
        """运行客户端"""
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

if __name__ == "__main__":
    # 检查依赖
    try:
        import pygame
        import aiohttp
    except ImportError as e:
        print(f"缺少依赖包: {e}")
        print("请运行以下命令安装依赖:")
        print("pip install pygame aiohttp")
        exit(1)
    
    client = ElysiaClient()
    client.run()