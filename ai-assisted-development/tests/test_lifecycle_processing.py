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
        # Temporarily unset TOOLBOX_ROOT to test fallback
        old_value = os.environ.pop("TOOLBOX_ROOT", None)
        try:
            result = get_toolbox_root({"cwd": "/hook/path"})
            self.assertEqual(result, "/hook/path")
        finally:
            if old_value is not None:
                os.environ["TOOLBOX_ROOT"] = old_value


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
