import unittest
import sys
import tempfile
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle.orchestrator import LifecycleOrchestrator


class TestLifecycleOrchestrator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = LifecycleOrchestrator()
        # Store and clear TOOLBOX_ROOT to ensure test isolation
        self.old_toolbox_root = os.environ.get("TOOLBOX_ROOT")
        if "TOOLBOX_ROOT" in os.environ:
            del os.environ["TOOLBOX_ROOT"]

    def tearDown(self):
        # Restore TOOLBOX_ROOT
        if self.old_toolbox_root is not None:
            os.environ["TOOLBOX_ROOT"] = self.old_toolbox_root

    def test_creates_instance(self):
        """LifecycleOrchestrator should instantiate."""
        self.assertIsInstance(self.orchestrator, LifecycleOrchestrator)

    def test_process_returns_without_toolbox_root(self):
        """process() should return early if no toolbox_root."""
        hook_input = {"hook_event_name": "SessionStart"}
        # Should not raise
        self.orchestrator.process(hook_input)

    def test_process_returns_without_request_id(self):
        """process() should return early if no request_id found for session."""
        hook_input = {
            "hook_event_name": "Stop",
            "cwd": self.temp_dir,
            "session_id": "session-unknown",
            "transcript_path": str(Path(self.temp_dir) / "session.jsonl")
        }
        # Should not raise - just returns early
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
        request_dirs = [d for d in events_dir.iterdir() if d.is_dir()]
        self.assertEqual(len(request_dirs), 1)

        # Should create context.md
        context_file = request_dirs[0] / "context.md"
        self.assertTrue(context_file.exists())
        content = context_file.read_text()
        self.assertIn("test prompt", content)
        self.assertIn("<userPrompt>", content)

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
        request_dir = [d for d in events_dir.iterdir() if d.is_dir()][0]
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
        request_dir = [d for d in events_dir.iterdir() if d.is_dir()][0]
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

    def test_event_data_stores_dict_not_json_string(self):
        """EventData should store raw_hook_input as dict."""
        hook_input = {
            "hook_event_name": "SessionStart",
            "session_id": "test-session",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": "/workspace"
        }

        event_data = self.orchestrator._build_event_data(hook_input)

        # Should be dict, not JSON string
        self.assertIsInstance(event_data.raw_hook_input, dict)
        self.assertEqual(event_data.raw_hook_input["session_id"], "test-session")

    def test_missing_required_fields_raises_nonblocking_error(self):
        """Missing session_id, transcript_path, or cwd should raise NonBlockingError."""
        from lifecycle.errors import NonBlockingError

        orchestrator = LifecycleOrchestrator()

        # Missing session_id (no hook_event_name, so inferred as StatusLine)
        with self.assertRaises(NonBlockingError) as cm:
            orchestrator._build_event_data({
                "transcript_path": "/path",
                "cwd": "/workspace"
            })
        self.assertIn("session_id", str(cm.exception))

        # Missing transcript_path (no hook_event_name, so inferred as StatusLine)
        with self.assertRaises(NonBlockingError):
            orchestrator._build_event_data({
                "session_id": "test",
                "cwd": "/workspace"
            })

        # Missing cwd (no hook_event_name, so inferred as StatusLine)
        with self.assertRaises(NonBlockingError):
            orchestrator._build_event_data({
                "session_id": "test",
                "transcript_path": "/path"
            })

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


if __name__ == "__main__":
    unittest.main()
