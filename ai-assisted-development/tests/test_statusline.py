"""Tests for standalone statusline script."""

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from statusline import PluginMetadata, format_statusline, main


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
        shutil.rmtree(self.temp_dir)

    def test_reads_installed_plugins_json(self):
        """Should read version, gitCommitSha, installPath from installed_plugins.json."""
        installed_plugins = {
            "version": 2,
            "plugins": {
                "test-plugin@test-marketplace": [
                    {
                        "scope": "user",
                        "version": "1.0.0",
                        "gitCommitSha": "abc123def456",
                        "installPath": "/path/to/plugin"
                    }
                ]
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

    def test_reads_v1_dict_format(self):
        """Should handle old v1 format where plugin entry is a dict, not an array."""
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

    def test_detects_dev_mode_from_known_marketplaces(self):
        """Should detect dev mode when source.source == 'directory'."""
        installed_plugins = {
            "version": 2,
            "plugins": {
                "test-plugin@test-marketplace": [
                    {
                        "scope": "user",
                        "version": "1.0.0",
                        "gitCommitSha": "abc123",
                        "installPath": "/path/to/plugin"
                    }
                ]
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
            "version": 2,
            "plugins": {
                "test-plugin@test-marketplace": [
                    {
                        "scope": "user",
                        "version": "1.0.0",
                        "gitCommitSha": "abc123",
                        "installPath": "/path/to/plugin"
                    }
                ]
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

    def test_runs_git_in_source_path(self):
        """Should run git in source repo path, not install cache path."""
        installed_plugins = {
            "version": 2,
            "plugins": {
                "test-plugin@test-marketplace": [
                    {
                        "scope": "user",
                        "version": "1.0.0",
                        "gitCommitSha": "abc123",
                        "installPath": "/path/to/cache/plugin"
                    }
                ]
            }
        }

        known_marketplaces = {
            "test-marketplace": {
                "source": {"source": "directory", "path": "/path/to/source/repo"},
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

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args[2], "/path/to/source/repo")

    def test_runs_git_in_dev_mode(self):
        """Should fall back to install path when source path not available."""
        installed_plugins = {
            "version": 2,
            "plugins": {
                "test-plugin@test-marketplace": [
                    {
                        "scope": "user",
                        "version": "1.0.0",
                        "gitCommitSha": "abc123",
                        "installPath": "/path/to/plugin"
                    }
                ]
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
            "version": 2,
            "plugins": {
                "test-plugin@test-marketplace": [
                    {
                        "scope": "user",
                        "version": "1.0.0",
                        "gitCommitSha": "abc123",
                        "installPath": "/path/to/plugin"
                    }
                ]
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
            "version": 2,
            "plugins": {
                "test-plugin@test-marketplace": [
                    {
                        "scope": "user",
                        "version": "1.0.0",
                        "gitCommitSha": "abc123",
                        "installPath": "/path/to/plugin"
                    }
                ]
            }
        }

        (self.claude_plugins / "installed_plugins.json").write_text(json.dumps(installed_plugins))

        with patch("pathlib.Path.home", return_value=self.home_path), \
             patch("subprocess.run") as mock_run:
            metadata = PluginMetadata("test-plugin@test-marketplace", "test-marketplace")

        mock_run.assert_not_called()
        self.assertFalse(metadata.is_dev_mode)
        self.assertEqual(metadata.current_sha, "")


class TestFormatStatusline(unittest.TestCase):
    """Test format_statusline function."""

    def _make_metadata(self, **overrides):
        """Create a PluginMetadata without calling _load."""
        metadata = PluginMetadata.__new__(PluginMetadata)
        metadata.plugin_id = "test-plugin@test-marketplace"
        metadata.version = "1.0.0"
        metadata.installed_sha = "abc123def456"
        metadata.current_sha = ""
        metadata.install_path = "/path/to/plugin"
        metadata.is_dev_mode = False
        metadata.needs_warning = False
        for key, value in overrides.items():
            setattr(metadata, key, value)
        return metadata

    def test_plugin_not_installed_message(self):
        """Should show 'Plugin not installed' when version is unknown."""
        metadata = self._make_metadata(version="unknown", install_path="")
        output = format_statusline(metadata)

        self.assertIn("Plugin not installed", output)

    def test_plugin_not_installed_when_no_install_path(self):
        """Should show 'Plugin not installed' when install_path is empty."""
        metadata = self._make_metadata(install_path="")
        output = format_statusline(metadata)

        self.assertIn("Plugin not installed", output)

    def test_normal_mode_output(self):
        """Should show version and single SHA line in normal mode."""
        metadata = self._make_metadata()
        output = format_statusline(metadata)

        self.assertIn("test-plugin@test-marketplace: v1.0.0", output)
        self.assertIn("Installed: abc123d", output)
        self.assertNotIn("Current:", output)

    def test_dev_mode_warning_output(self):
        """Should show both SHAs and warning in dev mode."""
        metadata = self._make_metadata(
            current_sha="fedcba987654",
            needs_warning=True
        )
        output = format_statusline(metadata)

        self.assertIn("test-plugin@test-marketplace: v1.0.0", output)
        self.assertIn("Installed: abc123d | Current: fedcba9", output)

    def test_warning_emoji_present(self):
        """Should include warning emoji when needs_warning is True."""
        metadata = self._make_metadata(
            current_sha="fedcba987654",
            needs_warning=True
        )
        output = format_statusline(metadata)

        self.assertIn("v1.0.0 ⚠️", output)


class TestMain(unittest.TestCase):
    """Test main() function."""

    def test_consumes_stdin_and_prints_output(self):
        """Should read stdin JSON and print statusline to stdout."""
        stdin_data = json.dumps({"session_id": "test", "cwd": "/workspace"})

        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("builtins.print") as mock_print, \
             patch.object(PluginMetadata, "_load"):
            main()

        mock_print.assert_called_once()
        output = mock_print.call_args[0][0]
        self.assertIsInstance(output, str)

    def test_handles_empty_stdin(self):
        """Should not crash when stdin is empty."""
        with patch("sys.stdin", io.StringIO("")), \
             patch("builtins.print") as mock_print, \
             patch.object(PluginMetadata, "_load"):
            main()

        mock_print.assert_called_once()


if __name__ == "__main__":
    unittest.main()
