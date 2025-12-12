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


if __name__ == "__main__":
    unittest.main()
