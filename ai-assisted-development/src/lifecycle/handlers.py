"""Event handlers for lifecycle tracking."""

from abc import ABC, abstractmethod

from .models import RequestContext, EventData


class EventHandler(ABC):
    """Abstract base class for business logic extension point."""

    @abstractmethod
    def handle(self, context: RequestContext, event: EventData) -> RequestContext:
        """Process event with business logic.

        Args:
            context: Request-scoped state
            event: Normalized hook input

        Returns:
            Modified context with queued file operations

        Raises:
            BlockingError: Validation failures (exit 2)
            NonBlockingError: I/O failures (exit 1)
        """
        pass
