"""Base event handler interface."""

from abc import ABC, abstractmethod
from ..models import RequestContext, EventData


class EventHandler(ABC):
    """Base class for event handlers."""

    @abstractmethod
    def handle(self, context: RequestContext, event_data: EventData) -> RequestContext:
        """Process event with business logic.

        Args:
            context: Request context with state
            event_data: Hook input data

        Returns:
            Modified request context

        Raises:
            BlockingError: For validation failures (exit 2)
            NonBlockingError: For I/O failures (exit 1)
        """
        pass
