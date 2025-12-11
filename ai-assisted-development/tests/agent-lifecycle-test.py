#!/usr/bin/env python3
"""
Unit tests for agent-lifecycle.py
Uses Python's built-in unittest module (no third-party dependencies).
"""

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import agent_lifecycle module
spec = importlib.util.spec_from_file_location(
    "agent_lifecycle",
    Path(__file__).parent.parent / "scripts" / "agent-lifecycle.py"
)
agent_lifecycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_lifecycle)


class TestGetToolboxRoot(unittest.TestCase):
    """Test get_toolbox_root() function"""

    def test_returns_env_var_when_set(self):
        """Returns TOOLBOX_ROOT from environment variable when set"""
        with patch.dict(os.environ, {"TOOLBOX_ROOT": "/test/root"}):
            result = agent_lifecycle.get_toolbox_root()
            self.assertEqual(result, "/test/root")

    def test_fallback_to_claude_env_file(self):
        """Falls back to parsing CLAUDE_ENV_FILE when env var not set"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('export TOOLBOX_ROOT="/from/file"\n')
            env_file_path = f.name

        try:
            with patch.dict(os.environ, {"CLAUDE_ENV_FILE": env_file_path}, clear=True):
                result = agent_lifecycle.get_toolbox_root()
                self.assertEqual(result, "/from/file")
        finally:
            os.unlink(env_file_path)

    def test_fallback_to_cwd_from_hook_input(self):
        """Falls back to cwd from hook_input when env sources fail"""
        hook_input = {"cwd": "/fallback/cwd"}
        with patch.dict(os.environ, {}, clear=True):
            result = agent_lifecycle.get_toolbox_root(hook_input)
            self.assertEqual(result, "/fallback/cwd")

    def test_returns_empty_string_when_all_fail(self):
        """Returns empty string when all fallback options fail"""
        with patch.dict(os.environ, {}, clear=True):
            result = agent_lifecycle.get_toolbox_root()
            self.assertEqual(result, "")


class TestGenerateRequestId(unittest.TestCase):
    """Test generate_request_id() function"""

    def test_deterministic_same_input_same_id(self):
        """Same input produces same ID"""
        hook_input = {
            "session_id": "test-session",
            "timestamp": "2025-12-10T10:30:00",
            "prompt": "test prompt"
        }
        id1 = agent_lifecycle.generate_request_id(hook_input)
        id2 = agent_lifecycle.generate_request_id(hook_input)
        self.assertEqual(id1, id2)

    def test_format_timestamp_hash(self):
        """Format is {timestamp}_{hash} with 8-char hash"""
        hook_input = {
            "session_id": "test",
            "timestamp": "2025-12-10T10:30:00",
            "prompt": "test"
        }
        result = agent_lifecycle.generate_request_id(hook_input)
        parts = result.split('_')
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0], "2025-12-10T10-30-00")
        self.assertEqual(len(parts[1]), 8)

    def test_handles_missing_timestamp(self):
        """Handles missing timestamp by generating current time"""
        hook_input = {"session_id": "test", "prompt": "test"}
        result = agent_lifecycle.generate_request_id(hook_input)
        self.assertIsNotNone(result)
        self.assertIn('_', result)

    def test_colons_replaced_with_dashes(self):
        """Colons replaced with dashes in timestamp"""
        hook_input = {
            "session_id": "test",
            "timestamp": "2025-12-10T10:30:00",
            "prompt": "test"
        }
        result = agent_lifecycle.generate_request_id(hook_input)
        self.assertNotIn(':', result.split('_')[0])


class TestCreateRequestDirectory(unittest.TestCase):
    """Test create_request_directory() function"""

    def test_creates_directory_structure(self):
        """Creates .toolbox/events/{request-id}/ with subdirs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            request_id = "test-request-id"
            result = agent_lifecycle.create_request_directory(tmpdir, request_id)

            self.assertTrue(result.exists())
            self.assertTrue((result / "work").exists())
            self.assertTrue((result / "session-logs").exists())
            self.assertTrue((result / "hook-events.jsonl").exists())
            self.assertTrue((result / "errors.log").exists())

    def test_idempotent_no_error_on_rerun(self):
        """Idempotent - no error when run multiple times"""
        with tempfile.TemporaryDirectory() as tmpdir:
            request_id = "test-request-id"
            agent_lifecycle.create_request_directory(tmpdir, request_id)
            # Should not raise error
            result = agent_lifecycle.create_request_directory(tmpdir, request_id)
            self.assertTrue(result.exists())


