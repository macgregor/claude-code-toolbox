# Agent Lifecycle Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Refactor 627-line `agent-lifecycle.py` into focused modules without changing behavior.

**Architecture:** Extract State/processing to modules, wrap handler functions into LifecycleOrchestrator class, add models/errors for type safety. All existing logic preserved - just reorganized.

**Tech Stack:** Python 3, unittest, existing State/StateFile pattern

**Testing Strategy:** Test each module extraction independently. Run existing lifecycle tests after each task to ensure no behavior changes.

---

## Task 1: Extract Error Classes

**Files:**
- Create: `ai-assisted-development/src/lifecycle/__init__.py`
- Create: `ai-assisted-development/src/lifecycle/errors.py`
- Test: `ai-assisted-development/tests/test_lifecycle_errors.py`

**Step 1: Write failing test for error classes**

```python
# ai-assisted-development/tests/test_lifecycle_errors.py
import unittest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle.errors import BlockingError, NonBlockingError


class TestLifecycleErrors(unittest.TestCase):
    def test_blocking_error_is_exception(self):
        """BlockingError should be an Exception subclass."""
        err = BlockingError("test message")
        self.assertIsInstance(err, Exception)
        self.assertEqual(str(err), "test message")

    def test_nonblocking_error_is_exception(self):
        """NonBlockingError should be an Exception subclass."""
        err = NonBlockingError("test message")
        self.assertIsInstance(err, Exception)
        self.assertEqual(str(err), "test message")

    def test_blocking_error_can_be_raised(self):
        """BlockingError should be raisable."""
        with self.assertRaises(BlockingError) as ctx:
            raise BlockingError("validation failed")
        self.assertEqual(str(ctx.exception), "validation failed")

    def test_nonblocking_error_can_be_raised(self):
        """NonBlockingError should be raisable."""
        with self.assertRaises(NonBlockingError) as ctx:
            raise NonBlockingError("io failed")
        self.assertEqual(str(ctx.exception), "io failed")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
cd ai-assisted-development
python -m pytest tests/test_lifecycle_errors.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'lifecycle'"

**Step 3: Create lifecycle package and error classes**

```bash
mkdir -p ai-assisted-development/src/lifecycle
```

```python
# ai-assisted-development/src/lifecycle/__init__.py
"""Lifecycle tracking infrastructure for agent coordination."""

from .errors import BlockingError, NonBlockingError

__all__ = ["BlockingError", "NonBlockingError"]
```

```python
# ai-assisted-development/src/lifecycle/errors.py
"""Custom exceptions for lifecycle tracking."""


class BlockingError(Exception):
    """Raised to block operation and show error to agent (exit code 2)."""
    pass


class NonBlockingError(Exception):
    """Raised to log error but allow operation to continue (exit code 1)."""
    pass
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_lifecycle_errors.py -v
```

Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add src/lifecycle/__init__.py src/lifecycle/errors.py tests/test_lifecycle_errors.py
git commit -m "feat: add lifecycle error classes

Add BlockingError (exit 2) and NonBlockingError (exit 1) for lifecycle
tracking. Errors provide clear semantics for validation vs I/O failures."
```

---

## Task 2: Extract State Management

**Files:**
- Create: `ai-assisted-development/src/lifecycle/state.py`
- Modify: `ai-assisted-development/src/agent-lifecycle.py:18-190`
- Test: `ai-assisted-development/tests/test_lifecycle_state.py`

**Step 1: Write failing test for State extraction**

```python
# ai-assisted-development/tests/test_lifecycle_state.py
import unittest
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle.state import State, StateFile


class TestStateFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_path = Path(self.temp_dir) / "test-state.json"

    def test_statefile_creates_empty_dict(self):
        """StateFile should initialize as empty dict."""
        sf = StateFile(self.state_path)
        self.assertEqual(dict(sf), {})
        self.assertFalse(sf._dirty)

    def test_statefile_loads_existing_file(self):
        """StateFile should load existing JSON."""
        self.state_path.write_text('{"key": "value"}')
        sf = StateFile(self.state_path)
        self.assertEqual(sf["key"], "value")
        self.assertFalse(sf._dirty)

    def test_statefile_marks_dirty_on_write(self):
        """StateFile should mark dirty when value set."""
        sf = StateFile(self.state_path)
        sf["key"] = "value"
        self.assertTrue(sf._dirty)

    def test_statefile_saves_when_dirty(self):
        """StateFile.save() should write JSON when dirty."""
        sf = StateFile(self.state_path)
        sf["key"] = "value"
        sf.save()
        self.assertFalse(sf._dirty)
        self.assertEqual(json.loads(self.state_path.read_text()), {"key": "value"})


class TestState(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.events_dir = Path(self.temp_dir) / ".toolbox" / "events"
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def test_state_context_manager(self):
        """State should work as context manager."""
        with State(self.temp_dir, "session-123", None) as state:
            self.assertIsInstance(state, State)

    def test_state_saves_on_exit(self):
        """State should save files on context exit."""
        with State(self.temp_dir, "session-123", None) as state:
            state.set_request_id("request-456")

        global_state_path = self.events_dir / ".global-state.json"
        self.assertTrue(global_state_path.exists())
        data = json.loads(global_state_path.read_text())
        self.assertEqual(data["session_requests"]["session-123"], "request-456")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_lifecycle_state.py -v
```

Expected: FAIL with "ImportError: cannot import name 'State'"

**Step 3: Extract State and StateFile classes**

Copy lines 18-190 from `agent-lifecycle.py` to new file:

```python
# ai-assisted-development/src/lifecycle/state.py
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
```

**Step 4: Update lifecycle __init__.py to export State**

