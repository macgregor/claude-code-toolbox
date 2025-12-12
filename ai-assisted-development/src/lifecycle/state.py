"""State management for lifecycle tracking."""

import json
from pathlib import Path
from typing import Dict, Any, Callable


class StateFile(dict):
    """File-backed dict with auto-population on cache miss.

    WARNING: Nested dict modifications don't trigger dirty flag.
    Example problematic pattern:
        state["agent_types"][agent_id] = type  # Won't mark dirty!

    Workaround: Re-assign the entire dict:
        agent_types = state["agent_types"]
        agent_types[agent_id] = type
        state["agent_types"] = agent_types  # Triggers dirty flag
    """

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self._dirty = False
        self._loaders = {}
        if path.exists():
            self.update(json.loads(path.read_text()))

    def register_loader(self, key: str, loader: Callable[[], Any]):
        """Register a function to populate key on cache miss."""
        self._loaders[key] = loader

    def __missing__(self, key: str):
        """Auto-populate from registered loader on cache miss."""
        if key in self._loaders:
            value = self._loaders[key]()
            if value is not None and value != "unknown":
                self[key] = value
                return value
        return None

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._dirty = True

    def save(self):
        """Atomic write if dirty."""
        if self._dirty:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(dict(self), indent=2))
            temp.rename(self.path)
            self._dirty = False


class State:
    """Unified state management hiding dual-file implementation.

    Args:
        toolbox_root: Project root directory (from get_toolbox_root(hook_input))
        session_id: Session ID (from hook_input['session_id'])
        transcript_path: Path to session log (from hook_input['transcript_path'])

    WARNING: agent_types is a nested dict that requires special handling.
    Nested modifications DON'T trigger dirty flag. To modify agent_types:
        agent_types = state["agent_types"]
        agent_types[agent_id] = type
        state["agent_types"] = agent_types  # Re-assign to trigger save
    """

    def __init__(self, toolbox_root: str, session_id: str, transcript_path: str = None):
        self.session_id = session_id
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self.events_dir = Path(toolbox_root) / ".toolbox" / "events"

        self._global = StateFile(self.events_dir / ".global-state.json")
        self._global.register_loader(
            "session_requests",
            lambda: {self.session_id: self._find_request_id()}
        )

        self._request = None

    def _ensure_request(self):
        """Lazy load request state file."""
        if self._request is None:
            rid = self._global.get("session_requests", {}).get(self.session_id)
            if not rid:
                rid = self._find_request_id()
                if not rid:
                    raise ValueError(f"No request_id for session {self.session_id}")
                session_requests = self._global.get("session_requests", {})
                session_requests[self.session_id] = rid
                self._global["session_requests"] = session_requests

            self._request = StateFile(self.events_dir / rid / ".state.json")
            self._request.register_loader("start_uuid", self._find_start_uuid)
            self._request.register_loader("agent_types", lambda: {})

    def __getitem__(self, key):
        """Dict-like access routing to correct file."""
        if key == "session_requests":
            return self._global.get(key, {})

        self._ensure_request()

        if key == "agent_types":
            return self._request.setdefault(key, {})

        return self._request.get(key, "")

    def set_request_id(self, request_id: str):
        """Set request_id for current session."""
        session_requests = self._global.get("session_requests", {})
        session_requests[self.session_id] = request_id
        self._global["session_requests"] = session_requests  # Trigger dirty flag

    def __setitem__(self, key, value):
        """Dict-like write routing to correct file."""
        self._ensure_request()
        self._request[key] = value

    def _find_request_id(self) -> str:
        """Reconstruct request_id by scanning all request directories.

        Raises:
            ValueError: If no request_id found for session
        """
        if not self.events_dir.exists():
            raise ValueError(f"Events directory does not exist: {self.events_dir}")

        for d in sorted(self.events_dir.iterdir(), key=lambda p: p.name, reverse=True):
            if not d.is_dir():
                continue
            hook_file = d / "hook-events.jsonl"
            if not hook_file.exists():
                continue
            # Read first line (UserPromptSubmit event)
            first_line = next((l for l in hook_file.read_text().split('\n') if l), None)
            if first_line and json.loads(first_line).get("session_id") == self.session_id:
                return d.name

        raise ValueError(f"No request_id found for session {self.session_id}")

    def _find_start_uuid(self) -> str:
        """Reconstruct start_uuid from session log.

        Raises:
            ValueError: If session log not found or no valid user prompt found
        """
        # Use transcript_path from hook input if available
        if self.transcript_path and self.transcript_path.exists():
            log = self.transcript_path
        else:
            # Fallback: use request-scoped session log copy (from handle_stop_event)
            request_id = self._global.get("session_requests", {}).get(self.session_id)
            if not request_id:
                raise ValueError(f"Cannot find start_uuid: no request_id for session {self.session_id}")
            log = self.events_dir / request_id / "session-logs" / f"{self.session_id}-pruned.jsonl"

        if not log.exists():
            raise ValueError(f"Session log not found: {log}")

        for line in reversed(log.read_text().split('\n')):
            if line and (msg := json.loads(line)).get("type") == "user" and not msg.get("isSidechain") and "isMeta" not in msg and isinstance(msg.get("message", {}).get("content"), str):
                uuid = msg.get("uuid")
                if not uuid:
                    raise ValueError("User prompt message missing uuid field")
                return uuid

        raise ValueError(f"No valid user prompt found in session log: {log}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._global.save()
        if self._request:
            self._request.save()
