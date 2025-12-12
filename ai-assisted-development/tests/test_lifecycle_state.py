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
