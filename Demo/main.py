"""
Elysia 主程序入口(单机版本)fastapi版本见 Demo/Server/server.py
负责初始化各个组件并启动服务
该版本采用阻塞式主循环，适合单机运行和测试，不支持dashboard，只支持终端输入
最后更新时间： 2025-12-26
"""
import logging

# 1. 引入核心架构组件
from Core.EventBus import EventBus
from Core.Dispatcher import Dispatcher
from Layers.L0.L0 import SensorLayer
from Layers.L1 import BrainLayer
from Layers.L2.L2 import MemoryLayer
from Layers.L3 import PersonaLayer
from Workers.Reflector.Reflector import Reflector
from Core.ActuatorLayer import ActuatorLayer
from Layers.PsycheSystem import PsycheSystem
from Core.SessionState import SessionState
from Core.CheckPointManager import CheckPointManager

from Logger import setup_logger
from Config.Config import GlobalConfig, global_config
from Core.AgentContext import AgentContext


class Elysia:
    def __init__(self, config: GlobalConfig):
        self.logger :logging.Logger = setup_logger("Elysia")
        self.bus = EventBus()               # 全局事件总线
        self.l0 = SensorLayer(event_bus=self.bus, config=config.L0)   # [L0 传感层] - 需要 bus 来发送 USER_INPUT 和 SYSTEM_TICK
        self.l1 = BrainLayer(config.L1)                      # [L1 大脑层] 
        self.l2 = MemoryLayer(config.L2)                     # [L2 记忆层] 
        self.l3 = PersonaLayer(config.L3)                    # [L3 人格层] - 加载初始设定
        self.reflector = Reflector(self.bus,config.Reflector, self.l2)                # [Reflector] - 负责后台整理
        self.actuator = ActuatorLayer(self.bus, config.Core.Actuator)        # [Actuator] - 负责执行动作
        self.psyche_system = PsycheSystem(config.L0.PsycheSystem)  # [PsycheSystem] - 心智系统
        self.session = SessionState(config=config.Core.SessionState)  # [SessionState] - 会话状态管理
        self.checkpoint_manager = CheckPointManager(config.Core.CheckPointManager)  # [CheckpointManager] - 检查点管理器
        
        self.context = AgentContext(
            event_bus=self.bus,
            l0=self.l0,
            l1=self.l1,
            l2=self.l2,
            l3=self.l3,
            reflector=self.reflector,
            actuator=self.actuator,
            psyche_system=self.psyche_system,
            session=self.session,
            checkpoint_manager=self.checkpoint_manager,
        )
        
        # 调度器持有所有模块的引用，负责指挥
        self.dispatcher = Dispatcher(context=self.context)

        self.logger.info("Elysia system initialized.")
        
    def run(self):
        try:
            self.logger.info("Starting Elysia system...")
            
            # 启动 Reflector 后台反思模块
            self.reflector.start()
            
            # 1. 启动 L0 的子线程 (输入监听 + 心跳)
            # 这样 input() 就不会阻塞主程序
            self.l0.start_threads()

            # 2. 启动调度器主循环 (这是一个阻塞操作，也是主程序的 Loop)
            self.logger.info("System ready. Entering Main Loop.")
            self.dispatcher.start() 
        except KeyboardInterrupt:
            # 捕获 Ctrl+C，进行优雅退出
            self.logger.info("\nSTOP signal received. Shutting down...")
        
        except Exception as e:
            self.logger.error(f"Critical System Failure: {e}", exc_info=True)
        
        finally:
            # 停止调度器循环
            if 'dispatcher' in locals():
                self.dispatcher.stop()
            
            # 停止 L0 的监听线程
            if 'l0' in locals():
                self.l0.stop_threads()
                
            # 确保 Reflector 保存所有未处理的缓存,然后停止它
            if 'reflector' in locals():
                self.logger.info("Saving pending reflections...")
                # 调用强制保存接口
                self.reflector.force_save() 
                self.reflector.stop()
                
            # 
            if 'l2' in locals():
                self.l2.close()
                
            self.logger.info("System Shutdown Complete.")


if __name__ == "__main__":
    # 加载配置
    config: GlobalConfig = global_config.load("/home/yomu/Elysia/Demo/config.yaml")
    elysia = Elysia(config)
    elysia.run()
    
    