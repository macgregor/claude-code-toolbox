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


if __name__ == "__main__":
    unittest.main()
