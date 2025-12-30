# Core/Handlers/BaseHandler.py
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from Core.Schema import Event

if TYPE_CHECKING:
    from Core.AgentContext import AgentContext

class BaseHandler(ABC):
    def __init__(self, context: "AgentContext"):
        self.context = context

    @abstractmethod
    def handle(self, event: Event):
        pass