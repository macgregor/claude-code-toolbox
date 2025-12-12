"""Orchestrator for lifecycle event processing."""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from .errors import NonBlockingError
from .models import RequestContext, EventData
from .processing import get_toolbox_root, generate_request_id, create_request_directory, parse_context_tags, parse_work_tags
from .state import State
from .handlers import EventHandler


class LifecycleOrchestrator:
    """Coordinates hook processing, manages lifecycle, executes side effects."""

    def __init__(self):
        self._global_state_file = ".global-state.json"
        self._request_state_file = ".state.json"

    def _load_json(self, path: Path) -> dict:
        """Load JSON from file, return empty dict if not exists."""
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def _save_json(self, path: Path, data: dict) -> None:
        """Save JSON to file with atomic write (temp + rename)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, indent=2))
        temp.rename(path)

    def _global_state_path(self, toolbox_root: str) -> Path:
        """Path to global state file."""
        return Path(toolbox_root) / ".toolbox" / "events" / self._global_state_file

    def _request_state_path(self, request_dir: Path) -> Path:
        """Path to request state file."""
        return request_dir / self._request_state_file

    def _load_global_state(self, toolbox_root: str) -> dict:
        """Load global state (session_requests mapping)."""
        return self._load_json(self._global_state_path(toolbox_root))

    def _save_global_state(self, toolbox_root: str, data: dict) -> None:
        """Save global state."""
        self._save_json(self._global_state_path(toolbox_root), data)

    def _load_request_state(self, request_dir: Path) -> dict:
        """Load request state (agent_types, start_uuid)."""
        return self._load_json(self._request_state_path(request_dir))

    def _save_request_state(self, request_dir: Path, data: dict) -> None:
        """Save request state."""
        self._save_json(self._request_state_path(request_dir), data)

    def process(self, raw_hook_input: Dict[str, Any]):
        """Process hook event.

        Args:
            raw_hook_input: Raw hook input JSON from Claude Code
        """
        # 1. Parse and validate
        event_data = self._build_event_data(raw_hook_input)

        # 2. Determine request context
        toolbox_root = get_toolbox_root(raw_hook_input)
        if not toolbox_root:
            return

        # Handle SessionStart specially - just create events dir
        if event_data.hook_event_name == "SessionStart":
            events_dir = Path(toolbox_root) / ".toolbox" / "events"
            events_dir.mkdir(parents=True, exist_ok=True)
            return

        # For other events, need request_id
        request_id = self._get_or_create_request_id(event_data, toolbox_root)
        if not request_id:
            return
        request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id

        # 3. Create request directory if needed
        if not request_dir.exists():
            self._create_request_directory(request_dir, toolbox_root, request_id)

        # 4. Initialize context with state
        session_id = event_data.fields.get("session_id")
        transcript_path = event_data.fields.get("transcript_path")

        with State(toolbox_root, session_id, transcript_path) as state:
            # For UserPromptSubmit, set request_id first before building context
            if event_data.hook_event_name == "UserPromptSubmit":
                state.set_request_id(request_id)

            context = self._build_request_context(event_data, request_dir, state)

            # 5. Execute framework logic specific to this event
            if event_data.hook_event_name == "UserPromptSubmit":
                self._handle_user_prompt_submit(context, event_data)
            elif event_data.hook_event_name == "SubagentStart":
                self._handle_subagent_start(context, event_data)
            elif event_data.hook_event_name == "SubagentStop":
                self._handle_subagent_stop(context, event_data)
            elif event_data.hook_event_name == "Stop":
                self._handle_stop(context, event_data)

            # 6. Persist state changes
            self._persist_state_changes(state, context)

            # 7. Execute side effects
            self._execute_file_operations(context)

            # 8. Log hook event
            self._append_hook_event(request_dir, raw_hook_input)

    def _build_event_data(self, raw_hook_input: Dict[str, Any]) -> EventData:
        """Extract/validate fields, create EventData."""
        return EventData(
            hook_event_name=raw_hook_input.get("hook_event_name", ""),
            raw_hook_input=json.dumps(raw_hook_input),
            fields=raw_hook_input
        )

    def _get_or_create_request_id(self, event_data: EventData, toolbox_root: str) -> str:
        """UserPromptSubmit creates, others lookup from state."""
        if event_data.hook_event_name == "UserPromptSubmit":
            return generate_request_id(event_data.fields)

        # Lookup from global state
        session_id = event_data.fields.get("session_id")
        global_state = self._load_global_state(toolbox_root)
        return global_state.get("session_requests", {}).get(session_id, "")

    def _create_request_directory(self, request_dir: Path, toolbox_root: str, request_id: str):
        """Create directory structure on first event."""
        create_request_directory(toolbox_root, request_id)

    def _get_handler(self, event_name: str) -> Optional[EventHandler]:
        """Route event to handler (returns None - extension point)."""
        return None

    def _build_request_context(self, event_data: EventData, request_dir: Path, request_id: str) -> RequestContext:
        """Load state data into RequestContext."""
        request_state = self._load_request_state(request_dir)
        return RequestContext(
            session_id=event_data.fields.get("session_id", ""),
            request_id=request_id,
            request_dir=request_dir,
            transcript_path=Path(event_data.fields.get("transcript_path", "")),
            agent_types=request_state.get("agent_types", {}),
            start_uuid=request_state.get("start_uuid")
        )

    def _handle_user_prompt_submit(self, context: RequestContext, event_data: EventData):
        """Write user prompt to context.md."""
        prompt = event_data.fields.get("prompt", "")
        context_file = context.request_dir / "context.md"
        context_file.write_text(f"""<userPrompt>
{prompt}
</userPrompt>

