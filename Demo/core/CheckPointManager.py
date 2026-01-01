
"""
Checkpoint Manager 模块
负责管理系统各模块的状态保存与恢复
"""
import json
import os
import logging
import threading
from typing import Callable, Any, Dict
from config.Config import CheckPointManagerConfig
from Logger import setup_logger

# 定义类型别名，方便阅读
type Getter = Callable[[], Any]
type Setter = Callable[[Any], None]

class CheckPointManager:
    def __init__(self, config: CheckPointManagerConfig):
        
        self.config: CheckPointManagerConfig = config
        self.logger:logging.Logger = setup_logger(self.config.logger_name)
        self.filepath = self.config.checkpoint_file
        self.temp_filepath = self.filepath + ".tmp"
        
        # 注册表：name -> (getter, setter)
        self._handlers: Dict[str, tuple[Getter, Setter]] = {}
        
        # 暂存区：用于存放“已从磁盘读取，但尚未注册”的数据
        self._pending_data: Dict[str, Any] = {}
        
        # 线程锁：防止多线程环境下注册/保存冲突
        self._lock = threading.RLock()
        

    def register(self, name: str, getter: Getter, setter: Setter):
        """
        核心注册方法
        :param name: 模块唯一标识
        :param getter: 调用它能返回可序列化数据
        :param setter: 调用它能接收数据并恢复状态
        """
        with self._lock:
            self._handlers[name] = (getter, setter)
            self.logger.info(f"模块注册成功: {name}")

            # 【关键设计】: 如果暂存区有该模块的数据，立即进行“迟到的恢复”
            if name in self._pending_data:
                try:
                    data = self._pending_data.pop(name)
                    setter(data)
                    self.logger.info(f"模块 {name} 触发延迟恢复")
                except Exception as e:
                    self.logger.error(f"模块 {name} 延迟恢复失败: {e}")


    def save_checkpoint(self):
        """收集所有状态并持久化"""
        data_snapshot = {}
        
        with self._lock:
            # 1. 遍历所有注册者，收集数据
            for name, (getter, _) in self._handlers.items():
                try:
                    state = getter()
                    self.logger.debug(f"收集模块 {name} 状态: {state}")
                    # 可以在这里加一个校验，确保 state 是 JSON 可序列化的
                    data_snapshot[name] = state
                except Exception as e:
                    # 某个模块挂了，不要影响整体保存，记录日志即可
                    self.logger.error(f"获取模块 {name} 状态时出错: {e}")

            # 2. 还要保留那些“未注册但存在于暂存区”的数据
            # 防止：上次存了模块C，这次程序运行C还没初始化就保存了，导致C的数据丢失
            for name, data in self._pending_data.items():
                if name not in data_snapshot:
                    data_snapshot[name] = data

        # 3. 原子写入磁盘 (无锁操作 IO)
        try:
            with open(self.temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(data_snapshot, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(self.temp_filepath, self.filepath)
            self.logger.info(f"检查点保存完毕，共 {len(data_snapshot)} 个模块:{list(data_snapshot.keys())}")
        except Exception as e:
            self.logger.error(f"保存文件失败: {e}")


    def load_checkpoint(self):
        """从磁盘加载数据"""
        if not os.path.exists(self.filepath):
            return

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
        except Exception as e:
            self.logger.error(f"读取存档文件失败: {e}")
            return

        with self._lock:
            # 先将数据全部放入暂存区
            self._pending_data = full_data
            
            # 遍历当前已注册的模块，尝试恢复
            # (注意：字典在遍历时不能修改 keys，所以转换成 list)
            for name in list(self._handlers.keys()):
                if name in self._pending_data:
                    getter, setter = self._handlers[name]
                    try:
                        data = self._pending_data.pop(name) # 取出并移除
                        self.logger.info(f"恢复模块 {name} 状态")
                        self.logger.debug(f"数据内容: {data}")
                        setter(data)
                    except Exception as e:
                        self.logger.error(f"恢复模块 {name} 失败: {e}")
            
            # 此时，_pending_data 里剩下的就是那些“还没注册”的模块数据
            # 它们会在 register 被调用时自动恢复
            
