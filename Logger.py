"""
    负责产生一个Logger并将其返回
"""

import os
import logging
from logging.handlers import TimedRotatingFileHandler

def setup_logger(name: str)->logging.Logger:
    """
    配置并返回一个日志记录器
    """
    # TODO 将来支持自定义
    log_path: str = "/home/yomu/Elysia/Log"
    os.makedirs(log_path, exist_ok=True) 
    
    # 创建日志处理器
    file_handler = TimedRotatingFileHandler(f"{log_path}/logger_{name}.log", when="midnight", interval=1, encoding="utf-8")
    file_handler.suffix = "%Y-%m-%d"
    
    # 创建日志格式
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(logging.StreamHandler())  # 控制台输出

    return logger

