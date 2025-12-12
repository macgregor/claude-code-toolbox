"""Domain models for lifecycle tracking."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Literal, Optional

from .errors import BlockingError


@dataclass
class RequestContext:
    """Request-scoped state managed by lifecycle framework.

    Handlers receive this, modify it, and return it.
    Orchestrator persists changes to State files.
    """
    session_id: str
    request_id: str
    request_dir: Path  # Handlers can read files from here
    transcript_path: Path

    # Mutable state data
    agent_types: Dict[str, str]  # agent_id -> agent_type
    start_uuid: Optional[str]

    # File operations to execute
    file_operations: List["FileOperation"] = field(default_factory=list)


@dataclass(frozen=True)
class EventData:
    """Normalized hook input from Claude Code.

    Transforms anthropic's hook input JSON into validated data.
    Common fields: session_id, transcript_path, cwd, hook_event_name.
    Event-specific fields available via .fields dict.
    """
    hook_event_name: str
    raw_hook_input: str  # Original JSON for debugging
    fields: Dict[str, Any]  # All normalized/validated fields


@dataclass(frozen=True)
class FileOperation:
    """File operation to execute relative to request_dir.

    Write mode overwrites existing files (last write wins).
    Orchestrator determines full path based on operation type.
    """
    filename: str  # Flat filename only (validated: no path separators)
    content: str
    mode: Literal["write", "append", "copy"]
    operation_type: Literal["context", "work", "session_log"]

    def validate(self):
        """Raise BlockingError if filename is invalid (resilience, not security)."""
        if "/" in self.filename or "\\" in self.filename or ".." in self.filename:
            raise BlockingError(f"Invalid filename: {self.filename}")
