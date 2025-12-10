#!/usr/bin/env python3
"""
Universal agent lifecycle hook handler.
Handles SubagentStart and SubagentStop events for all agents.
"""

import json
import sys
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


def handle_start(hook_input):
    """Handle SubagentStart event."""
    print(f"[SubagentStart] Initialized")
    sys.exit(0)


def handle_stop(hook_input):
    """Handle SubagentStop event."""
    print(f"[SubagentStop] Completed")
    sys.exit(0)


if __name__ == "__main__":
    main()
