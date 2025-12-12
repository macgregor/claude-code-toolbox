"""Orchestrator for lifecycle event processing."""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from .errors import NonBlockingError
from .models import RequestContext, EventData
from .processing import get_toolbox_root, generate_request_id, create_request_directory
from .state import State
from .handlers import EventHandler


class LifecycleOrchestrator:
    """Coordinates hook processing, manages lifecycle, executes side effects."""

    def process(self, raw_hook_input: Dict[str, Any]):
        """Process hook event.

        Args:
            raw_hook_input: Raw hook input JSON from Claude Code
        """
        # 1. Parse and validate
        event_data = self._build_event_data(raw_hook_input)

        # 2. Determine request context
        toolbox_root = get_toolbox_root(raw_hook_input)
        if not toolbox_root:
            return

        # Handle SessionStart specially - just create events dir
        if event_data.hook_event_name == "SessionStart":
            events_dir = Path(toolbox_root) / ".toolbox" / "events"
            events_dir.mkdir(parents=True, exist_ok=True)
            return

        # For other events, need request_id
        request_id = self._get_or_create_request_id(event_data, toolbox_root)
        request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id

        # 3. Create request directory if needed
        if not request_dir.exists():
            self._create_request_directory(request_dir, toolbox_root, request_id)

        # TODO: Implement full flow in subsequent tasks

    def _build_event_data(self, raw_hook_input: Dict[str, Any]) -> EventData:
        """Extract/validate fields, create EventData."""
        return EventData(
            hook_event_name=raw_hook_input.get("hook_event_name", ""),
            raw_hook_input=json.dumps(raw_hook_input),
            fields=raw_hook_input
        )

    def _get_or_create_request_id(self, event_data: EventData, toolbox_root: str) -> str:
        """UserPromptSubmit creates, others lookup from state."""
        if event_data.hook_event_name == "UserPromptSubmit":
            return generate_request_id(event_data.fields)

        # Lookup from state
        session_id = event_data.fields.get("session_id")
        transcript_path = event_data.fields.get("transcript_path")

        with State(toolbox_root, session_id, transcript_path) as state:
            return state._global.get("session_requests", {}).get(session_id, "")

    def _create_request_directory(self, request_dir: Path, toolbox_root: str, request_id: str):
        """Create directory structure on first event."""
        create_request_directory(toolbox_root, request_id)

    def _get_handler(self, event_name: str) -> Optional[EventHandler]:
        """Route event to handler (returns None - extension point)."""
        return None
