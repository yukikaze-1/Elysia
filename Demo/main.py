import sys
import time
import logging

# 1. 引入核心架构组件
from Demo.Core.EventBus import EventBus, global_event_bus
from Demo.Core.Dispatcher import Dispatcher
from Demo.Layers.L0.L0 import SensorLayer
from Demo.Layers.L1 import BrainLayer
from Demo.Layers.L2 import MemoryLayer
from Demo.Layers.L3 import PersonaLayer
from Demo.Workers.Reflector.Reflector import Reflector

from Demo.Logger import setup_logger

def main():
    logger :logging.Logger = setup_logger("Main")
    logger.info(">>> Initializing AI Agent System...")

    # ==========================================
    # Step 1: 创建神经中枢 (Event Bus)
    # ==========================================
    bus = global_event_bus

    # ==========================================
    # Step 2: 实例化各层 (Dependency Injection)
    # ==========================================
    
    # [L2 记忆层] 
    l2 = MemoryLayer()
    
    # [L3 人格层] - 加载初始设定
    l3 = PersonaLayer()
    
    # [L1 大脑层] - 加载 API Key
    l1 = BrainLayer()
    
    # [Reflector] - 负责后台整理
    reflector = Reflector()
    reflector.start()
    
    # [L0 传感层] - 需要 bus 来发送 USER_INPUT 和 SYSTEM_TICK
    l0 = SensorLayer(event_bus=bus)

    # ==========================================
    # Step 3: 组装调度器 (The Orchestrator)
    # ==========================================
    # 调度器持有所有模块的引用，负责指挥
    dispatcher = Dispatcher(
        event_bus=bus,
        l0=l0,
        l1=l1,
        l2=l2,
        l3=l3,
        reflector=reflector
    )

    # ==========================================
    # Step 4: 启动系统
    # ==========================================
    try:
        # 1. 启动 L0 的子线程 (输入监听 + 心跳)
        # 这样 input() 就不会阻塞主程序
        l0.start_threads()

        # 2. 启动调度器主循环 (这是一个阻塞操作，也是主程序的 Loop)
        logger.info("System ready. Entering Main Loop.")
        dispatcher.start() 

    except KeyboardInterrupt:
        # 捕获 Ctrl+C，进行优雅退出
        logger.info("\nSTOP signal received. Shutting down...")
    
    except Exception as e:
        logger.error(f"Critical System Failure: {e}", exc_info=True)
    
    finally:
        # ==========================================
        # Step 5: 清理资源 (Graceful Shutdown)
        # ==========================================
        # 停止调度器循环
        if 'dispatcher' in locals():
            dispatcher.stop()
        
        # 停止 L0 的监听线程
        if 'l0' in locals():
            l0.stop_threads()
            
        # 确保 Reflector 保存所有未处理的缓存,然后停止它
        if 'reflector' in locals():
            logger.info("Saving pending reflections...")
            # 调用强制保存接口
            reflector.force_save() 
            reflector.stop()
            
        logger.info("System Shutdown Complete.")


if __name__ == "__main__":
    main()
    
    