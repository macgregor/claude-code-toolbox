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
