#!/usr/bin/env python3
"""
Universal agent lifecycle hook handler.
Handles all hook events: PreToolUse, PostToolUse, UserPromptSubmit, Stop,
SessionStart, PreCompact, Notification, SubagentStart, SubagentStop.
"""

import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, List


def generate_request_id(hook_input: Dict[str, Any]) -> str:
    """Generate deterministic request ID: {timestamp}_{hash}"""
    session_id = hook_input.get("session_id", "")
    timestamp = hook_input.get("timestamp", "")
    prompt = hook_input.get("prompt", "")

    timestamp_safe = timestamp.replace(":", "-")
    hash_input = f"{session_id}{timestamp}{prompt}"
    hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()
    hash_short = hash_digest[:8]

    return f"{timestamp_safe}_{hash_short}"


def create_request_directory(toolbox_root: str, request_id: str) -> Path:
    """Create .toolbox/events/{request_id}/ with subdirs"""
    request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id
    request_dir.mkdir(parents=True, exist_ok=True)
    (request_dir / "work").mkdir(exist_ok=True)
    (request_dir / "session-logs").mkdir(exist_ok=True)
    (request_dir / "hook-events.jsonl").touch()
    (request_dir / "errors.log").touch()
    return request_dir


def get_current_request_id(toolbox_root: str) -> str:
    """Read current request ID from .toolbox/events/.current-request-id"""
    try:
        current_id_file = Path(toolbox_root) / ".toolbox" / "events" / ".current-request-id"
        if current_id_file.exists():
            return current_id_file.read_text().strip()
    except Exception:
        pass
    return ""


def append_to_request_events(hook_input: dict, toolbox_root: str = None):
    """Append hook event to request's hook-events.jsonl if request is active."""
    try:
        if not toolbox_root:
            toolbox_root = os.environ.get("TOOLBOX_ROOT")
        if not toolbox_root:
            return

        request_id = get_current_request_id(toolbox_root)
        if not request_id:
            return

        request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id
        hook_events_file = request_dir / "hook-events.jsonl"

        with open(hook_events_file, 'a') as f:
            f.write(json.dumps(hook_input) + '\n')
    except Exception:
        pass


def parse_context_tags(text: str) -> List[str]:
    """Extract content from <context> tags"""
    pattern = r'<context>(.*?)</context>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [match.strip() for match in matches]