class TestParseContextTags(unittest.TestCase):
    """Test parse_context_tags() function"""

    def test_extracts_single_context_tag(self):
        """Extracts single context tag"""
        text = "<context>Test context content</context>"
        result = agent_lifecycle.parse_context_tags(text)
        self.assertEqual(result, ["Test context content"])

    def test_extracts_multiple_context_tags(self):
        """Extracts multiple context tags"""
        text = "<context>First</context> some text <context>Second</context>"
        result = agent_lifecycle.parse_context_tags(text)
        self.assertEqual(result, ["First", "Second"])

    def test_handles_empty_text(self):
        """Handles empty text"""
        result = agent_lifecycle.parse_context_tags("")
        self.assertEqual(result, [])

    def test_handles_no_context_tags(self):
        """Handles text with no context tags"""
        result = agent_lifecycle.parse_context_tags("No tags here")
        self.assertEqual(result, [])

    def test_strips_whitespace_from_content(self):
        """Strips whitespace from content"""
        text = "<context>  \n  Test content  \n  </context>"
        result = agent_lifecycle.parse_context_tags(text)
        self.assertEqual(result, ["Test content"])


class TestParseWorkTags(unittest.TestCase):
    """Test parse_work_tags() function - NEW behavior with filename attribute"""

    def test_extracts_single_work_tag_with_filename(self):
        """Extracts single work tag with filename attribute"""
        text = '<work filename="report.json">{"test": "data"}</work>'
        result = agent_lifecycle.parse_work_tags(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["filename"], "report.json")
        self.assertEqual(result[0]["content"], '{"test": "data"}')

    def test_extracts_multiple_work_tags(self):
        """Extracts multiple work tags"""
        text = '<work filename="file1.txt">content1</work><work filename="file2.txt">content2</work>'
        result = agent_lifecycle.parse_work_tags(text)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["filename"], "file1.txt")
        self.assertEqual(result[1]["filename"], "file2.txt")

    def test_returns_correct_dict_structure(self):
        """Returns {"filename": ..., "content": ...} dict structure"""
        text = '<work filename="test.txt">content</work>'
        result = agent_lifecycle.parse_work_tags(text)
        self.assertEqual(set(result[0].keys()), {"filename", "content"})

    def test_handles_empty_text(self):
        """Handles empty text"""
        result = agent_lifecycle.parse_work_tags("")
        self.assertEqual(result, [])

    def test_strips_whitespace_from_content(self):
        """Strips whitespace from content"""
        text = '<work filename="test.txt">  \n  content  \n  </work>'
        result = agent_lifecycle.parse_work_tags(text)
        self.assertEqual(result[0]["content"], "content")

    def test_does_not_match_old_relpath_attribute(self):
        """Does NOT match old relpath attribute"""
        text = '<work relpath="old/path.txt">content</work>'
        result = agent_lifecycle.parse_work_tags(text)
        self.assertEqual(result, [])