```python
# ai-assisted-development/src/lifecycle/__init__.py
"""Lifecycle tracking infrastructure for agent coordination."""

from .errors import BlockingError, NonBlockingError
from .state import State, StateFile

__all__ = ["BlockingError", "NonBlockingError", "State", "StateFile"]
```

**Step 5: Run test to verify it passes**

```bash
python -m pytest tests/test_lifecycle_state.py -v
```

Expected: PASS (6 tests)

**Step 6: Run existing lifecycle tests to ensure no regression**

```bash
python -m pytest tests/test_lifecycle.py -v
```

Expected: PASS (all existing tests still pass - agent-lifecycle.py still has State classes)

**Step 7: Commit**

```bash
git add src/lifecycle/state.py src/lifecycle/__init__.py tests/test_lifecycle_state.py
git commit -m "feat: extract State management to lifecycle module

Move StateFile and State classes from agent-lifecycle.py to
lifecycle/state.py. No behavior changes - existing code still works."
```

---

## Task 3: Extract Processing Utilities

**Files:**
- Create: `ai-assisted-development/src/lifecycle/processing.py`
- Modify: `ai-assisted-development/src/agent-lifecycle.py:192-293`
- Test: `ai-assisted-development/tests/test_lifecycle_processing.py`

**Step 1: Write failing test for processing functions**

```python
# ai-assisted-development/tests/test_lifecycle_processing.py
import unittest
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle.processing import (
    get_toolbox_root,
    generate_request_id,
    create_request_directory,
    parse_context_tags,
    parse_work_tags
)


class TestGetToolboxRoot(unittest.TestCase):
    def test_returns_env_variable(self):
        """get_toolbox_root should return TOOLBOX_ROOT env var."""
        os.environ["TOOLBOX_ROOT"] = "/test/path"
        self.assertEqual(get_toolbox_root(), "/test/path")
        del os.environ["TOOLBOX_ROOT"]

    def test_returns_cwd_from_hook_input(self):
        """get_toolbox_root should fallback to hook_input cwd."""
        result = get_toolbox_root({"cwd": "/hook/path"})
        self.assertEqual(result, "/hook/path")


class TestGenerateRequestId(unittest.TestCase):
    def test_generates_deterministic_id(self):
        """generate_request_id should be deterministic."""
        hook_input = {
            "session_id": "sess-123",
            "timestamp": "2025-12-11T10:00:00",
            "prompt": "test prompt"
        }
        id1 = generate_request_id(hook_input)
        id2 = generate_request_id(hook_input)
        self.assertEqual(id1, id2)

    def test_id_format(self):
        """generate_request_id should return timestamp_hash format."""
        hook_input = {
            "session_id": "sess-123",
            "timestamp": "2025-12-11T10:00:00",
            "prompt": "test"
        }
        request_id = generate_request_id(hook_input)
        self.assertIn("_", request_id)
        parts = request_id.split("_")
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[1]), 8)  # hash is 8 chars


class TestCreateRequestDirectory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def test_creates_directory_structure(self):
        """create_request_directory should create all subdirs."""
        request_dir = create_request_directory(self.temp_dir, "test-request")
        self.assertTrue(request_dir.exists())
        self.assertTrue((request_dir / "work").exists())
        self.assertTrue((request_dir / "session-logs").exists())
        self.assertTrue((request_dir / "hook-events.jsonl").exists())
        self.assertTrue((request_dir / "errors.log").exists())


class TestParseContextTags(unittest.TestCase):
    def test_extracts_single_context(self):
        """parse_context_tags should extract <context> content."""
        text = "before <context>extracted content</context> after"
        result = parse_context_tags(text)
        self.assertEqual(result, ["extracted content"])

    def test_extracts_multiple_contexts(self):
        """parse_context_tags should extract all <context> tags."""
        text = "<context>first</context> middle <context>second</context>"
        result = parse_context_tags(text)
        self.assertEqual(result, ["first", "second"])


class TestParseWorkTags(unittest.TestCase):
    def test_extracts_work_tag(self):
        """parse_work_tags should extract filename and content."""
        text = '<work filename="test.txt">file content</work>'
        result = parse_work_tags(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["filename"], "test.txt")
        self.assertEqual(result[0]["content"], "file content")

    def test_extracts_multiple_work_tags(self):
        """parse_work_tags should extract all <work> tags."""
        text = '<work filename="a.txt">content a</work><work filename="b.txt">content b</work>'
        result = parse_work_tags(text)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["filename"], "a.txt")
        self.assertEqual(result[1]["filename"], "b.txt")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_lifecycle_processing.py -v
```

Expected: FAIL with "ImportError: cannot import name 'get_toolbox_root'"

**Step 3: Extract processing functions**

Copy lines 192-293 from `agent-lifecycle.py`:

