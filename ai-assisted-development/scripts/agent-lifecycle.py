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
    elif event_name == "SessionEnd":
        handle_session_end(hook_input)
    elif event_name == "PostToolUseFailure":
        handle_post_tool_use_failure(hook_input)
    elif event_name == "PermissionRequest":
        handle_permission_request(hook_input)
    else:
        print(f"[agent-lifecycle] Unknown event: {event_name}", file=sys.stderr)
        sys.exit(1)


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
    """Handle SubagentStart event (new hook as of ~3 weeks ago)."""
    log_path = log_hook_event("SubagentStart", hook_input)
    agent_name = extract_agent_name(hook_input)

    if agent_name:
        print(f"[SubagentStart] {agent_name} starting")
    else:
        print(f"[SubagentStart] Subagent starting")

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
