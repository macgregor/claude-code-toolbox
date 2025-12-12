"""Tests for StatusLine event handler."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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
        with patch("lifecycle.handlers.statusline.Path.home", return_value=Path("/home/user")):
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


if __name__ == "__main__":
    unittest.main()
