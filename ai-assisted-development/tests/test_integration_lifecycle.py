"""Integration test for full lifecycle refactoring."""

import unittest
import sys
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle import LifecycleOrchestrator
from lifecycle.errors import NonBlockingError


class TestLifecycleIntegration(unittest.TestCase):
    """End-to-end test simulating real hook events."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = LifecycleOrchestrator()
        self.session_log = Path(self.temp_dir) / "session.jsonl"
        # Store and clear TOOLBOX_ROOT to ensure test isolation
        self.old_toolbox_root = os.environ.get("TOOLBOX_ROOT")
        if "TOOLBOX_ROOT" in os.environ:
            del os.environ["TOOLBOX_ROOT"]

    def tearDown(self):
        # Restore TOOLBOX_ROOT
        if self.old_toolbox_root is not None:
            os.environ["TOOLBOX_ROOT"] = self.old_toolbox_root

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

        request_dirs = [d for d in events_dir.iterdir() if d.is_dir()]
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

    def test_statusline_event_calls_handler_and_prints(self):
        """StatusLine event should invoke handler and print output."""
        # Create minimal global state
        events_dir = Path(self.temp_dir) / ".toolbox" / "events"
        events_dir.mkdir(parents=True)

        global_state = {
            "session_requests": {
                "test-session-123": "2025-12-12T10-00-00_abc123"
            }
        }
        (events_dir / ".global-state.json").write_text(json.dumps(global_state))

        # Create request directory and state
        request_dir = events_dir / "2025-12-12T10-00-00_abc123"
        request_dir.mkdir(parents=True)
        (request_dir / ".state.json").write_text(json.dumps({}))

        # StatusLine hook input (no hook_event_name)
        hook_input = {
            "session_id": "test-session-123",
            "transcript_path": str(Path(self.temp_dir) / "transcript.jsonl"),
            "cwd": self.temp_dir
        }

        with patch("builtins.print") as mock_print, \
             patch("lifecycle.handlers.statusline.PluginMetadata._load"):  # Skip file I/O
            self.orchestrator.process(hook_input)

        # Verify print was called (handler executed)
        mock_print.assert_called_once()
        output = mock_print.call_args[0][0]
        self.assertIsInstance(output, str)
        self.assertTrue(len(output) > 0)

    def test_statusline_does_not_persist_state(self):
        """StatusLine should not append to hook-events.jsonl."""
        # Create minimal global state
        events_dir = Path(self.temp_dir) / ".toolbox" / "events"
        events_dir.mkdir(parents=True)

        global_state = {
            "session_requests": {
                "test-session-456": "2025-12-12T10-00-00_def456"
            }
        }
        (events_dir / ".global-state.json").write_text(json.dumps(global_state))

        # Create request directory
        request_dir = events_dir / "2025-12-12T10-00-00_def456"
        request_dir.mkdir(parents=True)
        (request_dir / ".state.json").write_text(json.dumps({}))

        hook_input = {
            "session_id": "test-session-456",
            "transcript_path": str(Path(self.temp_dir) / "transcript.jsonl"),
            "cwd": self.temp_dir
        }

        with patch("builtins.print"), \
             patch("lifecycle.handlers.statusline.PluginMetadata._load"):
            self.orchestrator.process(hook_input)

        # Verify hook-events.jsonl was NOT created
        hook_events = request_dir / "hook-events.jsonl"
        self.assertFalse(hook_events.exists())

    def test_statusline_validates_required_fields(self):
        """StatusLine should raise NonBlockingError if required fields missing."""
        # Missing session_id
        hook_input = {
            "transcript_path": "/path/to/transcript",
            "cwd": self.temp_dir
        }

        with self.assertRaises(NonBlockingError) as cm:
            self.orchestrator.process(hook_input)

        self.assertIn("missing required fields", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
