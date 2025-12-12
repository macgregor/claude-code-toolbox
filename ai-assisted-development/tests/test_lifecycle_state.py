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

    def test_nested_dict_modification_marks_dirty(self):
        """Nested dict modifications should automatically mark StateFile as dirty."""
        sf = StateFile(self.state_path)
        sf["agent_types"] = {}
        sf.save()
        self.assertFalse(sf._dirty)

        sf["agent_types"]["agent-123"] = "explore"
        self.assertTrue(sf._dirty)

    def test_deep_nested_dict_modification_marks_dirty(self):
        """Deep nested dict modifications should mark StateFile as dirty."""
        sf = StateFile(self.state_path)
        sf["config"] = {"nested": {}}
        sf.save()
        self.assertFalse(sf._dirty)

        sf["config"]["nested"]["deep"] = "value"
        self.assertTrue(sf._dirty)

    def test_nested_dict_persists_correctly(self):
        """Nested dict modifications should persist to JSON."""
        sf = StateFile(self.state_path)
        sf["agent_types"] = {}
        sf["agent_types"]["agent-123"] = "explore"
        sf["agent_types"]["agent-456"] = "plan"
        sf.save()

        loaded = json.loads(self.state_path.read_text())
        self.assertEqual(loaded["agent_types"]["agent-123"], "explore")
        self.assertEqual(loaded["agent_types"]["agent-456"], "plan")

    def test_nested_dict_reloads_correctly(self):
        """Nested dicts should reload from JSON and remain tracked."""
        sf = StateFile(self.state_path)
        sf["agent_types"] = {"agent-123": "explore"}
        sf.save()

        sf2 = StateFile(self.state_path)
        self.assertFalse(sf2._dirty)
        sf2["agent_types"]["agent-456"] = "plan"
        self.assertTrue(sf2._dirty)

    def test_dict_update_marks_dirty(self):
        """update() method should mark StateFile as dirty."""
        sf = StateFile(self.state_path)
        sf["data"] = {}
        sf.save()

        sf["data"].update({"key": "value"})
        self.assertTrue(sf._dirty)

    def test_dict_pop_marks_dirty(self):
        """pop() method should mark StateFile as dirty."""
        sf = StateFile(self.state_path)
        sf["data"] = {"key": "value"}
        sf.save()

        sf["data"].pop("key")
        self.assertTrue(sf._dirty)

    def test_dict_popitem_marks_dirty(self):
        """popitem() method should mark StateFile as dirty."""
        sf = StateFile(self.state_path)
        sf["data"] = {"key": "value"}
        sf.save()

        sf["data"].popitem()
        self.assertTrue(sf._dirty)

    def test_dict_clear_marks_dirty(self):
        """clear() method should mark StateFile as dirty."""
        sf = StateFile(self.state_path)
        sf["data"] = {"key": "value"}
        sf.save()

        sf["data"].clear()
        self.assertTrue(sf._dirty)

    def test_dict_setdefault_marks_dirty(self):
        """setdefault() should mark dirty when key doesn't exist."""
        sf = StateFile(self.state_path)
        sf["data"] = {}
        sf.save()

        nested = sf["data"].setdefault("key", {})
        self.assertTrue(sf._dirty)
        sf.save()

        nested["value"] = "test"
        self.assertTrue(sf._dirty)

    def test_dict_setdefault_no_dirty_when_exists(self):
        """setdefault() should not mark dirty when key exists."""
        sf = StateFile(self.state_path)
        sf["data"] = {"key": {"existing": "value"}}
        sf.save()

        result = sf["data"].setdefault("key", {})
        self.assertFalse(sf._dirty)
        self.assertEqual(result["existing"], "value")


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