class TestHandleSubagentStopWorkTags(unittest.TestCase):
    """Test handle_subagent_stop() work tag handling"""

    def setUp(self):
        """Set up temp directory for tests"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.toolbox_root = self.tmpdir.name
        self.request_id = "test-request"
        self.request_dir = agent_lifecycle.create_request_directory(
            self.toolbox_root, self.request_id
        )

        # Create current request ID file
        events_dir = Path(self.toolbox_root) / ".toolbox" / "events"
        (events_dir / ".current-request-id").write_text(self.request_id)

    def tearDown(self):
        """Clean up temp directory"""
        self.tmpdir.cleanup()

    def _create_agent_transcript(self, final_output):
        """Helper to create agent transcript file"""
        transcript_dir = Path(self.tmpdir.name) / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = transcript_dir / "agent-test.jsonl"

        message = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": final_output}]
            }
        }
        transcript_path.write_text(json.dumps(message) + '\n')
        return str(transcript_path)

    def test_writes_file_to_work_subdirectory(self):
        """Writes file to work/ subdirectory"""
        final_output = '<work filename="test.txt">content</work>'
        transcript_path = self._create_agent_transcript(final_output)

        hook_input = {
            "agent_id": "test123",
            "agent_type": "test-agent",
            "agent_transcript_path": transcript_path,
            "cwd": self.toolbox_root
        }

        with patch.dict(os.environ, {"TOOLBOX_ROOT": self.toolbox_root}):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_subagent_stop(hook_input)
            self.assertEqual(cm.exception.code, 0)

        work_file = self.request_dir / "work" / "test.txt"
        self.assertTrue(work_file.exists())
        self.assertEqual(work_file.read_text(), "content")

    def test_validates_filename_no_slash(self):
        """Exits with code 1 on invalid filename with /"""
        final_output = '<work filename="path/to/file.txt">content</work>'
        transcript_path = self._create_agent_transcript(final_output)

        hook_input = {
            "agent_id": "test123",
            "agent_type": "test-agent",
            "agent_transcript_path": transcript_path,
            "cwd": self.toolbox_root
        }

        with patch.dict(os.environ, {"TOOLBOX_ROOT": self.toolbox_root}):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_subagent_stop(hook_input)
            self.assertEqual(cm.exception.code, 1)

    def test_validates_filename_no_backslash(self):
        """Exits with code 1 on invalid filename with \\"""
        final_output = '<work filename="path\\\\file.txt">content</work>'
        transcript_path = self._create_agent_transcript(final_output)

        hook_input = {
            "agent_id": "test123",
            "agent_type": "test-agent",
            "agent_transcript_path": transcript_path,
            "cwd": self.toolbox_root
        }

        with patch.dict(os.environ, {"TOOLBOX_ROOT": self.toolbox_root}):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_subagent_stop(hook_input)
            self.assertEqual(cm.exception.code, 1)

    def test_validates_filename_no_dotdot(self):
        """Exits with code 1 on invalid filename with .."""
        final_output = '<work filename="../file.txt">content</work>'
        transcript_path = self._create_agent_transcript(final_output)

        hook_input = {
            "agent_id": "test123",
            "agent_type": "test-agent",
            "agent_transcript_path": transcript_path,
            "cwd": self.toolbox_root
        }

        with patch.dict(os.environ, {"TOOLBOX_ROOT": self.toolbox_root}):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_subagent_stop(hook_input)
            self.assertEqual(cm.exception.code, 1)

    def test_validates_duplicate_filename(self):
        """Exits with code 1 on duplicate filename"""
        # Create existing file
        (self.request_dir / "work" / "test.txt").write_text("existing")

        final_output = '<work filename="test.txt">new content</work>'
        transcript_path = self._create_agent_transcript(final_output)

        hook_input = {
            "agent_id": "test123",
            "agent_type": "test-agent",
            "agent_transcript_path": transcript_path,
            "cwd": self.toolbox_root
        }

        with patch.dict(os.environ, {"TOOLBOX_ROOT": self.toolbox_root}):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_subagent_stop(hook_input)
            self.assertEqual(cm.exception.code, 1)

    def test_handles_multiple_work_tags(self):
        """Handles multiple work tags"""
        final_output = '<work filename="file1.txt">content1</work><work filename="file2.txt">content2</work>'
        transcript_path = self._create_agent_transcript(final_output)

        hook_input = {
            "agent_id": "test123",
            "agent_type": "test-agent",
            "agent_transcript_path": transcript_path,
            "cwd": self.toolbox_root
        }

        with patch.dict(os.environ, {"TOOLBOX_ROOT": self.toolbox_root}):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_subagent_stop(hook_input)
            self.assertEqual(cm.exception.code, 0)

        self.assertTrue((self.request_dir / "work" / "file1.txt").exists())
        self.assertTrue((self.request_dir / "work" / "file2.txt").exists())


class TestHandleSubagentStopContextTags(unittest.TestCase):
    """Test handle_subagent_stop() context tag handling"""

    def setUp(self):
        """Set up temp directory for tests"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.toolbox_root = self.tmpdir.name
        self.request_id = "test-request"
        self.request_dir = agent_lifecycle.create_request_directory(
            self.toolbox_root, self.request_id
        )

        # Initialize context.md
        (self.request_dir / "context.md").write_text("<userPrompt>test</userPrompt>\n")

        # Create current request ID file
        events_dir = Path(self.toolbox_root) / ".toolbox" / "events"
        (events_dir / ".current-request-id").write_text(self.request_id)

    def tearDown(self):
        """Clean up temp directory"""
        self.tmpdir.cleanup()

    def _create_agent_transcript(self, final_output):
        """Helper to create agent transcript file"""
        transcript_dir = Path(self.tmpdir.name) / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = transcript_dir / "agent-test.jsonl"

        message = {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": final_output}]
            }
        }
        transcript_path.write_text(json.dumps(message) + '\n')
        return str(transcript_path)

    def test_appends_context_to_context_md(self):
        """Appends context to context.md"""
        final_output = '<context>Test context</context>'
        transcript_path = self._create_agent_transcript(final_output)

        hook_input = {
            "agent_id": "abc123",
            "agent_type": "test-agent",
            "agent_transcript_path": transcript_path,
            "cwd": self.toolbox_root
        }

        with patch.dict(os.environ, {"TOOLBOX_ROOT": self.toolbox_root}):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_subagent_stop(hook_input)
            self.assertEqual(cm.exception.code, 0)

        context_content = (self.request_dir / "context.md").read_text()
        self.assertIn("Test context", context_content)

    def test_wraps_in_agent_tags(self):
        """Wraps in <agent-{id} type="{type}"> tags"""
        final_output = '<context>Test context</context>'
        transcript_path = self._create_agent_transcript(final_output)

        hook_input = {
            "agent_id": "abc123",
            "agent_type": "test-agent",
            "agent_transcript_path": transcript_path,
            "cwd": self.toolbox_root
        }

        with patch.dict(os.environ, {"TOOLBOX_ROOT": self.toolbox_root}):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_subagent_stop(hook_input)
            self.assertEqual(cm.exception.code, 0)

        context_content = (self.request_dir / "context.md").read_text()
        self.assertIn('<agent-abc123 type="test-agent">', context_content)
        self.assertIn('</agent-abc123>', context_content)

    def test_handles_multiple_context_tags(self):
        """Handles multiple context tags"""
        final_output = '<context>First</context><context>Second</context>'
        transcript_path = self._create_agent_transcript(final_output)

        hook_input = {
            "agent_id": "abc123",
            "agent_type": "test-agent",
            "agent_transcript_path": transcript_path,
            "cwd": self.toolbox_root
        }

        with patch.dict(os.environ, {"TOOLBOX_ROOT": self.toolbox_root}):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_subagent_stop(hook_input)
            self.assertEqual(cm.exception.code, 0)

        context_content = (self.request_dir / "context.md").read_text()
        self.assertIn("First", context_content)
        self.assertIn("Second", context_content)