def parse_work_tags(text: str) -> List[Dict[str, str]]:
    """Extract {relpath, content} from <work> tags"""
    pattern = r'<work\s+relpath="([^"]+)"(?:\s+abspath="[^"]+")?\s*>(.*?)</work>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [{"relpath": relpath, "content": content.strip()} for relpath, content in matches]


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
    """Handle UserPromptSubmit - create request, initialize context.md."""
    try:
        toolbox_root = os.environ.get("TOOLBOX_ROOT")
        if not toolbox_root:
            sys.exit(0)

        # Generate request ID
        request_id = generate_request_id(hook_input)

        # Write to .current-request-id
        events_dir = Path(toolbox_root) / ".toolbox" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        current_id_file = events_dir / ".current-request-id"
        current_id_file.write_text(request_id)

        # Create request directory
        request_dir = create_request_directory(toolbox_root, request_id)

        # Initialize context.md
        prompt = hook_input.get("prompt", "")
        context_file = request_dir / "context.md"
        context_file.write_text(f"""<userPrompt>
{prompt}
</userPrompt>

<!-- Hooks append agent context below as agents complete -->
""")

        # Extract start UUID from session log
        transcript_path = hook_input.get("transcript_path")
        if transcript_path and Path(transcript_path).exists():
            with open(transcript_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_msg = json.loads(lines[-1])
                    start_uuid = last_msg.get("uuid", "")
                    if start_uuid:
                        (request_dir / ".start-uuid").write_text(start_uuid)

        # Log to request's hook-events.jsonl
        append_to_request_events(hook_input, toolbox_root)

    except Exception as e:
        print(f"[UserPromptSubmit] ERROR: {e}", file=sys.stderr)

    sys.exit(0)


def handle_stop_event(hook_input):
    """Handle Stop - prune session log between start and end UUIDs."""
    try:
        toolbox_root = os.environ.get("TOOLBOX_ROOT")
        if not toolbox_root:
            sys.exit(0)

        request_id = get_current_request_id(toolbox_root)
        if not request_id:
            sys.exit(0)

        request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id

        # Read start UUID
        start_uuid_file = request_dir / ".start-uuid"
        if not start_uuid_file.exists():
            sys.exit(0)

        start_uuid = start_uuid_file.read_text().strip()

        # Get end UUID from session log
        transcript_path = hook_input.get("transcript_path")
        if not transcript_path or not Path(transcript_path).exists():
            sys.exit(0)

        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        messages = [json.loads(line) for line in lines]

        # Find start and end indices
        start_idx = None
        end_idx = None
        for idx, msg in enumerate(messages):
            if msg.get("uuid") == start_uuid:
                start_idx = idx
            if msg == messages[-1]:
                end_idx = idx

        # Prune and save
        if start_idx is not None and end_idx is not None:
            pruned_messages = messages[start_idx:end_idx + 1]
            session_id = hook_input.get("session_id", "unknown")
            pruned_log_path = request_dir / "session-logs" / f"{session_id}-pruned.jsonl"

            with open(pruned_log_path, 'w') as f:
                for msg in pruned_messages:
                    f.write(json.dumps(msg) + '\n')

        # Log to request's hook-events.jsonl
        append_to_request_events(hook_input, toolbox_root)

    except Exception as e:
        print(f"[Stop] ERROR: {e}", file=sys.stderr)

    sys.exit(0)


def handle_session_start(hook_input):
    """Handle SessionStart - setup TOOLBOX_ROOT and create events dir."""
    try:
        cwd = hook_input.get("cwd")
        env_file = os.environ.get("CLAUDE_ENV_FILE")

        # Write TOOLBOX_ROOT to env file
        if env_file and cwd:
            with open(env_file, 'a') as f:
                f.write(f'export TOOLBOX_ROOT="{cwd}"\n')

        # Create .toolbox/events directory
        if cwd:
            events_dir = Path(cwd) / ".toolbox" / "events"
            events_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[SessionStart] ERROR: {e}", file=sys.stderr)

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
    """Handle SubagentStop - copy transcript, extract context/work tags."""
    try:
        toolbox_root = os.environ.get("TOOLBOX_ROOT")
        if not toolbox_root:
            sys.exit(0)

        request_id = get_current_request_id(toolbox_root)
        if not request_id:
            sys.exit(0)

        request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id
        agent_id = hook_input.get("agent_id", "unknown")
        agent_type = hook_input.get("agent_type", "unknown")
        agent_transcript_path = hook_input.get("agent_transcript_path")

        if not agent_transcript_path or not Path(agent_transcript_path).exists():
            sys.exit(0)

        # Copy agent transcript
        transcript_copy = request_dir / "session-logs" / f"agent-{agent_id}.jsonl"
        shutil.copy2(agent_transcript_path, transcript_copy)

        # Extract final agent output
        with open(agent_transcript_path, 'r') as f:
            lines = f.readlines()

        final_output = ""
        for line in reversed(lines):
            msg = json.loads(line)
            if msg.get("type") == "assistant":
                # Extract text from content blocks (content is an array)
                content_blocks = msg.get("message", {}).get("content", [])
                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") == "text":
                        final_output += block.get("text", "")
                break

        # Parse and append context tags
        contexts = parse_context_tags(final_output)
        if contexts:
            context_file = request_dir / "context.md"
            with open(context_file, 'a') as f:
                f.write(f'\n<agent-{agent_id} type="{agent_type}">\n')
                for context in contexts:
                    f.write(context + '\n')
                f.write(f'</agent-{agent_id}>\n')

        # Parse and write work files
        work_items = parse_work_tags(final_output)
        for item in work_items:
            work_path = request_dir / item["relpath"]
            work_path.parent.mkdir(parents=True, exist_ok=True)
            work_path.write_text(item["content"])

        # Log to request's hook-events.jsonl
        append_to_request_events(hook_input, toolbox_root)

    except Exception as e:
        print(f"[SubagentStop] ERROR: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
