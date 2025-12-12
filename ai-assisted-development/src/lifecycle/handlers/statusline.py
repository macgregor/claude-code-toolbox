"""StatusLine event handler."""

from ..models import RequestContext, EventData
from ..errors import NonBlockingError
from .base import EventHandler


class StatusLineHandler(EventHandler):
    """Handler for StatusLine hook events."""

    PLUGIN_ID = "ai-assisted-development@claude-code-toolbox"
    MARKETPLACE_ID = "claude-code-toolbox"

    def handle(self, context: RequestContext, event_data: EventData) -> RequestContext:
        """Build and print statusline (stub implementation)."""
        # Stub - will implement later
        print("StatusLine stub")
        return context