class TestHandleUserPromptSubmit(unittest.TestCase):
    """Test handle_user_prompt_submit() function"""

    def setUp(self):
        """Set up temp directory"""
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        """Clean up temp directory"""
        self.tmpdir.cleanup()

    def test_generates_request_id(self):
        """Generates request ID"""
        hook_input = {
            "cwd": self.tmpdir.name,
            "session_id": "test",
            "timestamp": "2025-12-10T10:30:00",
            "prompt": "test prompt"
        }

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_user_prompt_submit(hook_input)
            self.assertEqual(cm.exception.code, 0)

        current_id_file = Path(self.tmpdir.name) / ".toolbox" / "events" / ".current-request-id"
        self.assertTrue(current_id_file.exists())

    def test_writes_to_current_request_id(self):
        """Writes to .current-request-id"""
        hook_input = {
            "cwd": self.tmpdir.name,
            "session_id": "test",
            "timestamp": "2025-12-10T10:30:00",
            "prompt": "test prompt"
        }

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_user_prompt_submit(hook_input)
            self.assertEqual(cm.exception.code, 0)

        current_id_file = Path(self.tmpdir.name) / ".toolbox" / "events" / ".current-request-id"
        request_id = current_id_file.read_text().strip()
        self.assertIn("2025-12-10T10-30-00", request_id)

    def test_creates_request_directory(self):
        """Creates request directory"""
        hook_input = {
            "cwd": self.tmpdir.name,
            "session_id": "test",
            "timestamp": "2025-12-10T10:30:00",
            "prompt": "test prompt"
        }

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_user_prompt_submit(hook_input)
            self.assertEqual(cm.exception.code, 0)

        current_id_file = Path(self.tmpdir.name) / ".toolbox" / "events" / ".current-request-id"
        request_id = current_id_file.read_text().strip()
        request_dir = Path(self.tmpdir.name) / ".toolbox" / "events" / request_id

        self.assertTrue(request_dir.exists())
        self.assertTrue((request_dir / "work").exists())

    def test_initializes_context_md_with_user_prompt(self):
        """Initializes context.md with user prompt"""
        hook_input = {
            "cwd": self.tmpdir.name,
            "session_id": "test",
            "timestamp": "2025-12-10T10:30:00",
            "prompt": "test prompt"
        }

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                agent_lifecycle.handle_user_prompt_submit(hook_input)
            self.assertEqual(cm.exception.code, 0)

        current_id_file = Path(self.tmpdir.name) / ".toolbox" / "events" / ".current-request-id"
        request_id = current_id_file.read_text().strip()
        context_file = Path(self.tmpdir.name) / ".toolbox" / "events" / request_id / "context.md"

        self.assertTrue(context_file.exists())
        content = context_file.read_text()
        self.assertIn("test prompt", content)
        self.assertIn("<userPrompt>", content)


class TestAppendToRequestEvents(unittest.TestCase):
    """Test append_to_request_events() function"""

    def setUp(self):
        """Set up temp directory"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.toolbox_root = self.tmpdir.name

    def tearDown(self):
        """Clean up temp directory"""
        self.tmpdir.cleanup()

    def test_appends_when_request_active(self):
        """Appends to hook-events.jsonl when request active"""
        request_id = "test-request"
        request_dir = agent_lifecycle.create_request_directory(
            self.toolbox_root, request_id
        )

        # Create current request ID file
        events_dir = Path(self.toolbox_root) / ".toolbox" / "events"
        (events_dir / ".current-request-id").write_text(request_id)

        hook_input = {"test": "data"}
        agent_lifecycle.append_to_request_events(hook_input, self.toolbox_root)

        hook_events_file = request_dir / "hook-events.jsonl"
        content = hook_events_file.read_text()
        self.assertIn('"test"', content)

    def test_does_nothing_when_no_request_active(self):
        """Does nothing when no request active"""
        hook_input = {"test": "data"}
        # No exception should be raised
        agent_lifecycle.append_to_request_events(hook_input, self.toolbox_root)


if __name__ == "__main__":
    unittest.main()
