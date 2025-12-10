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
    hook_input = json.load(sys.stdin)

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


def extract_json_from_transcript(transcript_path):
    """Extract final assistant message from agent transcript and parse as JSON."""
    try:
        with open(transcript_path) as f:
            transcript = json.load(f)
    except Exception as e:
        print(f"[SubagentStop] ERROR: Cannot read transcript: {e}", file=sys.stderr)
        sys.exit(2)

    # Get last assistant message
    agent_output = None
    for message in reversed(transcript):
        if message.get("role") == "assistant":
            agent_output = message.get("content", "")
            break

    if not agent_output:
        print(f"[SubagentStop] ERROR: No assistant message in transcript", file=sys.stderr)
        sys.exit(2)

    # Parse as JSON
    try:
        data = json.loads(agent_output)
        return data
    except json.JSONDecodeError as e:
        print(f"[SubagentStop] ERROR: Invalid JSON in agent output", file=sys.stderr)
        print(f"JSON error: {e}", file=sys.stderr)
        print(f"Agent output preview: {agent_output[:200]}...", file=sys.stderr)
        sys.exit(2)


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
    agent_name = extract_agent_name(hook_input)

    # Get transcript path
    transcript_path = hook_input.get("agent_transcript_path")
    if not transcript_path:
        print(f"[SubagentStop] ERROR: No agent_transcript_path in hook input", file=sys.stderr)
        sys.exit(2)

    # Extract JSON
    data = extract_json_from_transcript(transcript_path)

    # Create output directory
    output_dir = Path(f"/tmp/{agent_name}-output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    filename = f"{agent_name}-{timestamp}.json"
    output_path = output_dir / filename

    # Write output
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"[SubagentStop] {agent_name} completed")
    print(f"Output: {output_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
