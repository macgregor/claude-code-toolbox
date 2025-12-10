#!/usr/bin/env python3
"""
Universal agent lifecycle hook handler.
Handles all hook events: PreToolUse, PostToolUse, UserPromptSubmit, Stop,
SessionStart, PreCompact, Notification, SubagentStart, SubagentStop.
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

    if event_name == "PreToolUse":
        handle_pre_tool_use(hook_input)
    elif event_name == "PostToolUse":
        handle_post_tool_use(hook_input)
    elif event_name == "UserPromptSubmit":
        handle_user_prompt_submit(hook_input)
    elif event_name == "Stop":
        handle_stop_event(hook_input)
    elif event_name == "SessionStart":
        handle_session_start(hook_input)
    elif event_name == "PreCompact":
        handle_pre_compact(hook_input)
    elif event_name == "Notification":
        handle_notification(hook_input)
    elif event_name == "SubagentStart":
        handle_subagent_start(hook_input)
    elif event_name == "SubagentStop":
        handle_subagent_stop(hook_input)
    else:
        print(f"[agent-lifecycle] Unknown event: {event_name}", file=sys.stderr)
        sys.exit(1)


def log_hook_event(event_name, hook_input):
    """Log hook event data to single JSONL file for debugging and analysis."""
    # Create log directory in project workspace
    log_dir = Path("/workspace/tmp")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "hook-events.jsonl"

    # Add timestamp to hook input
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_name,
        **hook_input
    }

    # Append to JSONL file (one JSON object per line)
    with open(log_file, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

    return log_file


def extract_agent_name(hook_input):
    """Extract agent name from hook input."""
    # Try these fields in order:
    agent_name = (
        hook_input.get("subagent_type") or
        hook_input.get("agent_id") or
        hook_input.get("agent_name")
    )

    if not agent_name:
        # For non-subagent hooks, this is expected
        return None

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


def handle_pre_tool_use(hook_input):
    """Handle PreToolUse event."""
    log_path = log_hook_event("PreToolUse", hook_input)
    tool_name = hook_input.get("tool_name", "unknown")
    print(f"[PreToolUse] Tool: {tool_name}")
    print(f"Logged to: {log_path}")
    sys.exit(0)


def handle_post_tool_use(hook_input):
    """Handle PostToolUse event."""
    log_path = log_hook_event("PostToolUse", hook_input)
    tool_name = hook_input.get("tool_name", "unknown")
    print(f"[PostToolUse] Tool: {tool_name}")
    print(f"Logged to: {log_path}")
    sys.exit(0)


def handle_user_prompt_submit(hook_input):
    """Handle UserPromptSubmit event."""
    log_path = log_hook_event("UserPromptSubmit", hook_input)
    print(f"[UserPromptSubmit] User prompt received")
    print(f"Logged to: {log_path}")
    sys.exit(0)


def handle_stop_event(hook_input):
    """Handle Stop event."""
    log_path = log_hook_event("Stop", hook_input)
    print(f"[Stop] Session stopping")
    print(f"Logged to: {log_path}")
    sys.exit(0)


def handle_session_start(hook_input):
    """Handle SessionStart event."""
    log_path = log_hook_event("SessionStart", hook_input)
    print(f"[SessionStart] New session starting")
    print(f"Logged to: {log_path}")
    sys.exit(0)


def handle_pre_compact(hook_input):
    """Handle PreCompact event."""
    log_path = log_hook_event("PreCompact", hook_input)
    print(f"[PreCompact] Context compaction starting")
    print(f"Logged to: {log_path}")
    sys.exit(0)


def handle_notification(hook_input):
    """Handle Notification event."""
    log_path = log_hook_event("Notification", hook_input)
    notification_type = hook_input.get("notification_type", "unknown")
    print(f"[Notification] Type: {notification_type}")
    print(f"Logged to: {log_path}")
    sys.exit(0)


def handle_subagent_start(hook_input):
    """Handle SubagentStart event."""
    log_path = log_hook_event("SubagentStart", hook_input)
    agent_name = extract_agent_name(hook_input)

    # Create workspace
    workspace = Path(f"/tmp/{agent_name}-workspace")
    workspace.mkdir(parents=True, exist_ok=True)

    print(f"[SubagentStart] {agent_name} initialized")
    print(f"Workspace: {workspace}")
    print(f"Logged to: {log_path}")
    sys.exit(0)


def handle_subagent_stop(hook_input):
    """Handle SubagentStop event."""
    log_path = log_hook_event("SubagentStop", hook_input)
    agent_name = extract_agent_name(hook_input)

    # Get transcript path
    transcript_path = hook_input.get("agent_transcript_path")
    if not transcript_path:
        print(f"[SubagentStop] No transcript path, skipping output extraction", file=sys.stderr)
        sys.exit(0)

    # Only extract JSON for document-reviewer agent
    # Other agents may not output pure JSON
    if agent_name == "document-reviewer":
        try:
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
        except Exception as e:
            print(f"[SubagentStop] Failed to extract JSON: {e}", file=sys.stderr)
    else:
        print(f"[SubagentStop] {agent_name} completed (no JSON extraction)")

    print(f"Logged to: {log_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