```python
# ai-assisted-development/src/lifecycle/processing.py
"""Data processing utilities for lifecycle tracking."""

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


def get_toolbox_root(hook_input: Dict[str, Any] = None) -> str:
    """Get TOOLBOX_ROOT from environment or env file, with fallback to cwd."""
    # Try environment variable first
    toolbox_root = os.environ.get("TOOLBOX_ROOT")
    if toolbox_root:
        return toolbox_root

    # Try reading from CLAUDE_ENV_FILE
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if env_file and Path(env_file).exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('export TOOLBOX_ROOT='):
                        # Parse: export TOOLBOX_ROOT="/workspace"
                        value = line.split('=', 1)[1].strip()
                        # Remove quotes
                        toolbox_root = value.strip('"\'')
                        if toolbox_root:
                            return toolbox_root
        except Exception:
            pass

    # Fallback to cwd from hook_input
    if hook_input:
        cwd = hook_input.get("cwd")
        if cwd:
            return cwd

    return ""


def generate_request_id(hook_input: Dict[str, Any]) -> str:
    """Generate deterministic request ID: {timestamp}_{hash}"""
    session_id = hook_input.get("session_id", "")
    timestamp = hook_input.get("timestamp", "")
    prompt = hook_input.get("prompt", "")

    # If no timestamp provided, generate one
    if not timestamp:
        timestamp = datetime.now().isoformat()

    timestamp_safe = timestamp.replace(":", "-")
    hash_input = f"{session_id}{timestamp}{prompt}"
    hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()
    hash_short = hash_digest[:8]

    return f"{timestamp_safe}_{hash_short}"


def create_request_directory(toolbox_root: str, request_id: str) -> Path:
    """Create .toolbox/events/{request_id}/ with subdirs"""
    request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id
    request_dir.mkdir(parents=True, exist_ok=True)
    (request_dir / "work").mkdir(exist_ok=True)
    (request_dir / "session-logs").mkdir(exist_ok=True)
    (request_dir / "hook-events.jsonl").touch()
    (request_dir / "errors.log").touch()
    return request_dir


def parse_context_tags(text: str) -> List[str]:
    """Extract content from <context> tags"""
    pattern = r'<context>(.*?)</context>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [match.strip() for match in matches]


def parse_work_tags(text: str) -> List[Dict[str, str]]:
    """Extract {filename, content} from <work> tags"""
    pattern = r'<work\s+filename="([^"]+)"\s*>(.*?)</work>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [{"filename": filename, "content": content.strip()} for filename, content in matches]
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_lifecycle_processing.py -v
```

Expected: PASS (10 tests)

**Step 5: Run existing lifecycle tests**

```bash
python -m pytest tests/test_lifecycle.py -v
```

Expected: PASS (agent-lifecycle.py still has functions, no regression)

**Step 6: Commit**

```bash
git add src/lifecycle/processing.py tests/test_lifecycle_processing.py
git commit -m "feat: extract processing utilities to lifecycle module

Move get_toolbox_root, generate_request_id, create_request_directory,
parse_context_tags, and parse_work_tags to lifecycle/processing.py.
No behavior changes."
```

---

## Task 4: Create Domain Models

**Files:**
- Create: `ai-assisted-development/src/lifecycle/models.py`
- Test: `ai-assisted-development/tests/test_lifecycle_models.py`

**Step 1: Write failing test for models**

```python
# ai-assisted-development/tests/test_lifecycle_models.py
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle.models import RequestContext, EventData, FileOperation
from lifecycle.errors import BlockingError


class TestRequestContext(unittest.TestCase):
    def test_creates_with_required_fields(self):
        """RequestContext should initialize with all fields."""
        ctx = RequestContext(
            session_id="sess-123",
            request_id="req-456",
            request_dir=Path("/tmp/req"),
            transcript_path=Path("/tmp/log.jsonl"),
            agent_types={},
            start_uuid="uuid-789"
        )
        self.assertEqual(ctx.session_id, "sess-123")
        self.assertEqual(ctx.request_id, "req-456")
        self.assertEqual(len(ctx.file_operations), 0)

    def test_file_operations_default_empty(self):
        """RequestContext file_operations should default to empty list."""
        ctx = RequestContext(
            session_id="s",
            request_id="r",
            request_dir=Path("/tmp"),
            transcript_path=Path("/tmp/t"),
            agent_types={},
            start_uuid=None
        )
        self.assertEqual(ctx.file_operations, [])
        ctx.file_operations.append("test")
        self.assertEqual(len(ctx.file_operations), 1)


class TestEventData(unittest.TestCase):
    def test_creates_immutable(self):
        """EventData should be frozen dataclass."""
        event = EventData(
            hook_event_name="UserPromptSubmit",
            raw_hook_input='{"test": "data"}',
            fields={"session_id": "sess-123"}
        )
        self.assertEqual(event.hook_event_name, "UserPromptSubmit")

        with self.assertRaises(AttributeError):
            event.hook_event_name = "changed"

    def test_stores_fields_dict(self):
        """EventData should store all fields in dict."""
        event = EventData(
            hook_event_name="Stop",
            raw_hook_input="{}",
            fields={"session_id": "s", "transcript_path": "/tmp/t"}
        )
        self.assertEqual(event.fields["session_id"], "s")
        self.assertEqual(event.fields["transcript_path"], "/tmp/t")


class TestFileOperation(unittest.TestCase):
    def test_creates_immutable(self):
        """FileOperation should be frozen dataclass."""
        op = FileOperation(
            filename="test.txt",
            content="content",
            mode="write",
            operation_type="work"
        )
        self.assertEqual(op.filename, "test.txt")

        with self.assertRaises(AttributeError):
            op.filename = "changed"

    def test_validate_rejects_path_separators(self):
        """FileOperation.validate() should reject path separators."""
        op = FileOperation(
            filename="path/to/file.txt",
            content="",
            mode="write",
            operation_type="work"
        )
        with self.assertRaises(BlockingError) as ctx:
            op.validate()
        self.assertIn("Invalid filename", str(ctx.exception))

    def test_validate_rejects_parent_traversal(self):
        """FileOperation.validate() should reject .. traversal."""
        op = FileOperation(
            filename="../file.txt",
            content="",
            mode="write",
            operation_type="work"
        )
        with self.assertRaises(BlockingError):
            op.validate()

    def test_validate_accepts_flat_filename(self):
        """FileOperation.validate() should accept flat filenames."""
        op = FileOperation(
            filename="file.txt",
            content="",
            mode="write",
            operation_type="work"
        )
        op.validate()  # Should not raise


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_lifecycle_models.py -v
```

