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
from typing import Dict, Any, List, Callable


class StateFile(dict):
    """File-backed dict with auto-population on cache miss.

    WARNING: Nested dict modifications don't trigger dirty flag.
    Example problematic pattern:
        state["agent_types"][agent_id] = type  # Won't mark dirty!

    Workaround: Re-assign the entire dict:
        agent_types = state["agent_types"]
        agent_types[agent_id] = type
        state["agent_types"] = agent_types  # Triggers dirty flag
    """

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self._dirty = False
        self._loaders = {}
        if path.exists():
            self.update(json.loads(path.read_text()))

    def register_loader(self, key: str, loader: Callable[[], Any]):
        """Register a function to populate key on cache miss."""
        self._loaders[key] = loader

    def __missing__(self, key: str):
        """Auto-populate from registered loader on cache miss."""
        if key in self._loaders:
            value = self._loaders[key]()
            if value is not None and value != "unknown":
                self[key] = value
                return value
        return None

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._dirty = True

    def save(self):
        """Atomic write if dirty."""
        if self._dirty:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(dict(self), indent=2))
            temp.rename(self.path)
            self._dirty = False


class State:
    """Unified state management hiding dual-file implementation.

    Args:
        toolbox_root: Project root directory (from get_toolbox_root(hook_input))
        session_id: Session ID (from hook_input['session_id'])
        transcript_path: Path to session log (from hook_input['transcript_path'])

    WARNING: agent_types is a nested dict that requires special handling.
    Nested modifications DON'T trigger dirty flag. To modify agent_types:
        agent_types = state["agent_types"]
        agent_types[agent_id] = type
        state["agent_types"] = agent_types  # Re-assign to trigger save
    """

    def __init__(self, toolbox_root: str, session_id: str, transcript_path: str = None):
        self.session_id = session_id
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self.events_dir = Path(toolbox_root) / ".toolbox" / "events"

        self._global = StateFile(self.events_dir / ".global-state.json")
        self._global.register_loader(
            "session_requests",
            lambda: {self.session_id: self._find_request_id()}
        )

        self._request = None

    def _ensure_request(self):
        """Lazy load request state file."""
        if self._request is None:
            rid = self._global.get("session_requests", {}).get(self.session_id)
            if not rid:
                rid = self._find_request_id()
                if not rid:
                    raise ValueError(f"No request_id for session {self.session_id}")
                session_requests = self._global.get("session_requests", {})
                session_requests[self.session_id] = rid
                self._global["session_requests"] = session_requests

            self._request = StateFile(self.events_dir / rid / ".state.json")
            self._request.register_loader("start_uuid", self._find_start_uuid)
            self._request.register_loader("agent_types", lambda: {})

    def __getitem__(self, key):
        """Dict-like access routing to correct file."""
        if key == "session_requests":
            return self._global.get(key, {})

        self._ensure_request()

        if key == "agent_types":
            return self._request.setdefault(key, {})

        return self._request.get(key, "")

    def set_request_id(self, request_id: str):
        """Set request_id for current session."""
        session_requests = self._global.get("session_requests", {})
        session_requests[self.session_id] = request_id
        self._global["session_requests"] = session_requests  # Trigger dirty flag

    def __setitem__(self, key, value):
        """Dict-like write routing to correct file."""
        self._ensure_request()
        self._request[key] = value

    def _find_request_id(self) -> str:
        """Reconstruct request_id by scanning all request directories.

        Raises:
            ValueError: If no request_id found for session
        """
        if not self.events_dir.exists():
            raise ValueError(f"Events directory does not exist: {self.events_dir}")

        for d in sorted(self.events_dir.iterdir(), key=lambda p: p.name, reverse=True):
            if not d.is_dir():
                continue
            hook_file = d / "hook-events.jsonl"
            if not hook_file.exists():
                continue
            # Read first line (UserPromptSubmit event)
            first_line = next((l for l in hook_file.read_text().split('\n') if l), None)
            if first_line and json.loads(first_line).get("session_id") == self.session_id:
                return d.name

        raise ValueError(f"No request_id found for session {self.session_id}")

    def _find_start_uuid(self) -> str:
        """Reconstruct start_uuid from session log.

        Raises:
            ValueError: If session log not found or no valid user prompt found
        """
        # Use transcript_path from hook input if available
        if self.transcript_path and self.transcript_path.exists():
            log = self.transcript_path
        else:
            # Fallback: use request-scoped session log copy (from handle_stop_event)
            request_id = self._global.get("session_requests", {}).get(self.session_id)
            if not request_id:
                raise ValueError(f"Cannot find start_uuid: no request_id for session {self.session_id}")
            log = self.events_dir / request_id / "session-logs" / f"{self.session_id}-pruned.jsonl"

        if not log.exists():
            raise ValueError(f"Session log not found: {log}")

        for line in reversed(log.read_text().split('\n')):
            if line and (msg := json.loads(line)).get("type") == "user" and not msg.get("isSidechain") and "isMeta" not in msg and isinstance(msg.get("message", {}).get("content"), str):
                uuid = msg.get("uuid")
                if not uuid:
                    raise ValueError("User prompt message missing uuid field")
                return uuid

        raise ValueError(f"No valid user prompt found in session log: {log}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._global.save()
        if self._request:
            self._request.save()


def get_toolbox_root(hook_input: Dict[str, Any] = None) -> str:
    """Get TOOLBOX_ROOT from environment or env file, with fallback to cwd."""
    # Try environment variable first
    toolbox_root = os.environ.get("TOOLBOX_ROOT")
    if toolbox_root:
        return toolbox_root

    # Try reading from CLAUDE_ENV_FILE
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if env_file and Path(env_file).exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('export TOOLBOX_ROOT='):
                        # Parse: export TOOLBOX_ROOT="/workspace"
                        value = line.split('=', 1)[1].strip()
                        # Remove quotes
                        toolbox_root = value.strip('"\'')
                        if toolbox_root:
                            return toolbox_root
        except Exception:
            pass

    # Fallback to cwd from hook_input
    if hook_input:
        cwd = hook_input.get("cwd")
        if cwd:
            return cwd

    return ""


def generate_request_id(hook_input: Dict[str, Any]) -> str:
    """Generate deterministic request ID: {timestamp}_{hash}"""
    from datetime import datetime

    session_id = hook_input.get("session_id", "")
    timestamp = hook_input.get("timestamp", "")
    prompt = hook_input.get("prompt", "")

    # If no timestamp provided, generate one
    if not timestamp:
        timestamp = datetime.now().isoformat()

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
            toolbox_root = get_toolbox_root(hook_input)
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
    """Extract {filename, content} from <work> tags"""
    pattern = r'<work\s+filename="([^"]+)"\s*>(.*?)</work>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [{"filename": filename, "content": content.strip()} for filename, content in matches]


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
    append_to_request_events(hook_input)
    sys.exit(0)


def handle_post_tool_use(hook_input):
    """Handle PostToolUse event."""
    append_to_request_events(hook_input)
    sys.exit(0)


def handle_user_prompt_submit(hook_input):
    """Handle UserPromptSubmit - create request, initialize context.md."""
    try:
        toolbox_root = get_toolbox_root(hook_input)
        if not toolbox_root:
            sys.exit(0)

        session_id = hook_input.get("session_id")
        transcript_path = hook_input.get("transcript_path")

        # Generate request ID (still needed for directory creation)
        request_id = generate_request_id(hook_input)

        # Create request directory structure
        request_dir = create_request_directory(toolbox_root, request_id)

        # Initialize context.md
        prompt = hook_input.get("prompt", "")
        context_file = request_dir / "context.md"
        context_file.write_text(f"""<userPrompt>
{prompt}
</userPrompt>

<!-- Hooks append agent context below as agents complete -->
""")

        # Initialize state and store request_id + start_uuid
        with State(toolbox_root, session_id, transcript_path) as state:
            state.set_request_id(request_id)

            # Extract start UUID from session log
            if transcript_path and Path(transcript_path).exists():
                with open(transcript_path, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_msg = json.loads(lines[-1])
                        start_uuid = last_msg.get("uuid", "")
                        if start_uuid:
                            state["start_uuid"] = start_uuid

        # Log to request's hook-events.jsonl
        append_to_request_events(hook_input, toolbox_root)

    except ValueError as e:
        print(f"[UserPromptSubmit] State ERROR: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[UserPromptSubmit] ERROR: {e}", file=sys.stderr)

    sys.exit(0)


def handle_stop_event(hook_input):
    """Handle Stop - prune session log between start and end UUIDs."""
    try:
        toolbox_root = get_toolbox_root(hook_input)
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
    append_to_request_events(hook_input)
    sys.exit(0)


def handle_notification(hook_input):
    """Handle Notification event."""
    append_to_request_events(hook_input)
    sys.exit(0)


def handle_subagent_start(hook_input):
    """Handle SubagentStart - store agent_type for later retrieval."""
    try:
        toolbox_root = get_toolbox_root(hook_input)
        if not toolbox_root:
            sys.exit(0)

        session_id = hook_input.get("session_id")
        transcript_path = hook_input.get("transcript_path")
        agent_id = hook_input.get("agent_id")
        agent_type = hook_input.get("agent_type", "unknown")

        if agent_id and agent_type != "unknown":
            with State(toolbox_root, session_id, transcript_path) as state:
                state["agent_types"][agent_id] = agent_type

        append_to_request_events(hook_input)
    except ValueError as e:
        print(f"[SubagentStart] State ERROR: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[SubagentStart] ERROR: {e}", file=sys.stderr)

    sys.exit(0)


def handle_post_tool_use_failure(hook_input):
    """Handle PostToolUseFailure event."""
    append_to_request_events(hook_input)
    sys.exit(0)


def handle_permission_request(hook_input):
    """Handle PermissionRequest event."""
    append_to_request_events(hook_input)
    sys.exit(0)


def handle_session_end(hook_input):
    """Handle SessionEnd event."""
    append_to_request_events(hook_input)
    sys.exit(0)


def handle_subagent_stop(hook_input):
    """Handle SubagentStop - copy transcript, extract context/work tags."""
    try:
        toolbox_root = get_toolbox_root(hook_input)
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
        work_dir = request_dir / "work"

        for item in work_items:
            filename = item["filename"]

            # Validate: no path separators or traversal
            if "/" in filename or "\\" in filename or ".." in filename:
                print(f"[SubagentStop] ERROR: Invalid filename '{filename}' - must be simple filename only", file=sys.stderr)
                sys.exit(1)

            work_path = work_dir / filename

            # Validate: no duplicates
            if work_path.exists():
                print(f"[SubagentStop] ERROR: File '{filename}' already exists in work directory", file=sys.stderr)
                sys.exit(1)

            work_path.write_text(item["content"])

        # Log to request's hook-events.jsonl
        append_to_request_events(hook_input, toolbox_root)

    except Exception as e:
        print(f"[SubagentStop] ERROR: {e}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
