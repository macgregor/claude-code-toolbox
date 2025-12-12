"""Integration test for full lifecycle refactoring."""

import unittest
import sys
import tempfile
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lifecycle import LifecycleOrchestrator


class TestLifecycleIntegration(unittest.TestCase):
    """End-to-end test simulating real hook events."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = LifecycleOrchestrator()
        self.session_log = Path(self.temp_dir) / "session.jsonl"
        # Store and clear TOOLBOX_ROOT to ensure test isolation
        self.old_toolbox_root = os.environ.get("TOOLBOX_ROOT")
        if "TOOLBOX_ROOT" in os.environ:
            del os.environ["TOOLBOX_ROOT"]

    def tearDown(self):
        # Restore TOOLBOX_ROOT
        if self.old_toolbox_root is not None:
            os.environ["TOOLBOX_ROOT"] = self.old_toolbox_root

    def test_full_lifecycle_flow(self):
        """Test complete flow: SessionStart -> UserPromptSubmit -> SubagentStart -> SubagentStop -> Stop."""

        # 1. SessionStart
        self.orchestrator.process({
            "hook_event_name": "SessionStart",
            "cwd": self.temp_dir,
            "session_id": "sess-integration"
        })

        events_dir = Path(self.temp_dir) / ".toolbox" / "events"
        self.assertTrue(events_dir.exists())

        # 2. UserPromptSubmit
        self.session_log.write_text(json.dumps({
            "type": "user",
            "uuid": "uuid-start",
            "message": {"content": "help me implement feature X"}
        }) + '\n')

        self.orchestrator.process({
            "hook_event_name": "UserPromptSubmit",
            "cwd": self.temp_dir,
            "session_id": "sess-integration",
            "timestamp": "2025-12-11T10:00:00",
            "prompt": "help me implement feature X",
            "transcript_path": str(self.session_log)
        })

        request_dirs = [d for d in events_dir.iterdir() if d.is_dir()]
        self.assertEqual(len(request_dirs), 1)
        request_dir = request_dirs[0]

        context_file = request_dir / "context.md"
        self.assertTrue(context_file.exists())
        self.assertIn("help me implement feature X", context_file.read_text())

        # 3. SubagentStart
        self.orchestrator.process({
            "hook_event_name": "SubagentStart",
            "cwd": self.temp_dir,
            "session_id": "sess-integration",
            "agent_id": "agent-explore",
            "agent_type": "Explore",
            "transcript_path": str(self.session_log)
        })

        state_file = request_dir / ".state.json"
        state_data = json.loads(state_file.read_text())
        self.assertEqual(state_data["agent_types"]["agent-explore"], "Explore")

        # 4. SubagentStop
        agent_transcript = Path(self.temp_dir) / "agent-explore.jsonl"
        agent_transcript.write_text(json.dumps({
            "type": "assistant",
            "message": {
                "content": [{
                    "type": "text",
                    "text": "I found the relevant code. <context>The feature X implementation should go in src/feature_x.py</context>"
                }]
            }
        }))

        self.orchestrator.process({
            "hook_event_name": "SubagentStop",
            "cwd": self.temp_dir,
            "session_id": "sess-integration",
            "agent_id": "agent-explore",
            "agent_transcript_path": str(agent_transcript),
            "transcript_path": str(self.session_log)
        })

        context_content = context_file.read_text()
        self.assertIn("feature X implementation", context_content)
        self.assertIn('<agent-agent-explore type="Explore">', context_content)

        # 5. Stop
        self.session_log.write_text(
            self.session_log.read_text() +
            json.dumps({"type": "assistant", "message": {"content": "Done"}}) + '\n'
        )

        self.orchestrator.process({
            "hook_event_name": "Stop",
            "cwd": self.temp_dir,
            "session_id": "sess-integration",
            "transcript_path": str(self.session_log)
        })

        pruned_log = request_dir / "session-logs" / "sess-integration-pruned.jsonl"
        self.assertTrue(pruned_log.exists())


if __name__ == "__main__":
    unittest.main()