Expected: FAIL with "ImportError: cannot import name 'RequestContext'"

**Step 3: Create models module**

```python
# ai-assisted-development/src/lifecycle/models.py
"""Domain models for lifecycle tracking."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Literal

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
    start_uuid: str | None

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
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_lifecycle_models.py -v
```

Expected: PASS (10 tests)

**Step 5: Commit**

```bash
git add src/lifecycle/models.py tests/test_lifecycle_models.py
git commit -m "feat: add domain models for lifecycle tracking

Add RequestContext, EventData, and FileOperation dataclasses.
Models provide type safety and clear contracts for orchestrator."
```

---

## Task 5: Create Handler ABC

**Files:**
- Create: `ai-assisted-development/src/lifecycle/handlers.py`
- Test: `ai-assisted-development/tests/test_lifecycle_handlers.py`

**Step 1: Write failing test for EventHandler ABC**

```python
# ai-assisted-development/tests/test_lifecycle_handlers.py
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle.handlers import EventHandler
from lifecycle.models import RequestContext, EventData


class TestEventHandler(unittest.TestCase):
    def test_is_abstract(self):
        """EventHandler should be abstract base class."""
        with self.assertRaises(TypeError):
            EventHandler()

    def test_requires_handle_method(self):
        """EventHandler subclass must implement handle()."""
        class IncompleteHandler(EventHandler):
            pass

        with self.assertRaises(TypeError):
            IncompleteHandler()

    def test_concrete_implementation_works(self):
        """EventHandler subclass with handle() should work."""
        class ConcreteHandler(EventHandler):
            def handle(self, context: RequestContext, event: EventData) -> RequestContext:
                return context

        handler = ConcreteHandler()
        ctx = RequestContext(
            session_id="s",
            request_id="r",
            request_dir=Path("/tmp"),
            transcript_path=Path("/tmp/t"),
            agent_types={},
            start_uuid=None
        )
        event = EventData(
            hook_event_name="Test",
            raw_hook_input="{}",
            fields={}
        )
        result = handler.handle(ctx, event)
        self.assertEqual(result, ctx)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_lifecycle_handlers.py -v
```

Expected: FAIL with "ImportError: cannot import name 'EventHandler'"

**Step 3: Create handlers module**

```python
# ai-assisted-development/src/lifecycle/handlers.py
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
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_lifecycle_handlers.py -v
```

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/lifecycle/handlers.py tests/test_lifecycle_handlers.py
git commit -m "feat: add EventHandler ABC for business logic

Create abstract base class for future handler implementations.
Currently unused - extension point for domain-specific logic."
```

---

## Task 6: Create Orchestrator Skeleton

**Files:**
- Create: `ai-assisted-development/src/lifecycle/orchestrator.py`
- Test: `ai-assisted-development/tests/test_lifecycle_orchestrator.py`

**Step 1: Write failing test for orchestrator**

```python
# ai-assisted-development/tests/test_lifecycle_orchestrator.py
import unittest
import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle.orchestrator import LifecycleOrchestrator


class TestLifecycleOrchestrator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = LifecycleOrchestrator()

    def test_creates_instance(self):
        """LifecycleOrchestrator should instantiate."""
        self.assertIsInstance(self.orchestrator, LifecycleOrchestrator)

    def test_process_returns_without_toolbox_root(self):
        """process() should return early if no toolbox_root."""
        hook_input = {"hook_event_name": "SessionStart"}
        # Should not raise
        self.orchestrator.process(hook_input)

    def test_process_handles_session_start(self):
        """process() should handle SessionStart event."""
        hook_input = {
            "hook_event_name": "SessionStart",
            "cwd": self.temp_dir,
            "session_id": "sess-123"
        }
        # Should create .toolbox/events directory
        self.orchestrator.process(hook_input)
        events_dir = Path(self.temp_dir) / ".toolbox" / "events"
        self.assertTrue(events_dir.exists())


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_lifecycle_orchestrator.py -v
```

Expected: FAIL with "ImportError: cannot import name 'LifecycleOrchestrator'"

**Step 3: Create orchestrator skeleton**

```python
# ai-assisted-development/src/lifecycle/orchestrator.py
"""Orchestrator for lifecycle event processing."""

import json
from pathlib import Path
from typing import Dict, Any

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

    def _get_handler(self, event_name: str) -> EventHandler | None:
        """Route event to handler (returns None - extension point)."""
        return None
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_lifecycle_orchestrator.py -v
```

Expected: PASS (3 tests)

**Step 5: Update lifecycle __init__.py**

```python
# ai-assisted-development/src/lifecycle/__init__.py
"""Lifecycle tracking infrastructure for agent coordination."""

from .errors import BlockingError, NonBlockingError
from .orchestrator import LifecycleOrchestrator

__all__ = ["LifecycleOrchestrator", "BlockingError", "NonBlockingError"]
```

**Step 6: Commit**

```bash
git add src/lifecycle/orchestrator.py src/lifecycle/__init__.py tests/test_lifecycle_orchestrator.py
git commit -m "feat: add LifecycleOrchestrator skeleton

