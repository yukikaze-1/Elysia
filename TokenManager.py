import re
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

class TokenManager:
    """Token 计数管理器 - 支持持久化"""
    
    def __init__(self, data_file: str = "token_stats.json"):
        """
        初始化 TokenManager
        
        Args:
            data_file: 持久化数据文件路径
        """
        self.data_file = data_file
        
        # 初始化默认值
        self._init_default_values()
        
        # 尝试加载持久化数据
        self._load_from_file()
        
        
    def _init_default_values(self):
        """初始化默认值"""
        # 本地模型统计
        self.local_total_input_tokens = 0
        self.local_total_output_tokens = 0
        self.local_total_tokens = 0
        self.local_session_input_tokens = 0
        self.local_session_output_tokens = 0
        self.local_session_total_tokens = 0
        
        # 云端模型统计
        self.cloud_total_input_tokens = 0
        self.cloud_total_output_tokens = 0
        self.cloud_total_tokens = 0
        self.cloud_session_input_tokens = 0
        self.cloud_session_output_tokens = 0
        self.cloud_session_total_tokens = 0
        
        # 总体统计（本地+云端）
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.session_input_tokens = 0
        self.session_output_tokens = 0
        self.session_total_tokens = 0
        
        # 统计开始时间
        self.start_time = datetime.now()
        
        # 持久化相关
        self.last_save_time = datetime.now()
        self.auto_save_interval = 60  # 自动保存间隔（秒）
        
    def _load_from_file(self):
        """从文件加载持久化数据"""
        if not os.path.exists(self.data_file):
            print(f"Token统计文件 {self.data_file} 不存在，使用默认值")
            return
            
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 加载本地模型统计
            local_stats = data.get('local_stats', {})
            self.local_total_input_tokens = local_stats.get('input_tokens', 0)
            self.local_total_output_tokens = local_stats.get('output_tokens', 0)
            self.local_total_tokens = local_stats.get('total_tokens', 0)
            
            # 加载云端模型统计
            cloud_stats = data.get('cloud_stats', {})
            self.cloud_total_input_tokens = cloud_stats.get('input_tokens', 0)
            self.cloud_total_output_tokens = cloud_stats.get('output_tokens', 0)
            self.cloud_total_tokens = cloud_stats.get('total_tokens', 0)
            
            # 计算总体统计
            self._update_total_stats()
            
            # 加载时间信息
            runtime_info = data.get('runtime_info', {})
            if runtime_info.get('start_time'):
                try:
                    self.start_time = datetime.fromisoformat(runtime_info['start_time'])
                except:
                    self.start_time = datetime.now()
            
            print(f"成功加载Token统计数据:")
            print(f"  本地模型: {self.local_total_tokens} tokens")
            print(f"  云端模型: {self.cloud_total_tokens} tokens")
            print(f"  总计: {self.total_tokens} tokens")
            
        except Exception as e:
            print(f"加载Token统计文件失败: {e}")
            print("使用默认值重新开始")
            
    def _save_to_file(self):
        """保存数据到文件"""
        try:
            data = {
                "local_stats": {
                    "input_tokens": self.local_total_input_tokens,
                    "output_tokens": self.local_total_output_tokens,
                    "total_tokens": self.local_total_tokens
                },
                "cloud_stats": {
                    "input_tokens": self.cloud_total_input_tokens,
                    "output_tokens": self.cloud_total_output_tokens,
                    "total_tokens": self.cloud_total_tokens
                },
                "total_stats": {
                    "input_tokens": self.total_input_tokens,
                    "output_tokens": self.total_output_tokens,
                    "total_tokens": self.total_tokens
                },
                "session_stats": {
                    "local": {
                        "input_tokens": self.local_session_input_tokens,
                        "output_tokens": self.local_session_output_tokens,
                        "total_tokens": self.local_session_total_tokens
                    },
                    "cloud": {
                        "input_tokens": self.cloud_session_input_tokens,
                        "output_tokens": self.cloud_session_output_tokens,
                        "total_tokens": self.cloud_session_total_tokens
                    },
                    "total": {
                        "input_tokens": self.session_input_tokens,
                        "output_tokens": self.session_output_tokens,
                        "total_tokens": self.session_total_tokens
                    }
                },
                "runtime_info": {
                    "start_time": self.start_time.isoformat(),
                    "last_save_time": datetime.now().isoformat(),
                },
                "metadata": {
                    "version": "2.0",
                    "description": "Elysia Token Statistics with Local/Cloud Separation",
                    "auto_save_interval": self.auto_save_interval
                }
            }
            
            # 先写入临时文件，再重命名，避免写入过程中程序崩溃导致数据丢失
            temp_file = self.data_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            # 原子性重命名
            os.replace(temp_file, self.data_file)
            self.last_save_time = datetime.now()
            
        except Exception as e:
            print(f"保存Token统计文件失败: {e}")
            
    def _update_total_stats(self):
        """更新总体统计"""
        self.total_input_tokens = self.local_total_input_tokens + self.cloud_total_input_tokens
        self.total_output_tokens = self.local_total_output_tokens + self.cloud_total_output_tokens
        self.total_tokens = self.local_total_tokens + self.cloud_total_tokens
        
        self.session_input_tokens = self.local_session_input_tokens + self.cloud_session_input_tokens
        self.session_output_tokens = self.local_session_output_tokens + self.cloud_session_output_tokens
        self.session_total_tokens = self.local_session_total_tokens + self.cloud_session_total_tokens
    
    def add_local_input_tokens(self, input_tokens: int) -> int:
        """添加本地模型输入 token 统计"""
        self.local_total_input_tokens += input_tokens
        self.local_total_tokens += input_tokens
        self.local_session_input_tokens += input_tokens
        self.local_session_total_tokens += input_tokens
        self._update_total_stats()
        return input_tokens

    def add_local_streaming_output_tokens(self, chunk_tokens: int) -> int:
        """本地模型流式输出时，逐步累加 output tokens"""
        self.local_total_output_tokens += chunk_tokens
        self.local_total_tokens += chunk_tokens
        self.local_session_output_tokens += chunk_tokens
        self.local_session_total_tokens += chunk_tokens
        self._update_total_stats()
        return chunk_tokens

    def add_cloud_input_tokens(self, input_tokens: int) -> int:
        """添加云端模型输入 token 统计"""
        self.cloud_total_input_tokens += input_tokens
        self.cloud_total_tokens += input_tokens
        self.cloud_session_input_tokens += input_tokens
        self.cloud_session_total_tokens += input_tokens
        self._update_total_stats()
        return input_tokens

    def add_cloud_streaming_output_tokens(self, chunk_tokens: int) -> int:
        """云端模型流式输出时，逐步累加 output tokens"""
        self.cloud_total_output_tokens += chunk_tokens
        self.cloud_total_tokens += chunk_tokens
        self.cloud_session_output_tokens += chunk_tokens
        self.cloud_session_total_tokens += chunk_tokens
        self._update_total_stats()
        return chunk_tokens
    
    def adjust_cloud_tokens_with_usage(self, estimated_input: int, estimated_output: int, 
                                      actual_input: int, actual_output: int):
        """使用云端API返回的准确token数调整统计"""
        # 调整累计统计
        input_diff = actual_input - estimated_input
        output_diff = actual_output - estimated_output
        
        self.cloud_total_input_tokens += input_diff
        self.cloud_total_output_tokens += output_diff
        self.cloud_total_tokens += (input_diff + output_diff)
        
        self.cloud_session_input_tokens += input_diff
        self.cloud_session_output_tokens += output_diff
        self.cloud_session_total_tokens += (input_diff + output_diff)
        
        self._update_total_stats()
     
    def get_current_stats(self) -> Dict[str, Any]:
        """获取当前的统计信息"""
        runtime = datetime.now() - self.start_time
        
        return {
            "local_stats": {
                "input_tokens": self.local_total_input_tokens,
                "output_tokens": self.local_total_output_tokens,
                "total_tokens": self.local_total_tokens
            },
            "cloud_stats": {
                "input_tokens": self.cloud_total_input_tokens,
                "output_tokens": self.cloud_total_output_tokens,
                "total_tokens": self.cloud_total_tokens
            },
            "total_stats": {
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
                "total_tokens": self.total_tokens
            },
            "session_stats": {
                "local": {
                    "input_tokens": self.local_session_input_tokens,
                    "output_tokens": self.local_session_output_tokens,
                    "total_tokens": self.local_session_total_tokens
                },
                "cloud": {
                    "input_tokens": self.cloud_session_input_tokens,
                    "output_tokens": self.cloud_session_output_tokens,
                    "total_tokens": self.cloud_session_total_tokens
                },
                "total": {
                    "input_tokens": self.session_input_tokens,
                    "output_tokens": self.session_output_tokens,
                    "total_tokens": self.session_total_tokens
                }
            },
            "runtime_info": {
                "start_time": self.start_time.isoformat(),
                "runtime_seconds": int(runtime.total_seconds()),
                "last_save_time": self.last_save_time.isoformat()
            },
            "efficiency": {
                "total_tokens_per_second": round(self.total_tokens / max(runtime.total_seconds(), 1), 2),
                "local_tokens_per_second": round(self.local_total_tokens / max(runtime.total_seconds(), 1), 2),
                "cloud_tokens_per_second": round(self.cloud_total_tokens / max(runtime.total_seconds(), 1), 2)
            }
        }
        
    # 保持向后兼容的方法
    def add_input_tokens(self, input_text: str) -> int:
        """向后兼容方法 - 计算token并添加到本地模型统计"""
        input_tokens = self.count_tokens_approximate(input_text)
        return self.add_local_input_tokens(input_tokens)

    def add_streaming_output_tokens(self, chunk_text: str) -> int:
        """向后兼容方法 - 计算token并添加到本地模型统计"""
        chunk_tokens = self.count_tokens_approximate(chunk_text)
        return self.add_local_streaming_output_tokens(chunk_tokens)
            
    def _auto_save_if_needed(self):
        """如果需要，自动保存数据"""
        time_since_save = (datetime.now() - self.last_save_time).total_seconds()
        print(f"距离上次保存: {time_since_save:.1f}秒, 自动保存间隔: {self.auto_save_interval}秒")
        
        if time_since_save > self.auto_save_interval:
            print("触发自动保存...")
            self._save_to_file()
        else:
            print(f"还需等待 {self.auto_save_interval - time_since_save:.1f}秒 后自动保存")
    
    def count_tokens_approximate(self, text: str) -> int:
        """
        本地近似计算 token 数量
        对于中文和英文混合文本的粗略估算
        
        Args:
            text: 要计算的文本
            
        Returns:
            估算的 token 数量
        """
        if not text:
            return 0
        
        # 简单的 token 计算规则：
        # 1. 中文字符：每个字符约等于 1 token
        # 2. 英文单词：按空格分割计算
        # 3. 标点符号等：每个约 0.5 token
        
        # 统计中文字符（Unicode范围）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        # 统计英文单词
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        
        # 统计其他字符（标点、数字等）
        other_chars = len(re.sub(r'[\u4e00-\u9fff\s]|[a-zA-Z]+', '', text))
        
        # 粗略计算：中文字符1:1，英文单词按平均长度，其他字符0.5:1
        estimated_tokens = chinese_chars + english_words + (other_chars * 0.5)
        
        return int(estimated_tokens) 
    
    
    def get_turn_usage_info(self, input_tokens: int, output_tokens: int) -> Dict[str, Any]:
        """
        获取单轮对话的使用信息（用于流式响应）
        
        Args:
            input_tokens: 本轮输入 token 数
            output_tokens: 本轮输出 token 数
            
        Returns:
            格式化的使用信息
        """
        return {
            "type": "token_usage",
            "current_turn": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            },
            "session_total": {
                "input_tokens": self.session_input_tokens,
                "output_tokens": self.session_output_tokens,
                "total_tokens": self.session_total_tokens
            },
            "grand_total": {
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
                "total_tokens": self.total_tokens
            }
        }
    
    def reset_session_stats(self):
        """重置会话统计"""
        self.local_session_input_tokens = 0
        self.local_session_output_tokens = 0
        self.local_session_total_tokens = 0
        self.cloud_session_input_tokens = 0
        self.cloud_session_output_tokens = 0
        self.cloud_session_total_tokens = 0
        self._update_total_stats()
        self._save_to_file()
    
    def reset_all_stats(self):
        """重置所有统计"""
        # 重置本地统计
        self.local_total_input_tokens = 0
        self.local_total_output_tokens = 0
        self.local_total_tokens = 0
        self.local_session_input_tokens = 0
        self.local_session_output_tokens = 0
        self.local_session_total_tokens = 0
        
        # 重置云端统计
        self.cloud_total_input_tokens = 0
        self.cloud_total_output_tokens = 0
        self.cloud_total_tokens = 0
        self.cloud_session_input_tokens = 0
        self.cloud_session_output_tokens = 0
        self.cloud_session_total_tokens = 0
        
        # 重置时间
        self.start_time = datetime.now()
        
        # 更新总体统计
        self._update_total_stats()
        
        # 立即保存重置后的状态
        self._save_to_file()
    
    def force_save(self):
        """强制保存当前数据"""
        self._save_to_file()
        
    def export_stats(self, export_file: Optional[str] = None) -> str:
        """
        导出统计数据到指定文件
        
        Args:
            export_file: 导出文件路径，如果为None则使用时间戳命名
            
        Returns:
            导出文件的路径
        """
        if export_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = f"token_stats_export_{timestamp}.json"
        
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(self.get_current_stats(), f, ensure_ascii=False, indent=2)
            print(f"统计数据已导出到: {export_file}")
            return export_file
        except Exception as e:
            print(f"导出统计数据失败: {e}")
            raise
            
    def __del__(self):
        """析构函数，确保数据被保存"""
        try:
            self._save_to_file()
        except:
            pass