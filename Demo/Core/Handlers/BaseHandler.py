# Core/Handlers/BaseHandler.py
from abc import ABC, abstractmethod
from Core.Schema import Event

class BaseHandler(ABC):
    @abstractmethod
    def handle(self, event: Event):
        pass