Create orchestrator with basic event processing flow.
Handles SessionStart event. Framework for other events."
```

---

## Task 7: Implement UserPromptSubmit Handler

**Files:**
- Modify: `ai-assisted-development/src/lifecycle/orchestrator.py`
- Test: `ai-assisted-development/tests/test_lifecycle_orchestrator.py`

**Step 1: Write failing test for UserPromptSubmit**

Add to `test_lifecycle_orchestrator.py`:

```python
def test_process_handles_user_prompt_submit(self):
    """process() should handle UserPromptSubmit event."""
    hook_input = {
        "hook_event_name": "UserPromptSubmit",
        "cwd": self.temp_dir,
        "session_id": "sess-123",
        "timestamp": "2025-12-11T10:00:00",
        "prompt": "test prompt",
        "transcript_path": str(Path(self.temp_dir) / "session.jsonl")
    }

    # Create minimal session log
    session_log = Path(self.temp_dir) / "session.jsonl"
    session_log.write_text(json.dumps({
        "type": "user",
        "uuid": "uuid-789",
        "message": {"content": "test prompt"}
    }))

    self.orchestrator.process(hook_input)

    # Should create request directory
    events_dir = Path(self.temp_dir) / ".toolbox" / "events"
    request_dirs = list(events_dir.glob("*"))
    self.assertEqual(len(request_dirs), 1)

    # Should create context.md
    context_file = request_dirs[0] / "context.md"
    self.assertTrue(context_file.exists())
    content = context_file.read_text()
    self.assertIn("test prompt", content)
    self.assertIn("<userPrompt>", content)
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_lifecycle_orchestrator.py::TestLifecycleOrchestrator::test_process_handles_user_prompt_submit -v
```

Expected: FAIL with "AssertionError: False is not true" (context.md doesn't exist)

**Step 3: Implement UserPromptSubmit handler**

Add to `orchestrator.py`:

```python
def process(self, raw_hook_input: Dict[str, Any]):
    """Process hook event."""
    # ... existing code ...

    # 3. Create request directory if needed
    if not request_dir.exists():
        self._create_request_directory(request_dir, toolbox_root, request_id)

    # 4. Initialize context with state
    session_id = event_data.fields.get("session_id")
    transcript_path = event_data.fields.get("transcript_path")

    with State(toolbox_root, session_id, transcript_path) as state:
        context = self._build_request_context(event_data, request_dir, state)

        # 5. Execute framework logic specific to this event
        if event_data.hook_event_name == "UserPromptSubmit":
            self._handle_user_prompt_submit(context, event_data)

        # 6. Persist state changes
        self._persist_state_changes(state, context)

        # 7. Log hook event
        self._append_hook_event(request_dir, raw_hook_input)

def _build_request_context(self, event_data: EventData, request_dir: Path, state: State) -> RequestContext:
    """Load state data into RequestContext."""
    return RequestContext(
        session_id=event_data.fields.get("session_id", ""),
        request_id=state._global.get("session_requests", {}).get(event_data.fields.get("session_id"), ""),
        request_dir=request_dir,
        transcript_path=Path(event_data.fields.get("transcript_path", "")),
        agent_types=state["agent_types"],
        start_uuid=state["start_uuid"]
    )

def _handle_user_prompt_submit(self, context: RequestContext, event_data: EventData):
    """Write user prompt to context.md."""
    prompt = event_data.fields.get("prompt", "")
    context_file = context.request_dir / "context.md"
    context_file.write_text(f"""<userPrompt>
{prompt}
</userPrompt>

<!-- Hooks append agent context below as agents complete -->
""")

    # Store request_id and start_uuid in state
    # (will be persisted by _persist_state_changes)

def _persist_state_changes(self, state: State, context: RequestContext):
    """Write State changes to .state.json and .global-state.json files."""
    # For UserPromptSubmit, set request_id
    if not state._global.get("session_requests", {}).get(context.session_id):
        state.set_request_id(context.request_id)

    # Extract start_uuid from session log
    if context.transcript_path.exists():
        with open(context.transcript_path, 'r') as f:
            lines = f.readlines()
            if lines:
                last_msg = json.loads(lines[-1])
                start_uuid = last_msg.get("uuid", "")
                if start_uuid and not state["start_uuid"]:
                    state["start_uuid"] = start_uuid

def _append_hook_event(self, request_dir: Path, raw_hook_input: Dict[str, Any]):
    """Append hook event to hook_events.jsonl."""
    hook_events_file = request_dir / "hook-events.jsonl"
    with open(hook_events_file, 'a') as f:
        f.write(json.dumps(raw_hook_input) + '\n')
```

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_lifecycle_orchestrator.py::TestLifecycleOrchestrator::test_process_handles_user_prompt_submit -v
```

Expected: PASS

**Step 5: Run all orchestrator tests**

```bash
python -m pytest tests/test_lifecycle_orchestrator.py -v
```

Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add src/lifecycle/orchestrator.py tests/test_lifecycle_orchestrator.py
git commit -m "feat: implement UserPromptSubmit handler

Add _handle_user_prompt_submit() to write prompt to context.md.
Add _persist_state_changes() to save request_id and start_uuid.
Add _append_hook_event() to log all events."
```

---

## Task 8: Implement Remaining Event Handlers

**Files:**
- Modify: `ai-assisted-development/src/lifecycle/orchestrator.py`
- Test: `ai-assisted-development/tests/test_lifecycle_orchestrator.py`

**Step 1: Write failing tests for SubagentStart, SubagentStop, Stop**

Add to `test_lifecycle_orchestrator.py`:

```python
def test_process_handles_subagent_start(self):
    """process() should handle SubagentStart event."""
    # First create request with UserPromptSubmit
    self._create_test_request()

    hook_input = {
        "hook_event_name": "SubagentStart",
        "cwd": self.temp_dir,
        "session_id": "sess-123",
        "agent_id": "agent-456",
        "agent_type": "explore",
        "transcript_path": str(Path(self.temp_dir) / "session.jsonl")
    }

    self.orchestrator.process(hook_input)

    # Should store agent_type in state
    events_dir = Path(self.temp_dir) / ".toolbox" / "events"
    request_dir = list(events_dir.glob("*"))[0]
    state_file = request_dir / ".state.json"
    state_data = json.loads(state_file.read_text())
    self.assertEqual(state_data["agent_types"]["agent-456"], "explore")

