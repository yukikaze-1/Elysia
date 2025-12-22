"""
    负责产生一个Logger并将其返回
"""

import os
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

# 定义默认日志路径，方便修改
DEFAULT_LOG_PATH = "/home/yomu/Elysia/Demo/Log"

def setup_logger(name: str, log_dir: str = DEFAULT_LOG_PATH) -> logging.Logger:
    """
    配置并返回一个日志记录器 (单例模式安全)
    """
    # 1. 获取 logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 2. 【关键】检查是否已经添加过 handler，防止重复打印！
    if logger.handlers:
        return logger

    # 3. 准备目录
    os.makedirs(log_dir, exist_ok=True) 
    
    # 4. 创建统一的格式器 (Formatter)
    # 建议格式：[时间] [日志级别] [模块名]: 消息
    formatter = logging.Formatter(
        fmt="<%(asctime)s> - [%(levelname)s] - {%(name)s}: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S" # 更加可读的时间格式
    )

    # 5. 配置文件处理器 (File Handler)
    log_file = os.path.join(log_dir, f"logger_{name}.log")
    file_handler = TimedRotatingFileHandler(
        log_file, 
        when="midnight", 
        interval=1, 
        encoding="utf-8",
        backupCount=30 # 建议：保留最近30天的日志，防止磁盘占满
    )
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"
    
    # 6. 配置控制台处理器 (Stream Handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter) # 【关键】让控制台也应用同样的格式

    # 7. 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# --- 测试调用 ---
if __name__ == "__main__":
    # 模拟第一次调用
    log1 = setup_logger("L1_BrainLayer")
    log1.info("Brain layer initialized.")

    # 模拟重复调用（例如在其他模块再次 import）
    log2 = setup_logger("L1_BrainLayer") 
    log2.warning("This is a warning.") 
    # 此时控制台应该只显示一行 warning，而不是两行