<!-- Hooks append agent context below as agents complete -->
""")

    def _handle_subagent_start(self, context: RequestContext, event_data: EventData):
        """Update context.agent_types mapping (state change)."""
        agent_id = event_data.fields.get("agent_id")
        agent_type = event_data.fields.get("agent_type", "unknown")

        if agent_id and agent_type != "unknown":
            # Modify agent_types dict (will be persisted)
            context.agent_types[agent_id] = agent_type

    def _handle_subagent_stop(self, context: RequestContext, event_data: EventData):
        """Extract agent context/work tags, append to context.md, copy transcript."""
        agent_id = event_data.fields.get("agent_id", "unknown")
        agent_transcript_path = event_data.fields.get("agent_transcript_path")

        if not agent_transcript_path or not Path(agent_transcript_path).exists():
            return

        # Copy agent transcript
        transcript_copy = context.request_dir / "session-logs" / f"agent-{agent_id}.jsonl"
        shutil.copy2(agent_transcript_path, transcript_copy)

        # Extract final agent output
        with open(agent_transcript_path, 'r') as f:
            lines = f.readlines()

        final_output = ""
        for line in reversed(lines):
            msg = json.loads(line)
            if msg.get("type") == "assistant":
                content_blocks = msg.get("message", {}).get("content", [])
                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") == "text":
                        final_output += block.get("text", "")
                break

        # Parse and append context tags
        contexts = parse_context_tags(final_output)
        if contexts:
            agent_type = context.agent_types.get(agent_id, "unknown")
            context_file = context.request_dir / "context.md"
            with open(context_file, 'a') as f:
                f.write(f'\n<agent-{agent_id} type="{agent_type}">\n')
                for ctx in contexts:
                    f.write(ctx + '\n')
                f.write(f'</agent-{agent_id}>\n')

        # Parse and write work files
        work_items = parse_work_tags(final_output)
        work_dir = context.request_dir / "work"

        for item in work_items:
            filename = item["filename"]

            # Validate: no path separators or traversal
            if "/" in filename or "\\" in filename or ".." in filename:
                raise NonBlockingError(f"Invalid filename '{filename}' - must be simple filename only")

            work_path = work_dir / filename

            # Validate: no duplicates
            if work_path.exists():
                raise NonBlockingError(f"File '{filename}' already exists in work directory")

            work_path.write_text(item["content"])

    def _handle_stop(self, context: RequestContext, event_data: EventData):
        """Extract request-specific portion from full session log."""
        transcript_path = event_data.fields.get("transcript_path")

        if not transcript_path or not Path(transcript_path).exists():
            return

        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        messages = [json.loads(line) for line in lines]

        # Find start and end indices
        start_idx = None
        end_idx = None
        for idx, msg in enumerate(messages):
            if msg.get("uuid") == context.start_uuid:
                start_idx = idx
            if msg == messages[-1]:
                end_idx = idx

        # Prune and save
        if start_idx is not None and end_idx is not None:
            pruned_messages = messages[start_idx:end_idx + 1]
            pruned_log_path = context.request_dir / "session-logs" / f"{context.session_id}-pruned.jsonl"

            with open(pruned_log_path, 'w') as f:
                for msg in pruned_messages:
                    f.write(json.dumps(msg) + '\n')

    def _persist_state_changes(self, state: State, context: RequestContext):
        """Write State changes to .state.json and .global-state.json files."""
        # Extract start_uuid from session log
        if context.transcript_path.exists():
            with open(context.transcript_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_msg = json.loads(lines[-1])
                    start_uuid = last_msg.get("uuid", "")
                    if start_uuid and not state["start_uuid"]:
                        state["start_uuid"] = start_uuid

        # Persist agent_types changes (SubagentStart)
        if context.agent_types:
            state["agent_types"] = context.agent_types

    def _execute_file_operations(self, context: RequestContext):
        """Execute FileOperations queued by handlers (currently none - extension point)."""
        # Future: Execute context.file_operations
        # For now, no handlers registered, so nothing to execute
        pass

    def _append_hook_event(self, request_dir: Path, raw_hook_input: Dict[str, Any]):
        """Append hook event to hook-events.jsonl."""
        hook_events_file = request_dir / "hook-events.jsonl"
        with open(hook_events_file, 'a') as f:
            f.write(json.dumps(raw_hook_input) + '\n')