def test_process_handles_subagent_stop(self):
    """process() should handle SubagentStop event."""
    self._create_test_request()

    # Create agent transcript with context/work tags
    agent_transcript = Path(self.temp_dir) / "agent-456.jsonl"
    agent_transcript.write_text(json.dumps({
        "type": "assistant",
        "message": {
            "content": [{
                "type": "text",
                "text": "<context>agent context</context><work filename=\"test.txt\">content</work>"
            }]
        }
    }))

    hook_input = {
        "hook_event_name": "SubagentStop",
        "cwd": self.temp_dir,
        "session_id": "sess-123",
        "agent_id": "agent-456",
        "agent_transcript_path": str(agent_transcript),
        "transcript_path": str(Path(self.temp_dir) / "session.jsonl")
    }

    self.orchestrator.process(hook_input)

    # Should append context to context.md
    events_dir = Path(self.temp_dir) / ".toolbox" / "events"
    request_dir = list(events_dir.glob("*"))[0]
    context_file = request_dir / "context.md"
    content = context_file.read_text()
    self.assertIn("agent context", content)

    # Should write work file
    work_file = request_dir / "work" / "test.txt"
    self.assertTrue(work_file.exists())
    self.assertEqual(work_file.read_text(), "content")

    # Should copy transcript
    transcript_copy = request_dir / "session-logs" / "agent-agent-456.jsonl"
    self.assertTrue(transcript_copy.exists())

def _create_test_request(self):
    """Helper to create a test request."""
    hook_input = {
        "hook_event_name": "UserPromptSubmit",
        "cwd": self.temp_dir,
        "session_id": "sess-123",
        "timestamp": "2025-12-11T10:00:00",
        "prompt": "test",
        "transcript_path": str(Path(self.temp_dir) / "session.jsonl")
    }
    session_log = Path(self.temp_dir) / "session.jsonl"
    session_log.write_text(json.dumps({
        "type": "user",
        "uuid": "uuid-789",
        "message": {"content": "test"}
    }))
    self.orchestrator.process(hook_input)
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_lifecycle_orchestrator.py::TestLifecycleOrchestrator::test_process_handles_subagent_start -v
```

Expected: FAIL

**Step 3: Implement SubagentStart, SubagentStop, Stop handlers**

Add to `orchestrator.py`:

```python
import shutil
from .processing import parse_context_tags, parse_work_tags

def process(self, raw_hook_input: Dict[str, Any]):
    """Process hook event."""
    # ... existing code in framework logic section ...

    # 5. Execute framework logic specific to this event
    if event_data.hook_event_name == "UserPromptSubmit":
        self._handle_user_prompt_submit(context, event_data)
    elif event_data.hook_event_name == "SubagentStart":
        self._handle_subagent_start(context, event_data)
    elif event_data.hook_event_name == "SubagentStop":
        self._handle_subagent_stop(context, event_data)
    elif event_data.hook_event_name == "Stop":
        self._handle_stop(context, event_data)

def _handle_subagent_start(self, context: RequestContext, event_data: EventData):
    """Update context.agent_types mapping (state change)."""
    agent_id = event_data.fields.get("agent_id")
    agent_type = event_data.fields.get("agent_type", "unknown")

    if agent_id and agent_type != "unknown":
        # Modify agent_types dict (will be persisted)
        context.agent_types[agent_id] = agent_type

def _handle_subagent_stop(self, context: RequestContext, event_data: EventData):
    """Extract agent context/work tags, append to context.md, copy transcript."""
    agent_id = event_data.fields.get("agent_id", "unknown")
    agent_transcript_path = event_data.fields.get("agent_transcript_path")

    if not agent_transcript_path or not Path(agent_transcript_path).exists():
        return

    # Copy agent transcript
    transcript_copy = context.request_dir / "session-logs" / f"agent-{agent_id}.jsonl"
    shutil.copy2(agent_transcript_path, transcript_copy)

    # Extract final agent output
    with open(agent_transcript_path, 'r') as f:
        lines = f.readlines()

    final_output = ""
    for line in reversed(lines):
        msg = json.loads(line)
        if msg.get("type") == "assistant":
            content_blocks = msg.get("message", {}).get("content", [])
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    final_output += block.get("text", "")
            break

    # Parse and append context tags
    contexts = parse_context_tags(final_output)
    if contexts:
        agent_type = context.agent_types.get(agent_id, "unknown")
        context_file = context.request_dir / "context.md"
        with open(context_file, 'a') as f:
            f.write(f'\n<agent-{agent_id} type="{agent_type}">\n')
            for ctx in contexts:
                f.write(ctx + '\n')
            f.write(f'</agent-{agent_id}>\n')

    # Parse and write work files
    work_items = parse_work_tags(final_output)
    work_dir = context.request_dir / "work"

    for item in work_items:
        filename = item["filename"]

        # Validate: no path separators or traversal
        if "/" in filename or "\\" in filename or ".." in filename:
            raise NonBlockingError(f"Invalid filename '{filename}' - must be simple filename only")

        work_path = work_dir / filename

        # Validate: no duplicates
        if work_path.exists():
            raise NonBlockingError(f"File '{filename}' already exists in work directory")

        work_path.write_text(item["content"])

