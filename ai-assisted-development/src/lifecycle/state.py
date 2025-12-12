"""State management for lifecycle tracking."""

import json
import weakref
from pathlib import Path
from typing import Dict, Any, Callable, Optional, Tuple


class _TrackedDict(dict):
    """Dict that marks parent StateFile as dirty on any modification.

    Note: Only dict nesting is tracked. Dicts inside lists are not tracked
    and require manual re-assignment.
    """

    def __init__(self, parent: 'StateFile', *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._parent_ref = weakref.ref(parent)
        for key, value in list(self.items()):
            if isinstance(value, dict) and not isinstance(value, _TrackedDict):
                super().__setitem__(key, _TrackedDict(parent, value))

    def _mark_dirty(self) -> None:
        """Mark parent StateFile as dirty if parent still exists."""
        parent = self._parent_ref()
        if parent is not None:
            parent._dirty = True

    def __setitem__(self, key: Any, value: Any) -> None:
        parent = self._parent_ref()
        if parent is None:
            return
        if isinstance(value, dict) and not isinstance(value, _TrackedDict):
            value = _TrackedDict(parent, value)
        super().__setitem__(key, value)
        parent._dirty = True

    def __delitem__(self, key: Any) -> None:
        super().__delitem__(key)
        self._mark_dirty()

    def update(self, *args: Any, **kwargs: Any) -> None:
        super().update(*args, **kwargs)
        parent = self._parent_ref()
        if parent is not None:
            for key, value in list(self.items()):
                if isinstance(value, dict) and not isinstance(value, _TrackedDict):
                    super().__setitem__(key, _TrackedDict(parent, value))
        self._mark_dirty()

    def pop(self, *args: Any) -> Any:
        result = super().pop(*args)
        self._mark_dirty()
        return result

    def popitem(self) -> Tuple[Any, Any]:
        result = super().popitem()
        self._mark_dirty()
        return result

    def setdefault(self, key: Any, default: Any = None) -> Any:
        if key in self:
            return self[key]
        parent = self._parent_ref()
        if parent is not None:
            if isinstance(default, dict) and not isinstance(default, _TrackedDict):
                default = _TrackedDict(parent, default)
            parent._dirty = True
        super().__setitem__(key, default)
        return default

    def clear(self) -> None:
        super().clear()
        self._mark_dirty()


class StateFile(dict):
    """File-backed dict with automatic nested change tracking."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path: Path = path
        self._dirty: bool = False
        self._loaders: Dict[str, Callable[[], Any]] = {}
        if path.exists():
            data = json.loads(path.read_text())
            for key, value in data.items():
                if isinstance(value, dict):
                    super().__setitem__(key, _TrackedDict(self, value))
                else:
                    super().__setitem__(key, value)

    def register_loader(self, key: str, loader: Callable[[], Any]) -> None:
        """Register a function to populate key on cache miss."""
        self._loaders[key] = loader

    def __missing__(self, key: str) -> Optional[Any]:
        """Auto-populate from registered loader on cache miss."""
        if key in self._loaders:
            value = self._loaders[key]()
            if value is not None and value != "unknown":
                self[key] = value
                return value
        return None

    def __getitem__(self, key: Any) -> Any:
        value = super().__getitem__(key)
        if isinstance(value, dict) and not isinstance(value, _TrackedDict):
            value = _TrackedDict(self, value)
            super().__setitem__(key, value)
        return value

    def __setitem__(self, key: Any, value: Any) -> None:
        if isinstance(value, dict) and not isinstance(value, _TrackedDict):
            value = _TrackedDict(self, value)
        super().__setitem__(key, value)
        self._dirty = True

    def save(self) -> None:
        """Atomic write if dirty."""
        if self._dirty:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix('.tmp')
            data = self._unwrap_for_json(dict(self))
            temp.write_text(json.dumps(data, indent=2))
            temp.rename(self.path)
            self._dirty = False

    def _unwrap_for_json(self, obj: Any) -> Any:
        """Recursively unwrap _TrackedDict to plain dict for JSON serialization."""
        if isinstance(obj, _TrackedDict):
            return {k: self._unwrap_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, dict):
            return {k: self._unwrap_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._unwrap_for_json(item) for item in obj]
        return obj


class State:
    """Unified state management hiding dual-file implementation.

    Args:
        toolbox_root: Project root directory (from get_toolbox_root(hook_input))
        session_id: Session ID (from hook_input['session_id'])
        transcript_path: Path to session log (from hook_input['transcript_path'])
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
        if "session_requests" not in self._global:
            self._global["session_requests"] = {}
        self._global["session_requests"][self.session_id] = request_id

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
