# StatusLine Event Handler Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Implement statusline as an event handler in the lifecycle system, replacing bash script with testable Python code.

**Architecture:** Reuse agent-lifecycle.py as universal entry point. Orchestrator infers StatusLine event when hook_event_name missing, builds RequestContext, and routes to StatusLineHandler. Handler reads plugin metadata, checks git SHA, formats output, and prints to stdout.

**Tech Stack:** Python 3, unittest, subprocess (git commands), JSON (Claude's plugin files)

---

## Task 1: Simplify EventData Model

**Files:**
- Modify: `ai-assisted-development/src/lifecycle/models.py:30-40`
- Test: `ai-assisted-development/tests/test_lifecycle_orchestrator.py`

**Step 1: Write failing test for EventData simplification**

```python
# In ai-assisted-development/tests/test_lifecycle_orchestrator.py
# Add to existing test class

def test_event_data_stores_dict_not_json_string(self):
    """EventData should store raw_hook_input as dict."""
    hook_input = {
        "hook_event_name": "SessionStart",
        "session_id": "test-session",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/workspace"
    }

    event_data = EventData(
        hook_event_name="SessionStart",
        raw_hook_input=hook_input
    )

    # Should be dict, not JSON string
    self.assertIsInstance(event_data.raw_hook_input, dict)
    self.assertEqual(event_data.raw_hook_input["session_id"], "test-session")
```

**Step 2: Run test to verify it fails**

Run: `make test-lifecycle`
Expected: FAIL - EventData.__init__() expects 3 arguments (has `fields` parameter)

**Step 3: Update EventData model**

```python
# In ai-assisted-development/src/lifecycle/models.py

@dataclass(frozen=True)
class EventData:
    """Normalized hook input from Claude Code.

    Transforms anthropic's hook input JSON into validated data.
    Common fields: session_id, transcript_path, cwd, hook_event_name.
    Event-specific fields available via .raw_hook_input dict.
    """
    hook_event_name: str
    raw_hook_input: Dict[str, Any]  # Changed from str, removed fields
```

**Step 4: Run test to verify it passes**

Run: `make test-lifecycle`
Expected: FAIL - orchestrator still uses old API (event_data.fields)

**Step 5: Update orchestrator._build_event_data()**

```python
# In ai-assisted-development/src/lifecycle/orchestrator.py

def _build_event_data(self, raw_hook_input: Dict[str, Any]) -> EventData:
    """Extract/validate fields, create EventData."""
    return EventData(
        hook_event_name=raw_hook_input.get("hook_event_name", ""),
        raw_hook_input=raw_hook_input  # No JSON serialization
    )
```

**Step 6: Update all event_data.fields references**

```python
# In ai-assisted-development/src/lifecycle/orchestrator.py
# Replace all occurrences of event_data.fields with event_data.raw_hook_input

# Line ~81, ~122, ~138, ~147, ~159, ~167, ~217
# Change: event_data.fields.get(...)
# To: event_data.raw_hook_input.get(...)
```

**Step 7: Run tests to verify they pass**

Run: `make test-lifecycle`
Expected: PASS

**Step 8: Commit**

```bash
git add ai-assisted-development/src/lifecycle/models.py \
        ai-assisted-development/src/lifecycle/orchestrator.py \
        ai-assisted-development/tests/test_lifecycle_orchestrator.py
git commit -m "refactor: simplify EventData model

Remove .fields attribute, keep raw_hook_input as dict.
Update all references to use raw_hook_input directly."
```

---

## Task 2: Add StatusLine Event Inference and Validation

**Files:**
- Modify: `ai-assisted-development/src/lifecycle/orchestrator.py:109-115`
- Test: `ai-assisted-development/tests/test_lifecycle_orchestrator.py`

**Step 1: Write failing test for input validation**

```python
# In ai-assisted-development/tests/test_lifecycle_orchestrator.py

def test_missing_required_fields_raises_nonblocking_error(self):
    """Missing session_id, transcript_path, or cwd should raise NonBlockingError."""
    from lifecycle.errors import NonBlockingError

    orchestrator = LifecycleOrchestrator()

    # Missing session_id
    with self.assertRaises(NonBlockingError) as cm:
        orchestrator._build_event_data({
            "transcript_path": "/path",
            "cwd": "/workspace"
        })
    self.assertIn("session_id", str(cm.exception))

    # Missing transcript_path
    with self.assertRaises(NonBlockingError):
        orchestrator._build_event_data({
            "session_id": "test",
            "cwd": "/workspace"
        })

    # Missing cwd
    with self.assertRaises(NonBlockingError):
        orchestrator._build_event_data({
            "session_id": "test",
            "transcript_path": "/path"
        })
```

**Step 2: Write failing test for StatusLine inference**

```python
# In ai-assisted-development/tests/test_lifecycle_orchestrator.py

def test_missing_hook_event_name_infers_statusline(self):
    """Missing hook_event_name should be inferred as StatusLine."""
    orchestrator = LifecycleOrchestrator()

    hook_input = {
        "session_id": "test-session",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": "/workspace"
        # No hook_event_name
    }

    event_data = orchestrator._build_event_data(hook_input)

    self.assertEqual(event_data.hook_event_name, "StatusLine")
```

**Step 3: Run tests to verify they fail**

Run: `make test-lifecycle`
Expected: FAIL - _build_event_data() doesn't validate or infer

**Step 4: Implement validation and inference**

```python
# In ai-assisted-development/src/lifecycle/orchestrator.py

def _build_event_data(self, raw_hook_input: Dict[str, Any]) -> EventData:
    """Extract/validate fields, create EventData."""

    # Validate required fields
    session_id = raw_hook_input.get("session_id")
    transcript_path = raw_hook_input.get("transcript_path")
    cwd = raw_hook_input.get("cwd")

    if not session_id or not transcript_path or not cwd:
        raise NonBlockingError(
            f"Invalid hook input: missing required fields "
            f"(session_id={bool(session_id)}, "
            f"transcript_path={bool(transcript_path)}, "
            f"cwd={bool(cwd)})"
        )

    # Infer StatusLine if hook_event_name missing
    hook_event_name = raw_hook_input.get("hook_event_name", "")
    if not hook_event_name:
        hook_event_name = "StatusLine"

    return EventData(
        hook_event_name=hook_event_name,
        raw_hook_input=raw_hook_input
    )
```

**Step 5: Run tests to verify they pass**

Run: `make test-lifecycle`
Expected: PASS

**Step 6: Commit**

```bash
git add ai-assisted-development/src/lifecycle/orchestrator.py \
        ai-assisted-development/tests/test_lifecycle_orchestrator.py
git commit -m "feat: add StatusLine event inference and validation

Validate required fields (session_id, transcript_path, cwd).
Infer StatusLine event when hook_event_name is missing."
```

---

## Task 3: Create Handler Directory Structure

**Files:**
- Create: `ai-assisted-development/src/lifecycle/handlers/__init__.py`
- Create: `ai-assisted-development/src/lifecycle/handlers/base.py`
- Delete: `ai-assisted-development/src/lifecycle/handlers.py`
- Modify: `ai-assisted-development/src/lifecycle/orchestrator.py:11`

**Step 1: Create handlers directory and base.py**

```bash
mkdir -p ai-assisted-development/src/lifecycle/handlers
```

```python
# Create ai-assisted-development/src/lifecycle/handlers/base.py
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
```

**Step 2: Create handlers __init__.py**

```python
# Create ai-assisted-development/src/lifecycle/handlers/__init__.py
"""Event handlers for lifecycle tracking."""

from .base import EventHandler

__all__ = ["EventHandler"]
```

**Step 3: Update orchestrator import**

```python
# In ai-assisted-development/src/lifecycle/orchestrator.py
# Change line ~11:
# from .handlers import EventHandler
# To:
from .handlers import EventHandler
```

**Step 4: Delete old handlers.py**

```bash
git rm ai-assisted-development/src/lifecycle/handlers.py
```

**Step 5: Run tests to verify they pass**

Run: `make test-lifecycle`
Expected: PASS (imports still work)

**Step 6: Commit**

```bash
git add ai-assisted-development/src/lifecycle/handlers/ \
        ai-assisted-development/src/lifecycle/orchestrator.py
git commit -m "refactor: move EventHandler to handlers/ directory

Create handlers package structure.
Move EventHandler ABC to handlers/base.py.
Delete old handlers.py file."
```

---

## Task 4: Add StatusLine Handler Routing

**Files:**
- Modify: `ai-assisted-development/src/lifecycle/orchestrator.py:130-132`
- Test: `ai-assisted-development/tests/test_lifecycle_orchestrator.py`

**Step 1: Write failing test for StatusLine routing**

```python
# In ai-assisted-development/tests/test_lifecycle_orchestrator.py

def test_get_handler_returns_statusline_for_statusline_event(self):
    """_get_handler should return StatusLineHandler for StatusLine events."""
    orchestrator = LifecycleOrchestrator()

    handler = orchestrator._get_handler("StatusLine")

    # Will fail because StatusLineHandler doesn't exist yet
    # For now, just verify it attempts to import
    self.assertIsNotNone(handler)
    self.assertEqual(handler.__class__.__name__, "StatusLineHandler")

def test_get_handler_returns_none_for_other_events(self):
    """_get_handler should return None for events without handlers."""
    orchestrator = LifecycleOrchestrator()

    self.assertIsNone(orchestrator._get_handler("SessionStart"))
    self.assertIsNone(orchestrator._get_handler("UserPromptSubmit"))
    self.assertIsNone(orchestrator._get_handler("UnknownEvent"))
```

**Step 2: Run test to verify it fails**

Run: `make test-lifecycle`
Expected: FAIL - StatusLineHandler doesn't exist

**Step 3: Create minimal StatusLineHandler stub**

```python
# Create ai-assisted-development/src/lifecycle/handlers/statusline.py
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
```

**Step 4: Update handlers __init__.py**

```python
# In ai-assisted-development/src/lifecycle/handlers/__init__.py
from .base import EventHandler
from .statusline import StatusLineHandler

__all__ = ["EventHandler", "StatusLineHandler"]
```

**Step 5: Implement handler routing**

```python
# In ai-assisted-development/src/lifecycle/orchestrator.py

def _get_handler(self, event_name: str) -> Optional[EventHandler]:
    """Route event to handler."""
    if event_name == "StatusLine":
        from .handlers.statusline import StatusLineHandler
        return StatusLineHandler()
    return None
```

**Step 6: Run tests to verify they pass**

Run: `make test-lifecycle`
Expected: PASS

**Step 7: Commit**

```bash
git add ai-assisted-development/src/lifecycle/handlers/ \
        ai-assisted-development/src/lifecycle/orchestrator.py \
        ai-assisted-development/tests/test_lifecycle_orchestrator.py
git commit -m "feat: add StatusLine handler routing

Create StatusLineHandler stub.
Route StatusLine events to handler in orchestrator."
```

---

## Task 5: Implement PluginMetadata Class

**Files:**
- Modify: `ai-assisted-development/src/lifecycle/handlers/statusline.py`
- Create: `ai-assisted-development/tests/test_statusline.py`

**Step 1: Write failing test for PluginMetadata**

```python
# Create ai-assisted-development/tests/test_statusline.py
"""Tests for StatusLine event handler."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from lifecycle.handlers.statusline import PluginMetadata, StatusLineFormatter, StatusLineHandler
from lifecycle.models import RequestContext, EventData
from lifecycle.errors import NonBlockingError


class TestPluginMetadata(unittest.TestCase):
    """Test PluginMetadata class."""

    def setUp(self):
        """Create temporary home directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.home_path = Path(self.temp_dir)
        self.claude_plugins = self.home_path / ".claude" / "plugins"
        self.claude_plugins.mkdir(parents=True)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_reads_installed_plugins_json(self):
        """Should read version, gitCommitSha, installPath from installed_plugins.json."""
        installed_plugins = {
            "version": 1,
            "plugins": {
                "test-plugin@test-marketplace": {
                    "version": "1.0.0",
                    "gitCommitSha": "abc123def456",
                    "installPath": "/path/to/plugin"
                }
            }
        }

        (self.claude_plugins / "installed_plugins.json").write_text(json.dumps(installed_plugins))

        with patch("pathlib.Path.home", return_value=self.home_path):
            metadata = PluginMetadata("test-plugin@test-marketplace", "test-marketplace")

        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.installed_sha, "abc123def456")
        self.assertEqual(metadata.install_path, "/path/to/plugin")

    def test_graceful_fallback_when_plugin_not_found(self):
        """Should use 'unknown' defaults when plugin not in installed_plugins.json."""
        installed_plugins = {"version": 1, "plugins": {}}
        (self.claude_plugins / "installed_plugins.json").write_text(json.dumps(installed_plugins))

        with patch("pathlib.Path.home", return_value=self.home_path):
            metadata = PluginMetadata("nonexistent@marketplace", "marketplace")

        self.assertEqual(metadata.version, "unknown")
        self.assertEqual(metadata.installed_sha, "unknown")
        self.assertEqual(metadata.install_path, "")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest ai-assisted-development/tests/test_statusline.py::TestPluginMetadata::test_reads_installed_plugins_json -v`
Expected: FAIL - PluginMetadata not implemented

**Step 3: Implement PluginMetadata._load() for installed_plugins.json**

```python
# In ai-assisted-development/src/lifecycle/handlers/statusline.py

import json
import subprocess
from pathlib import Path
from typing import Optional


class PluginMetadata:
    """Plugin installation metadata from Claude Code."""

    def __init__(self, plugin_id: str, marketplace_id: str):
        self.plugin_id = plugin_id
        self.marketplace_id = marketplace_id

        # Default values
        self.version = "unknown"
        self.installed_sha = "unknown"
        self.current_sha = ""
        self.install_path = ""
        self.is_dev_mode = False
        self.needs_warning = False

        self._load()

    def _load(self):
        """Load metadata from Claude's JSON files and git."""
        try:
            # Read installed_plugins.json
            installed_path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
            if installed_path.exists():
                data = json.loads(installed_path.read_text())
                plugin = data.get("plugins", {}).get(self.plugin_id, {})
                if plugin:
                    self.version = plugin.get("version", "unknown")
                    self.installed_sha = plugin.get("gitCommitSha", "unknown")
                    self.install_path = plugin.get("installPath", "")
        except Exception:
            # Graceful fallback on any error
            pass
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest ai-assisted-development/tests/test_statusline.py::TestPluginMetadata::test_reads_installed_plugins_json -v`
Expected: PASS

**Step 5: Add test for dev mode detection**

```python
# In ai-assisted-development/tests/test_statusline.py

def test_detects_dev_mode_from_known_marketplaces(self):
    """Should detect dev mode when source.source == 'directory'."""
    installed_plugins = {
        "version": 1,
        "plugins": {
            "test-plugin@test-marketplace": {
                "version": "1.0.0",
                "gitCommitSha": "abc123",
                "installPath": "/path/to/plugin"
            }
        }
    }

    known_marketplaces = {
        "test-marketplace": {
            "source": {
                "source": "directory",
                "path": "/path/to/marketplace"
            },
            "installLocation": "/path/to/marketplace"
        }
    }

    (self.claude_plugins / "installed_plugins.json").write_text(json.dumps(installed_plugins))
    (self.claude_plugins / "known_marketplaces.json").write_text(json.dumps(known_marketplaces))

    with patch("pathlib.Path.home", return_value=self.home_path):
        metadata = PluginMetadata("test-plugin@test-marketplace", "test-marketplace")

    self.assertTrue(metadata.is_dev_mode)

def test_not_dev_mode_when_source_is_github(self):
    """Should not be dev mode when source is github."""
    installed_plugins = {
        "version": 1,
        "plugins": {
            "test-plugin@test-marketplace": {
                "version": "1.0.0",
                "gitCommitSha": "abc123",
                "installPath": "/path/to/plugin"
            }
        }
    }

    known_marketplaces = {
        "test-marketplace": {
            "source": {
                "source": "github",
                "repo": "owner/repo"
            },
            "installLocation": "/path/to/marketplace"
        }
    }

    (self.claude_plugins / "installed_plugins.json").write_text(json.dumps(installed_plugins))
    (self.claude_plugins / "known_marketplaces.json").write_text(json.dumps(known_marketplaces))

    with patch("pathlib.Path.home", return_value=self.home_path):
        metadata = PluginMetadata("test-plugin@test-marketplace", "test-marketplace")

    self.assertFalse(metadata.is_dev_mode)
```

**Step 6: Run tests to verify they fail**

Run: `python -m pytest ai-assisted-development/tests/test_statusline.py::TestPluginMetadata -v`
Expected: FAIL - dev mode detection not implemented

**Step 7: Implement dev mode detection**

```python
# In ai-assisted-development/src/lifecycle/handlers/statusline.py
# Update _load() method

def _load(self):
    """Load metadata from Claude's JSON files and git."""
    try:
        # Read installed_plugins.json
        installed_path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
        if installed_path.exists():
            data = json.loads(installed_path.read_text())
            plugin = data.get("plugins", {}).get(self.plugin_id, {})
            if plugin:
                self.version = plugin.get("version", "unknown")
                self.installed_sha = plugin.get("gitCommitSha", "unknown")
                self.install_path = plugin.get("installPath", "")

        # Read known_marketplaces.json for dev mode detection
        marketplaces_path = Path.home() / ".claude" / "plugins" / "known_marketplaces.json"
        if marketplaces_path.exists():
            data = json.loads(marketplaces_path.read_text())
            marketplace = data.get(self.marketplace_id, {})
            source = marketplace.get("source", {})
            self.is_dev_mode = source.get("source") == "directory"
    except Exception:
        # Graceful fallback on any error
        pass
```

**Step 8: Add test for git SHA checking**

```python
# In ai-assisted-development/tests/test_statusline.py

def test_runs_git_in_dev_mode(self):
    """Should run git rev-parse HEAD in dev mode."""
    installed_plugins = {
        "version": 1,
        "plugins": {
            "test-plugin@test-marketplace": {
                "version": "1.0.0",
                "gitCommitSha": "abc123",
                "installPath": "/path/to/plugin"
            }
        }
    }

    known_marketplaces = {
        "test-marketplace": {
            "source": {"source": "directory"},
            "installLocation": "/path/to/marketplace"
        }
    }

    (self.claude_plugins / "installed_plugins.json").write_text(json.dumps(installed_plugins))
    (self.claude_plugins / "known_marketplaces.json").write_text(json.dumps(known_marketplaces))

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "def456789\n"

    with patch("pathlib.Path.home", return_value=self.home_path), \
         patch("subprocess.run", return_value=mock_result) as mock_run:
        metadata = PluginMetadata("test-plugin@test-marketplace", "test-marketplace")

    # Verify git was called
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    self.assertEqual(args[0], "git")
    self.assertEqual(args[1], "-C")
    self.assertEqual(args[3], "rev-parse")
    self.assertEqual(args[4], "HEAD")

    self.assertEqual(metadata.current_sha, "def456789")

def test_sets_needs_warning_when_shas_differ(self):
    """Should set needs_warning=True when installed_sha != current_sha."""
    installed_plugins = {
        "version": 1,
        "plugins": {
            "test-plugin@test-marketplace": {
                "version": "1.0.0",
                "gitCommitSha": "abc123",
                "installPath": "/path/to/plugin"
            }
        }
    }

    known_marketplaces = {
        "test-marketplace": {
            "source": {"source": "directory"},
            "installLocation": "/path/to/marketplace"
        }
    }

    (self.claude_plugins / "installed_plugins.json").write_text(json.dumps(installed_plugins))
    (self.claude_plugins / "known_marketplaces.json").write_text(json.dumps(known_marketplaces))

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "different_sha\n"

    with patch("pathlib.Path.home", return_value=self.home_path), \
         patch("subprocess.run", return_value=mock_result):
        metadata = PluginMetadata("test-plugin@test-marketplace", "test-marketplace")

    self.assertTrue(metadata.needs_warning)

def test_does_not_run_git_when_not_dev_mode(self):
    """Should not run git when not in dev mode."""
    installed_plugins = {
        "version": 1,
        "plugins": {
            "test-plugin@test-marketplace": {
                "version": "1.0.0",
                "gitCommitSha": "abc123",
                "installPath": "/path/to/plugin"
            }
        }
    }

    (self.claude_plugins / "installed_plugins.json").write_text(json.dumps(installed_plugins))
    # No known_marketplaces.json - not dev mode

    with patch("pathlib.Path.home", return_value=self.home_path), \
         patch("subprocess.run") as mock_run:
        metadata = PluginMetadata("test-plugin@test-marketplace", "test-marketplace")

    mock_run.assert_not_called()
    self.assertFalse(metadata.is_dev_mode)
    self.assertEqual(metadata.current_sha, "")
```

**Step 9: Run tests to verify they fail**

Run: `python -m pytest ai-assisted-development/tests/test_statusline.py::TestPluginMetadata -v`
Expected: FAIL - git operations not implemented

**Step 10: Implement git SHA checking**

```python
# In ai-assisted-development/src/lifecycle/handlers/statusline.py
# Update _load() method

def _load(self):
    """Load metadata from Claude's JSON files and git."""
    try:
        # Read installed_plugins.json
        installed_path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
        if installed_path.exists():
            data = json.loads(installed_path.read_text())
            plugin = data.get("plugins", {}).get(self.plugin_id, {})
            if plugin:
                self.version = plugin.get("version", "unknown")
                self.installed_sha = plugin.get("gitCommitSha", "unknown")
                self.install_path = plugin.get("installPath", "")

        # Read known_marketplaces.json for dev mode detection
        marketplaces_path = Path.home() / ".claude" / "plugins" / "known_marketplaces.json"
        if marketplaces_path.exists():
            data = json.loads(marketplaces_path.read_text())
            marketplace = data.get(self.marketplace_id, {})
            source = marketplace.get("source", {})
            self.is_dev_mode = source.get("source") == "directory"

        # Run git in dev mode
        if self.is_dev_mode and self.install_path:
            try:
                result = subprocess.run(
                    ["git", "-C", self.install_path, "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    self.current_sha = result.stdout.strip()
                    # Check if warning needed
                    if self.current_sha and self.installed_sha != "unknown":
                        self.needs_warning = (self.current_sha != self.installed_sha)
            except Exception:
                # Git failed - leave current_sha empty
                pass
    except Exception:
        # Graceful fallback on any error
        pass
```

**Step 11: Run tests to verify they pass**

Run: `python -m pytest ai-assisted-development/tests/test_statusline.py::TestPluginMetadata -v`
Expected: PASS

**Step 12: Commit**

```bash
git add ai-assisted-development/src/lifecycle/handlers/statusline.py \
        ai-assisted-development/tests/test_statusline.py
git commit -m "feat: implement PluginMetadata class

Read plugin metadata from Claude's JSON files.
Detect dev mode from marketplace source.
Run git to compare SHAs in dev mode."
```

---

## Task 6: Implement StatusLineFormatter Class

**Files:**
- Modify: `ai-assisted-development/src/lifecycle/handlers/statusline.py`
- Test: `ai-assisted-development/tests/test_statusline.py`

**Step 1: Write failing test for formatter**

```python
# In ai-assisted-development/tests/test_statusline.py

class TestStatusLineFormatter(unittest.TestCase):
    """Test StatusLineFormatter class."""

    def test_plugin_not_installed_message(self):
        """Should show 'Plugin not installed' when version is unknown."""
        metadata = PluginMetadata.__new__(PluginMetadata)
        metadata.plugin_id = "test-plugin@test-marketplace"
        metadata.version = "unknown"
        metadata.install_path = ""

        context = RequestContext(
            session_id="test-session",
            request_id="test-request",
            request_dir=Path("/workspace/.toolbox/events/test-request"),
            transcript_path=Path("/path/to/transcript"),
            agent_types={},
            start_uuid=None
        )

        formatter = StatusLineFormatter()
        output = formatter.format(metadata, context)

        self.assertIn("Plugin not installed", output)
        self.assertIn("⚠️", output)

    def test_normal_mode_output(self):
        """Should show single SHA line in normal mode."""
        metadata = PluginMetadata.__new__(PluginMetadata)
        metadata.plugin_id = "test-plugin@test-marketplace"
        metadata.version = "1.0.0"
        metadata.installed_sha = "abc123def456"
        metadata.current_sha = ""
        metadata.install_path = "/path/to/plugin"
        metadata.needs_warning = False

        context = RequestContext(
            session_id="test-session",
            request_id="2025-12-11T00-15-32_e36738f5",
            request_dir=Path("/home/user/.toolbox/events/2025-12-11T00-15-32_e36738f5"),
            transcript_path=Path("/path/to/transcript"),
            agent_types={},
            start_uuid=None
        )

        formatter = StatusLineFormatter()
        output = formatter.format(metadata, context)

        self.assertIn("test-plugin@test-marketplace: v1.0.0", output)
        self.assertIn("📦 Installed: abc123d", output)  # 7 chars
        self.assertIn("📁 Request: 2025-12-11T00-15-32_e36738f5", output)
        self.assertIn("💾 ~/.toolbox/events/2025-12-11T00-15-32_e36738f5/", output)
        self.assertNotIn("Current:", output)  # Not dev mode

    def test_dev_mode_warning_output(self):
        """Should show both SHAs and warning in dev mode."""
        metadata = PluginMetadata.__new__(PluginMetadata)
        metadata.plugin_id = "test-plugin@test-marketplace"
        metadata.version = "1.0.0"
        metadata.installed_sha = "abc123def456"
        metadata.current_sha = "fedcba987654"
        metadata.install_path = "/path/to/plugin"
        metadata.needs_warning = True

        context = RequestContext(
            session_id="test-session",
            request_id="test-request",
            request_dir=Path("/home/user/.toolbox/events/test-request"),
            transcript_path=Path("/path/to/transcript"),
            agent_types={},
            start_uuid=None
        )

        formatter = StatusLineFormatter()
        output = formatter.format(metadata, context)

        self.assertIn("test-plugin@test-marketplace: v1.0.0 ⚠️", output)
        self.assertIn("📦 Installed: abc123d | Current: fedcba9", output)

    def test_no_active_request(self):
        """Should show 'No active request' when request_id empty."""
        metadata = PluginMetadata.__new__(PluginMetadata)
        metadata.plugin_id = "test-plugin@test-marketplace"
        metadata.version = "1.0.0"
        metadata.installed_sha = "abc123"
        metadata.install_path = "/path"
        metadata.needs_warning = False

        context = RequestContext(
            session_id="test-session",
            request_id="",  # Empty
            request_dir=Path(""),
            transcript_path=Path("/path/to/transcript"),
            agent_types={},
            start_uuid=None
        )

        formatter = StatusLineFormatter()
        output = formatter.format(metadata, context)

        self.assertIn("📁 No active request", output)
        self.assertNotIn("💾", output)  # No path line
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest ai-assisted-development/tests/test_statusline.py::TestStatusLineFormatter -v`
Expected: FAIL - StatusLineFormatter not implemented

**Step 3: Implement StatusLineFormatter**

```python
# In ai-assisted-development/src/lifecycle/handlers/statusline.py

class StatusLineFormatter:
    """Formats status line output."""

    def format(self, metadata: PluginMetadata, context: RequestContext) -> str:
        """Build formatted status line string.

        Args:
            metadata: Plugin state (version, SHAs, paths, dev mode)
            context: Request context (request_id, request_dir)

        Returns:
            Multi-line status string
        """
        lines = []

        # Check if plugin is installed
        if metadata.version == "unknown" or not metadata.install_path:
            lines.append(f"{metadata.plugin_id}: ⚠️  Plugin not installed.")
            return "\n".join(lines)

        # Plugin version line
        if metadata.needs_warning:
            lines.append(f"{metadata.plugin_id}: v{metadata.version} ⚠️")
            lines.append(
                f"📦 Installed: {metadata.installed_sha[:7]} | "
                f"Current: {metadata.current_sha[:7]}"
            )
        else:
            lines.append(f"{metadata.plugin_id}: v{metadata.version}")
            lines.append(f"📦 Installed: {metadata.installed_sha[:7]}")

        # Request info
        if context.request_id:
            lines.append(f"📁 Request: {context.request_id}")

            # Abbreviate home directory
            display_path = str(context.request_dir)
            home_str = str(Path.home())
            if display_path.startswith(home_str):
                display_path = "~" + display_path[len(home_str):]
            lines.append(f"💾 {display_path}/")
        else:
            lines.append("📁 No active request")

        return "\n".join(lines)
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest ai-assisted-development/tests/test_statusline.py::TestStatusLineFormatter -v`
Expected: PASS

**Step 5: Commit**

```bash
git add ai-assisted-development/src/lifecycle/handlers/statusline.py \
        ai-assisted-development/tests/test_statusline.py
git commit -m "feat: implement StatusLineFormatter class

Format status output matching bash script.
Handle plugin not installed, normal mode, dev mode warnings.
Abbreviate home directory in paths."
```

---

## Task 7: Complete StatusLineHandler Implementation

**Files:**
- Modify: `ai-assisted-development/src/lifecycle/handlers/statusline.py`
- Test: `ai-assisted-development/tests/test_statusline.py`

**Step 1: Write failing test for handler**

```python
# In ai-assisted-development/tests/test_statusline.py

class TestStatusLineHandler(unittest.TestCase):
    """Test StatusLineHandler class."""

    def test_handler_prints_formatted_output(self):
        """Handler should create metadata, format, and print output."""
        context = RequestContext(
            session_id="test-session",
            request_id="test-request",
            request_dir=Path("/workspace/.toolbox/events/test-request"),
            transcript_path=Path("/path/to/transcript"),
            agent_types={},
            start_uuid=None
        )

        event_data = EventData(
            hook_event_name="StatusLine",
            raw_hook_input={"session_id": "test", "cwd": "/workspace", "transcript_path": "/path"}
        )

        handler = StatusLineHandler()

        with patch("builtins.print") as mock_print, \
             patch.object(PluginMetadata, "_load"):  # Skip actual file reads
            result = handler.handle(context, event_data)

        # Should print something
        mock_print.assert_called_once()
        output = mock_print.call_args[0][0]
        self.assertIsInstance(output, str)

        # Should return unchanged context
        self.assertEqual(result, context)

    def test_handler_raises_nonblocking_error_on_failure(self):
        """Handler should raise NonBlockingError if metadata or formatter fails."""
        context = RequestContext(
            session_id="test-session",
            request_id="test-request",
            request_dir=Path("/workspace/.toolbox/events/test-request"),
            transcript_path=Path("/path/to/transcript"),
            agent_types={},
            start_uuid=None
        )

        event_data = EventData(
            hook_event_name="StatusLine",
            raw_hook_input={"session_id": "test", "cwd": "/workspace", "transcript_path": "/path"}
        )

        handler = StatusLineHandler()

        # Make PluginMetadata raise an exception
        with patch.object(PluginMetadata, "_load", side_effect=Exception("Test error")):
            with self.assertRaises(NonBlockingError) as cm:
                handler.handle(context, event_data)

            self.assertIn("StatusLine failed", str(cm.exception))
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest ai-assisted-development/tests/test_statusline.py::TestStatusLineHandler -v`
Expected: FAIL - handler stub doesn't do real work

**Step 3: Complete StatusLineHandler implementation**

```python
# In ai-assisted-development/src/lifecycle/handlers/statusline.py

class StatusLineHandler(EventHandler):
    """Handler for StatusLine hook events."""

    PLUGIN_ID = "ai-assisted-development@claude-code-toolbox"
    MARKETPLACE_ID = "claude-code-toolbox"

    def handle(self, context: RequestContext, event_data: EventData) -> RequestContext:
        """Build and print statusline.

        Args:
            context: Request context from orchestrator
            event_data: Hook input data

        Returns:
            Unchanged context

        Raises:
            NonBlockingError: On any failure (logged to stderr, exits 1)
        """
        try:
            metadata = PluginMetadata(self.PLUGIN_ID, self.MARKETPLACE_ID)
            formatter = StatusLineFormatter()
            output = formatter.format(metadata, context)
            print(output)
            return context
        except Exception as e:
            raise NonBlockingError(f"StatusLine failed: {e}")
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest ai-assisted-development/tests/test_statusline.py::TestStatusLineHandler -v`
Expected: PASS

**Step 5: Run all statusline tests**

Run: `python -m pytest ai-assisted-development/tests/test_statusline.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add ai-assisted-development/src/lifecycle/handlers/statusline.py \
        ai-assisted-development/tests/test_statusline.py
git commit -m "feat: complete StatusLineHandler implementation

Orchestrate PluginMetadata, StatusLineFormatter, and output.
Raise NonBlockingError on failures."
```

---

## Task 8: Integration Testing

**Files:**
- Test: Manual testing with statusline_input.txt

**Step 1: Test with actual statusline input**

```bash
# Feed actual statusline hook input to agent-lifecycle.py
cat statusline_input.txt | python ai-assisted-development/src/agent-lifecycle.py
```

Expected output (similar to):
```
ai-assisted-development@claude-code-toolbox: v1.0.0
📦 Installed: 898edc0
📁 No active request
```

**Step 2: Verify output format matches bash script**

```bash
# Compare with bash script output (if plugin installed)
cat statusline_input.txt | bash ai-assisted-development/src/statusline.sh
```

Outputs should match in format (exact SHAs may differ based on installation).

**Step 3: Test with missing plugin files**

```bash
# Temporarily rename plugin files
mv ~/.claude/plugins/installed_plugins.json ~/.claude/plugins/installed_plugins.json.bak

cat statusline_input.txt | python ai-assisted-development/src/agent-lifecycle.py

# Should show: "Plugin not installed"

# Restore files
mv ~/.claude/plugins/installed_plugins.json.bak ~/.claude/plugins/installed_plugins.json
```

**Step 4: Test error handling**

```bash
# Feed invalid input (missing required fields)
echo '{"session_id": "test"}' | python ai-assisted-development/src/agent-lifecycle.py

# Should exit 1 with error to stderr about missing fields
# Exit code check:
echo $?  # Should be 1
```

**Step 5: Verify exit codes**

```bash
# Success case
cat statusline_input.txt | python ai-assisted-development/src/agent-lifecycle.py
echo $?  # Should be 0

# Error case (invalid input)
echo '{}' | python ai-assisted-development/src/agent-lifecycle.py 2>/dev/null
echo $?  # Should be 1
```

**Note:** No commit for manual testing.

---

## Task 9: Run Full Test Suite

**Step 1: Run all lifecycle tests**

Run: `make test-lifecycle`
Expected: ALL PASS

**Step 2: Run all tests**

Run: `make test`
Expected: ALL PASS

**Step 3: Fix any failing tests**

If tests fail, investigate and fix. Common issues:
- Import errors from restructuring
- Missing test updates for EventData changes
- Mock expectations not matching implementation

**Step 4: Commit any test fixes**

```bash
git add .
git commit -m "test: fix test issues from statusline implementation"
```

---

## Task 10: Delete Bash Script

**Files:**
- Delete: `ai-assisted-development/src/statusline.sh`

**Step 1: Verify Python implementation works**

```bash
# One final verification
cat statusline_input.txt | python ai-assisted-development/src/agent-lifecycle.py
```

Expected: Proper statusline output, exit 0

**Step 2: Delete bash script**

```bash
git rm ai-assisted-development/src/statusline.sh
```

**Step 3: Run tests to ensure nothing breaks**

Run: `make test`
Expected: ALL PASS

**Step 4: Commit**

```bash
git commit -m "remove: delete statusline.sh bash script

Replaced by StatusLineHandler in Python.
Use agent-lifecycle.py as universal entry point."
```

---

## Task 11: Update Documentation

**Files:**
- Modify: `ai-assisted-development/README.md` (if statusline mentioned)
- Modify: `CONTRIBUTING.md` (if statusline setup documented)

**Step 1: Check if statusline is documented**

```bash
grep -r "statusline" README.md CONTRIBUTING.md docs/
```

**Step 2: Update references to use Python instead of bash**

If found, update examples to use `agent-lifecycle.py` instead of `statusline.sh`.

**Step 3: Commit documentation updates**

```bash
git add README.md CONTRIBUTING.md docs/
git commit -m "docs: update statusline references to use Python

Replace statusline.sh with agent-lifecycle.py in examples."
```

Note: Skip if no documentation updates needed.

---

## Final Verification

**Step 1: Run complete test suite**

Run: `make test`
Expected: ALL PASS

**Step 2: Test installation in devcontainer**

```bash
make install-plugin
```

Expected: Plugin installs successfully

**Step 3: Verify in real Claude Code session**

After user manually updates settings.json:
```json
{
  "statusLine": {
    "type": "command",
    "command": "python ${CLAUDE_PLUGIN_ROOT}/src/agent-lifecycle.py"
  }
}
```

Start Claude Code and verify statusline appears correctly.

**Step 4: Review commit history**

```bash
git log --oneline --graph
```

Expected: Clean, logical commits following TDD pattern

---

## Success Criteria

- [ ] All tests pass (`make test`)
- [ ] EventData simplified (no .fields attribute)
- [ ] StatusLine event inference works
- [ ] Handler directory structure established
- [ ] PluginMetadata reads Claude's JSON files and git
- [ ] StatusLineFormatter produces correct output
- [ ] StatusLineHandler orchestrates and prints
- [ ] Integration test passes with statusline_input.txt
- [ ] Bash script deleted
- [ ] Documentation updated
- [ ] Clean commit history following TDD

**Implementation complete!** StatusLine is now an event handler in the lifecycle system.