def _handle_stop(self, context: RequestContext, event_data: EventData):
    """Extract request-specific portion from full session log."""
    transcript_path = event_data.fields.get("transcript_path")

    if not transcript_path or not Path(transcript_path).exists():
        return

    with open(transcript_path, 'r') as f:
        lines = f.readlines()

    messages = [json.loads(line) for line in lines]

    # Find start and end indices
    start_idx = None
    end_idx = None
    for idx, msg in enumerate(messages):
        if msg.get("uuid") == context.start_uuid:
            start_idx = idx
        if msg == messages[-1]:
            end_idx = idx

    # Prune and save
    if start_idx is not None and end_idx is not None:
        pruned_messages = messages[start_idx:end_idx + 1]
        pruned_log_path = context.request_dir / "session-logs" / f"{context.session_id}-pruned.jsonl"

        with open(pruned_log_path, 'w') as f:
            for msg in pruned_messages:
                f.write(json.dumps(msg) + '\n')

def _persist_state_changes(self, state: State, context: RequestContext):
    """Write State changes to .state.json and .global-state.json files."""
    # For UserPromptSubmit, set request_id
    if not state._global.get("session_requests", {}).get(context.session_id):
        state.set_request_id(context.request_id)

    # Extract start_uuid from session log
    if context.transcript_path.exists():
        with open(context.transcript_path, 'r') as f:
            lines = f.readlines()
            if lines:
                last_msg = json.loads(lines[-1])
                start_uuid = last_msg.get("uuid", "")
                if start_uuid and not state["start_uuid"]:
                    state["start_uuid"] = start_uuid

    # Persist agent_types changes (SubagentStart)
    if context.agent_types:
        state["agent_types"] = context.agent_types
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_lifecycle_orchestrator.py -v
```

Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add src/lifecycle/orchestrator.py tests/test_lifecycle_orchestrator.py
git commit -m "feat: implement SubagentStart, SubagentStop, Stop handlers

Add _handle_subagent_start() to track agent types.
Add _handle_subagent_stop() to extract context/work tags and copy transcript.
Add _handle_stop() to create session log snapshot.
Update _persist_state_changes() to save agent_types."
```

---

## Task 9: Update agent-lifecycle.py to Use Orchestrator

**Files:**
- Modify: `ai-assisted-development/src/agent-lifecycle.py`
- Test: `ai-assisted-development/tests/test_lifecycle.py`

**Step 1: Run existing tests to establish baseline**

```bash
python -m pytest tests/test_lifecycle.py -v
```

Expected: PASS (all existing tests pass with current implementation)

**Step 2: Update agent-lifecycle.py main() to use orchestrator**

Replace lines 295-329 (main function) in `agent-lifecycle.py`:

```python
from lifecycle import LifecycleOrchestrator, BlockingError, NonBlockingError


def main():
    """Read hook input and dispatch to orchestrator."""
    try:
        hook_input = json.load(sys.stdin)
        orchestrator = LifecycleOrchestrator()
        orchestrator.process(hook_input)
        sys.exit(0)
    except BlockingError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except NonBlockingError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
```

**Step 3: Run existing tests to verify no regression**

```bash
python -m pytest tests/test_lifecycle.py -v
```

Expected: PASS (all tests still pass - orchestrator implements same behavior)

**Step 4: Commit**

```bash
git add src/agent-lifecycle.py
git commit -m "refactor: use LifecycleOrchestrator in main()

Replace event dispatch with orchestrator.process().
Add exception handling for BlockingError/NonBlockingError.
No behavior changes - all tests pass."
```

---

## Task 10: Remove Duplicate Code from agent-lifecycle.py

**Files:**
- Modify: `ai-assisted-development/src/agent-lifecycle.py`
- Test: `ai-assisted-development/tests/test_lifecycle.py`

**Step 1: Run tests to establish baseline**

```bash
python -m pytest tests/test_lifecycle.py -v
```

Expected: PASS

**Step 2: Remove State classes (lines 18-190)**

Delete StateFile and State classes from `agent-lifecycle.py` (already in lifecycle/state.py).

**Step 3: Remove processing functions (lines 192-293)**

Delete get_toolbox_root, generate_request_id, create_request_directory, parse_context_tags, parse_work_tags from `agent-lifecycle.py` (already in lifecycle/processing.py).

**Step 4: Remove handler functions**

Delete all handle_* functions except main() from `agent-lifecycle.py` (logic now in orchestrator).

**Step 5: Simplify imports**

Update imports at top of `agent-lifecycle.py`:

```python
#!/usr/bin/env python3
"""
Universal agent lifecycle hook handler.
Handles all hook events via LifecycleOrchestrator.
"""

import json
import sys

from lifecycle import LifecycleOrchestrator, BlockingError, NonBlockingError


def main():
    """Read hook input and dispatch to orchestrator."""
    try:
        hook_input = json.load(sys.stdin)
        orchestrator = LifecycleOrchestrator()
        orchestrator.process(hook_input)
        sys.exit(0)
    except BlockingError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except NonBlockingError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 6: Run tests to verify no regression**

```bash
python -m pytest tests/test_lifecycle.py -v
```

Expected: PASS (all tests still pass)

**Step 7: Run all tests**

```bash
python -m pytest ai-assisted-development/tests/ -v
```

Expected: PASS (all lifecycle tests pass)

**Step 8: Commit**

```bash
git add src/agent-lifecycle.py
git commit -m "refactor: remove duplicate code from agent-lifecycle.py

Delete State, processing, and handler functions (now in lifecycle modules).
agent-lifecycle.py is now just hook interface layer.
File reduced from 627 lines to ~30 lines."
```

---

## Task 11: Add Extension Point Placeholders

**Files:**
- Modify: `ai-assisted-development/src/lifecycle/orchestrator.py`
- Test: Run manual test

**Step 1: Add _execute_file_operations() stub**

Add to `orchestrator.py`:

```python
def _execute_file_operations(self, context: RequestContext):
    """Execute FileOperations queued by handlers (currently none - extension point)."""
    # Future: Execute context.file_operations
    # For now, no handlers registered, so nothing to execute
    pass
