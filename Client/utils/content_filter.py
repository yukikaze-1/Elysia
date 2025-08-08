"""
内容过滤和处理工具
处理重复内容检测、文本清理等
"""

from typing import Set, Optional
from core.config import Config


class ContentFilter:
    """内容过滤器 - 针对流式输出优化"""
    
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
    def is_streaming_mode_suitable(response_pattern: str) -> bool:
        """判断是否适合使用流式模式（基于响应模式）"""
        try:
            # 检查是否有明显的重复模式
            lines = response_pattern.split('\n')
            if len(lines) <= 2:
                return True  # 短内容适合流式
            
            # 检查是否有逐渐截断的迹象
            truncation_count = 0
            for i in range(len(lines) - 1):
                current = lines[i].strip()
                next_line = lines[i + 1].strip()
                if current and next_line and current.startswith(next_line) and len(next_line) < len(current) * 0.8:
                    truncation_count += 1
            
            # 如果截断模式很多，说明不适合当前的处理方式
            return truncation_count < len(lines) * 0.3
            
        except Exception as e:
            print(f"判断流式模式适用性失败: {e}")
            return True
    
    @staticmethod
    def remove_immediate_duplicates(text: str) -> str:
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
            seen_content: Set[str] = set()
            
            for line in cleaned_lines:
                # 对于长句子，检查是否已经有相似的内容
                line_key = line[:Config.DUPLICATE_CHECK_LENGTH] if len(line) > Config.DUPLICATE_CHECK_LENGTH else line
                if line_key not in seen_content:
                    final_lines.append(line)
                    seen_content.add(line_key)
            
            return '\n'.join(final_lines)
            
        except Exception as e:
            print(f"移除即时重复失败: {e}")
            return text
    
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
                    # 如果两个签名非常相似（>90%）
                    if ContentFilter._signature_similarity(signature, existing_sig) > 0.9:
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
    def _signature_similarity(sig1: str, sig2: str) -> float:
        """计算两个签名的相似度"""
        try:
            if not sig1 or not sig2:
                return 0.0
            
            # 如果一个是另一个的前缀或后缀
            shorter = sig1 if len(sig1) < len(sig2) else sig2
            longer = sig2 if len(sig1) < len(sig2) else sig1
            
            if longer.startswith(shorter) or longer.endswith(shorter):
                return len(shorter) / len(longer)
            
            # 计算字符级相似度
            common_chars = 0
            for i in range(min(len(sig1), len(sig2))):
                if sig1[i] == sig2[i]:
                    common_chars += 1
                else:
                    break
            
            return common_chars / max(len(sig1), len(sig2))
            
        except Exception as e:
            print(f"计算签名相似度失败: {e}")
            return 0.0
    
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
                    if (core_content.startswith(existing_core[:20]) or 
                        existing_core.startswith(core_content[:20]) or
                        ContentFilter._content_similarity(core_content, existing_core) > 0.7):
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
    
    @staticmethod
    def _content_similarity(content1: str, content2: str) -> float:
        """计算两个内容的相似度"""
        try:
            if not content1 or not content2:
                return 0.0
            
            # 简化内容（只保留字母数字）
            simple1 = ''.join(c for c in content1.lower() if c.isalnum())
            simple2 = ''.join(c for c in content2.lower() if c.isalnum())
            
            if not simple1 or not simple2:
                return 0.0
            
            # 计算最长公共子序列的比例
            shorter = simple1 if len(simple1) < len(simple2) else simple2
            longer = simple2 if len(simple1) < len(simple2) else simple1
            
            if longer.startswith(shorter):
                return len(shorter) / len(longer)
            
            # 计算字符重叠度
            common = 0
            for i in range(min(len(simple1), len(simple2))):
                if simple1[i] == simple2[i]:
                    common += 1
                else:
                    break
            
            return common / max(len(simple1), len(simple2))
            
        except Exception as e:
            print(f"计算内容相似度失败: {e}")
            return 0.0
    
    @staticmethod
    def _calculate_similarity(str1: str, str2: str) -> float:
        """计算两个字符串的相似度"""
        try:
            if not str1 or not str2:
                return 0.0
            
            # 简单的相似度计算：基于公共子串
            shorter = str1 if len(str1) < len(str2) else str2
            longer = str2 if len(str1) < len(str2) else str1
            
            if longer.startswith(shorter):
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
    def is_content_similar(content1: str, content2: str, threshold: Optional[float] = None) -> bool:
        """检查两个内容是否相似"""
        try:
            if threshold is None:
                threshold = Config.SIMILARITY_THRESHOLD
                
            if not content1 or not content2:
                return False
            
            # 如果完全相同
            if content1 == content2:
                return True
            
            # 如果一个是另一个的子集且差异很小
            shorter = content1 if len(content1) < len(content2) else content2
            longer = content2 if len(content1) < len(content2) else content1
            
            # 如果较短的内容是较长内容的前缀，且长度差异小于阈值
            if longer.startswith(shorter) and len(shorter) / len(longer) > threshold:
                return True
            
            return False
            
        except Exception as e:
            print(f"内容相似性检查失败: {e}")
            return False
    
    @staticmethod
    def needs_content_cleanup(line: str) -> bool:
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
