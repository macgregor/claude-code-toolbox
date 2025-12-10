#!/usr/bin/env python3
"""
Universal agent lifecycle hook handler.
Handles SubagentStart and SubagentStop events for all agents.
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def main():
    """Read hook input and dispatch to appropriate handler."""
    # Read hook input from stdin
    hook_input = json.load(sys.stdin)

    # Log input for debugging (TEMPORARY - remove after validation)
    debug_log = Path("/tmp/hook-debug.log")
    with open(debug_log, "a") as f:
        f.write(f"\n=== Hook Input ===\n")
        f.write(json.dumps(hook_input, indent=2))
        f.write("\n")

    # Dispatch based on event
    event_name = hook_input.get("hook_event_name")

    if event_name == "SubagentStart":
        handle_start(hook_input)
    elif event_name == "SubagentStop":
        handle_stop(hook_input)
    else:
        print(f"[agent-lifecycle] Unknown event: {event_name}", file=sys.stderr)
        sys.exit(1)


def extract_agent_name(hook_input):
    """Extract agent name from hook input."""
    # ADJUST THIS based on Task 3 findings
    # Try these fields in order:
    agent_name = (
        hook_input.get("subagent_type") or
        hook_input.get("agent_id") or
        hook_input.get("agent_name")
    )

    if not agent_name:
        print(f"[agent-lifecycle] ERROR: Cannot find agent name in hook input", file=sys.stderr)
        print(f"Available fields: {list(hook_input.keys())}", file=sys.stderr)
        sys.exit(2)

    # If name contains plugin prefix, extract base name
    # e.g., "ai-assisted-development:document-reviewer" -> "document-reviewer"
    if ":" in agent_name:
        agent_name = agent_name.split(":")[-1]

    return agent_name


def handle_start(hook_input):
    """Handle SubagentStart event."""
    agent_name = extract_agent_name(hook_input)

    # Create workspace
    workspace = Path(f"/tmp/{agent_name}-workspace")
    workspace.mkdir(parents=True, exist_ok=True)

    print(f"[SubagentStart] {agent_name} initialized")
    print(f"Workspace: {workspace}")
    sys.exit(0)


def handle_stop(hook_input):
    """Handle SubagentStop event."""
    print(f"[SubagentStop] Completed")
    sys.exit(0)


if __name__ == "__main__":
    main()