```

**Step 2: Update process() to call _execute_file_operations()**

Modify process() method:

```python
# 7. Execute side effects
self._persist_state_changes(state, context)
self._execute_file_operations(context)  # Extension point
self._append_hook_event(request_dir, raw_hook_input)
```

**Step 3: Verify orchestrator still works**

```bash
python -m pytest tests/test_lifecycle_orchestrator.py -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add src/lifecycle/orchestrator.py
git commit -m "feat: add file operations extension point

Add _execute_file_operations() stub for future handler support.
Currently unused - extension point for business logic."
```

---

## Task 12: Final Integration Test

**Files:**
- Test: `ai-assisted-development/tests/test_integration_lifecycle.py`

**Step 1: Write end-to-end integration test**

```python
# ai-assisted-development/tests/test_integration_lifecycle.py
"""Integration test for full lifecycle refactoring."""

import unittest
import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle import LifecycleOrchestrator


class TestLifecycleIntegration(unittest.TestCase):
    """End-to-end test simulating real hook events."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = LifecycleOrchestrator()
        self.session_log = Path(self.temp_dir) / "session.jsonl"

    def test_full_lifecycle_flow(self):
        """Test complete flow: SessionStart -> UserPromptSubmit -> SubagentStart -> SubagentStop -> Stop."""

        # 1. SessionStart
        self.orchestrator.process({
            "hook_event_name": "SessionStart",
            "cwd": self.temp_dir,
            "session_id": "sess-integration"
        })

        events_dir = Path(self.temp_dir) / ".toolbox" / "events"
        self.assertTrue(events_dir.exists())

        # 2. UserPromptSubmit
        self.session_log.write_text(json.dumps({
            "type": "user",
            "uuid": "uuid-start",
            "message": {"content": "help me implement feature X"}
        }) + '\n')

        self.orchestrator.process({
            "hook_event_name": "UserPromptSubmit",
            "cwd": self.temp_dir,
            "session_id": "sess-integration",
            "timestamp": "2025-12-11T10:00:00",
            "prompt": "help me implement feature X",
            "transcript_path": str(self.session_log)
        })

        request_dirs = list(events_dir.glob("*"))
        self.assertEqual(len(request_dirs), 1)
        request_dir = request_dirs[0]

        context_file = request_dir / "context.md"
        self.assertTrue(context_file.exists())
        self.assertIn("help me implement feature X", context_file.read_text())

        # 3. SubagentStart
        self.orchestrator.process({
            "hook_event_name": "SubagentStart",
            "cwd": self.temp_dir,
            "session_id": "sess-integration",
            "agent_id": "agent-explore",
            "agent_type": "Explore",
            "transcript_path": str(self.session_log)
        })

        state_file = request_dir / ".state.json"
        state_data = json.loads(state_file.read_text())
        self.assertEqual(state_data["agent_types"]["agent-explore"], "Explore")

        # 4. SubagentStop
        agent_transcript = Path(self.temp_dir) / "agent-explore.jsonl"
        agent_transcript.write_text(json.dumps({
            "type": "assistant",
            "message": {
                "content": [{
                    "type": "text",
                    "text": "I found the relevant code. <context>The feature X implementation should go in src/feature_x.py</context>"
                }]
            }
        }))

        self.orchestrator.process({
            "hook_event_name": "SubagentStop",
            "cwd": self.temp_dir,
            "session_id": "sess-integration",
            "agent_id": "agent-explore",
            "agent_transcript_path": str(agent_transcript),
            "transcript_path": str(self.session_log)
        })

        context_content = context_file.read_text()
        self.assertIn("feature X implementation", context_content)
        self.assertIn('<agent-agent-explore type="Explore">', context_content)

        # 5. Stop
        self.session_log.write_text(
            self.session_log.read_text() +
            json.dumps({"type": "assistant", "message": {"content": "Done"}}) + '\n'
        )

        self.orchestrator.process({
            "hook_event_name": "Stop",
            "cwd": self.temp_dir,
            "session_id": "sess-integration",
            "transcript_path": str(self.session_log)
        })

        pruned_log = request_dir / "session-logs" / "sess-integration-pruned.jsonl"
        self.assertTrue(pruned_log.exists())


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run integration test**

```bash
python -m pytest tests/test_integration_lifecycle.py -v
```

Expected: PASS

**Step 3: Run all tests to ensure everything works**

```bash
python -m pytest ai-assisted-development/tests/ -v
```

Expected: PASS (all tests pass)

**Step 4: Commit**

```bash
git add tests/test_integration_lifecycle.py
git commit -m "test: add end-to-end lifecycle integration test

Test complete flow from SessionStart through Stop.
Verifies all framework operations work together correctly."
```

---

## Task 13: Documentation Update

**Files:**
- Modify: `docs/plans/2025-12-11-agent-lifecycle-refactoring.md`

**Step 1: Update plan status**

Change status from "design" to "implemented":

```yaml
---
name: agent-lifecycle-refactoring
description: >
  Refactoring plan for agent-lifecycle.py to extract core patterns and improve
  maintainability. Establishes clean separation between hook interface, orchestration,
  state management, and event handlers.
created: 2025-12-11
status: implemented
---
```

**Step 2: Commit**

```bash
git add docs/plans/2025-12-11-agent-lifecycle-refactoring.md
git commit -m "docs: mark agent-lifecycle refactoring as implemented"
```

---

## Completion

All tasks complete. The refactoring:
- Extracted 627-line file into focused modules
- Preserved all existing behavior (tests pass)
- Established clear architecture layers
- Added extension points for future development
- Maintained test coverage throughout

Run final verification:

```bash
python -m pytest ai-assisted-development/tests/ -v
make test
```

Both should PASS.
