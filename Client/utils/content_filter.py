"""
内容过滤和处理工具
处理重复内容检测、文本清理等
"""

from typing import Set, Optional
from core.config import Config


class ContentFilter:
    """内容过滤器 - 针对流式输出优化"""
    
    # 常量定义，避免硬编码
    SIMILARITY_THRESHOLD_HIGH = 0.9  # 高相似度阈值
    SIMILARITY_THRESHOLD_MEDIUM = 0.7  # 中等相似度阈值
    MIN_CHECK_LENGTH = 20  # 重复检查的最小长度
    
    @staticmethod
    def process_streaming_chunk(new_chunk: str, accumulated_text: str) -> str:
        """处理流式输出的新块（针对真正的流式输出优化）"""
        try:
            if not new_chunk:
                return new_chunk
            
            # 对于真正的流式输出，通常不需要复杂的去重
            # 只需要做基本的清理
            
            # 1. 移除可能的控制字符
            cleaned_chunk = ''.join(char for char in new_chunk if ord(char) >= 32 or char in '\n\r\t')
            
            # 2. 检查是否是明显的重复（比如服务器错误发送了相同内容）
            if len(accumulated_text) > 20:  # 只在有足够内容时检查
                recent_text = accumulated_text[-20:]  # 检查最近20个字符
                if cleaned_chunk in recent_text:
                    print(f"检测到可能的重复chunk: {cleaned_chunk}")
                    return ""  # 跳过明显重复的chunk
            
            return cleaned_chunk
            
        except Exception as e:
            print(f"处理流式chunk失败: {e}")
            return new_chunk
    
    @staticmethod
    def advanced_duplicate_filter(text: str) -> str:
        """高级重复内容过滤器"""
        try:
            if not text.strip():
                return text
            
            # 首先移除逐渐截断（这是主要问题）
            cleaned_text = ContentFilter.remove_progressive_truncation(text)
            
            # 然后做行级去重
            lines = cleaned_text.split('\n')
            unique_lines = []
            seen_signatures = set()
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 创建行的唯一签名（去除标点和空格后的前40个字符）
                signature = ''.join(c for c in line if c.isalnum() or c.isspace())[:40].strip()
                
                # 检查是否已经有相似的行
                is_duplicate = False
                for existing_sig in seen_signatures:
                    # 如果两个签名非常相似（使用高相似度阈值）
                    if ContentFilter._signature_similarity(signature, existing_sig) > ContentFilter.SIMILARITY_THRESHOLD_HIGH:
                        is_duplicate = True
                        break
                
                if not is_duplicate and signature:
                    unique_lines.append(line)
                    seen_signatures.add(signature)
            
            return '\n'.join(unique_lines)
            
        except Exception as e:
            print(f"高级重复过滤失败: {e}")
            return text
    
    @staticmethod
    def _calculate_similarity(str1: str, str2: str, normalize: bool = False) -> float:
        """统一的相似度计算方法"""
        try:
            if not str1 or not str2:
                return 0.0
            
            # 如果需要标准化（用于内容比较）
            if normalize:
                str1 = ''.join(c for c in str1.lower() if c.isalnum())
                str2 = ''.join(c for c in str2.lower() if c.isalnum())
                if not str1 or not str2:
                    return 0.0
            
            # 检查前缀匹配
            shorter = str1 if len(str1) < len(str2) else str2
            longer = str2 if len(str1) < len(str2) else str1
            
            if longer.startswith(shorter) or (not normalize and longer.endswith(shorter)):
                return len(shorter) / len(longer)
            
            # 计算最长公共前缀
            common_prefix = 0
            for i in range(min(len(str1), len(str2))):
                if str1[i] == str2[i]:
                    common_prefix += 1
                else:
                    break
            
            return common_prefix / max(len(str1), len(str2))
            
        except Exception as e:
            print(f"计算相似度失败: {e}")
            return 0.0
    
    @staticmethod
    def _signature_similarity(sig1: str, sig2: str) -> float:
        """计算两个签名的相似度（保留用于签名特定逻辑）"""
        return ContentFilter._calculate_similarity(sig1, sig2, normalize=False)
    
    @staticmethod
    def remove_progressive_truncation(text: str) -> str:
        """移除逐渐截断的文本（主要问题的核心修复）"""
        try:
            lines = text.split('\n')
            if len(lines) <= 1:
                return text
            
            # 先将所有行按内容分组
            content_groups = {}
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # 提取内容的核心部分（去除特殊字符，只保留主要文字）
                core_content = ''.join(c for c in line if c.isalnum() or c.isspace()).strip()
                if not core_content:
                    continue
                
                # 找到匹配的组（基于内容相似性）
                matched_group = None
                for existing_core in content_groups:
                    # 检查是否是同一内容的不同版本
                    if (core_content.startswith(existing_core[:ContentFilter.MIN_CHECK_LENGTH]) or 
                        existing_core.startswith(core_content[:ContentFilter.MIN_CHECK_LENGTH]) or
                        ContentFilter._calculate_similarity(core_content, existing_core, normalize=True) > ContentFilter.SIMILARITY_THRESHOLD_MEDIUM):
                        matched_group = existing_core
                        break
                
                if matched_group:
                    # 添加到现有组，保留最完整的版本
                    current_best = content_groups[matched_group]
                    if len(line) > len(current_best):
                        # 新行更完整，替换
                        del content_groups[matched_group]
                        content_groups[core_content] = line
                    # 否则保持原有的最佳版本
                else:
                    # 创建新组
                    content_groups[core_content] = line
            
            # 返回每组中最完整的版本
            result_lines = list(content_groups.values())
            
            # 最后排序以保持相对顺序
            return '\n'.join(result_lines)
            
        except Exception as e:
            print(f"移除逐渐截断失败: {e}")
            return text
