import threading
import time
from datetime import datetime
from Core.EventBus import EventBus
from Core.Schema import Event, EventType, EventContentType, EventSource
from Logger import setup_logger
from Config import SystemClockConfig
import logging

class SystemClock:
    """
    [基建组件] 系统时钟
    负责产生 SYSTEM_TICK 事件，驱动 PsycheSystem 和其他周期性任务。
    """
    def __init__(self, event_bus: EventBus, config: SystemClockConfig):
        self.config = config
        self.bus = event_bus
        self.interval: float = config.heartbeat_interval
        self.logger: logging.Logger = setup_logger(config.logger_name)
        
        self.running = False
        self._thread = None


    def start(self):
        if self.running:
            return
        self.running = True
        self.logger.info(f"SystemClock started. Tick interval: {self.interval}s")
        self._thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._thread.start()


    def stop(self):
        self.running = False
        self.logger.info("SystemClock stopping...")


    def _tick_loop(self):
        while self.running:
            time.sleep(self.interval)
            
            timestamp = time.time()
            # 发送心跳事件
            event = Event(
                type=EventType.SYSTEM_TICK,
                content_type=EventContentType.TIME,
                content=timestamp,
                source=EventSource.SYSTEM_CLOCK, 
                timestamp=timestamp
            )
            self.bus.publish(event)
            self.logger.debug(f"Tick: {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}")