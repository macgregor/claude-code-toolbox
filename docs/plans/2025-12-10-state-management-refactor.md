# State Management Refactor

**Date**: 2025-12-10
**Status**: Planning
**Context**: Refactoring agent-lifecycle.py to use cleaner state management patterns

---

## Problem Statement

1. **Messy file proliferation**: Multiple ad-hoc state files (`.start-uuid`, `.agent-types.json`)
2. **Concurrency issues**: `.toolbox/events/.current-request-id` is global but multiple sessions can run concurrently
3. **No encapsulation**: State read/write logic scattered throughout handlers

---

## Current State Files

### Session-Scoped (Global)
- `.toolbox/events/.current-request-id` - Maps current session to active request
  - **Problem**: Only tracks ONE session, but multiple sessions can be concurrent

### Request-Scoped
- `.toolbox/events/{request_id}/.start-uuid` - Session log boundary marker
- `.toolbox/events/{request_id}/context.md` - User prompt + agent contexts
- `.toolbox/events/{request_id}/work/` - Agent-created files
- `.toolbox/events/{request_id}/session-logs/` - Agent transcripts
- `.toolbox/events/{request_id}/hook-events.jsonl` - Audit trail

### Global (Workaround)
- `.toolbox/events/.agent-types.json` - Maps agent_id → agent_type (SubagentStop missing agent_type)

---

## Concurrency Problem

**Scenario**: User has 2 terminal sessions running Claude Code in the same workspace:
- Session A (session_id: `aaa-111`) handles user prompt → creates request_id `2025-12-10T10-00-00_abc123`
- Session B (session_id: `bbb-222`) handles user prompt → creates request_id `2025-12-10T10-00-05_def456`

**Current behavior**:
- `.current-request-id` can only hold ONE value
- Whichever session writes last wins
- Hooks from session A might append to session B's request directory

---

## Design Constraints

1. **Request-scoped state**: Most state belongs to a specific request
2. **Lazy I/O**: Only read state when needed, only write when changed
3. **Concurrent sessions**: Multiple sessions must not corrupt each other's data
4. **Atomic writes**: Temp file + rename to prevent partial corruption

---

## Solution: Dual-Layer State Management

### Global State: Session-to-Request Mapping

**File**: `.toolbox/events/.global-state.json`

**Purpose**: Maps session_id → request_id to solve concurrency problem

**Structure**:
```json
{
  "session_requests": {
    "338a2bf2-9a80-4ec6-8cc6-cac916b62270": "2025-12-10T10-00-00_abc123",
    "862867f5-5738-4d23-beb7-7c2f6ba8e1ff": "2025-12-10T10-00-05_def456"
  }
}
```

---

### Request State: Per-Request State File

**File**: `.toolbox/events/{request_id}/.state.json`

**Purpose**: Consolidates `.start-uuid` and agent_types (currently in `.agent-types.json`)

**Structure**:
```json
{
  "start_uuid": "msg-uuid-1234",
  "agent_types": {
    "83c40a7b": "ai-assisted-development:document-reviewer",
    "7f8a9012": "ai-assisted-development:web-research"
  }
}
```

---

## State Reconstruction

All state can be reconstructed from source of truth (session logs, hook events). This enables graceful recovery from corruption.

### start_uuid Reconstruction

**Source**: Session transcript (reverse search for user prompt)

**Target Message**:
```json
{
  "type": "user",
  "isSidechain": false,
  "message": {
    "role": "user",
    "content": "we modified document-reviewer agent. spawn it and have it review ARCHITECTURE.md"
  },
  "uuid": "877d773f-ee67-404c-8905-22a836b8a101"
}
```

**Filter Logic**: `type == "user"` AND `isSidechain == false` AND NO `isMeta` field AND `message.content` is string (not array)

### agent_type Reconstruction

**Source**: Request's hook-events.jsonl (search for SubagentStart event)

**Target Message**:
```json
{
  "hook_event_name": "SubagentStart",
  "agent_id": "83c40a7b",
  "agent_type": "ai-assisted-development:document-reviewer"
}
```

**Lookup**: Match `agent_id`, extract `agent_type` field

### request_id Reconstruction

**Source**: Scan all request directories for matching session_id

**Strategy**: We cannot derive request_id without already having it (chicken-and-egg). Instead:
1. Iterate all directories in `.toolbox/events/`
2. For each directory with `hook-events.jsonl`, read first line (UserPromptSubmit)
3. Match `session_id` field to find the request directory for this session

**Target Message** (from hook-events.jsonl first line):
```json
{
  "session_id": "338a2bf2-9a80-4ec6-8cc6-cac916b62270",
  "transcript_path": "/path/to/.claude/projects/{workspace}/{session_id}.jsonl",
  "hook_event_name": "UserPromptSubmit"
}
```

**Note**: O(N) scan acceptable for <100 request directories. Most recent request checked first (reverse sorted).

## Python Class Interface

### Usage Pattern

**Context Manager (Recommended)**:
```python
try:
    with State(toolbox_root, session_id, transcript_path) as state:
        state.set_request_id(request_id)
        state["start_uuid"] = uuid
        # Automatically saves on __exit__
except ValueError as e:
    print(f"[handler] ERROR: {e}", file=sys.stderr)
    # Hook continues with exit code 0
```

**Manual Save (Alternative)**:
```python
try:
    state = State(toolbox_root, session_id, transcript_path)
    state["agent_types"][agent_id] = agent_type
    state._global.save()
    state._request.save()
except ValueError as e:
    print(f"[handler] ERROR: {e}", file=sys.stderr)
```

**Error Handling**: All reconstruction methods raise `ValueError` on failure. Hook handlers should catch and log errors, then exit 0 (don't fail the hook).

### StateFile Class

```python
class StateFile(dict):
    """File-backed dict with auto-population on cache miss."""

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
            if value and value != "unknown":
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
```

### State Class

```python
class State:
    """Unified state management hiding dual-file implementation.

    Args:
        toolbox_root: Project root directory (from get_toolbox_root(hook_input))
        session_id: Session ID (from hook_input['session_id'])
        transcript_path: Path to session log (from hook_input['transcript_path'])
    """

    def __init__(self, toolbox_root: Path, session_id: str, transcript_path: str = None):
        self.session_id = session_id
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self.events_dir = toolbox_root / ".toolbox" / "events"

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
```

## Implementation Plan

### Step 1: Create State Classes

Implement `StateFile` and `State` classes in `agent-lifecycle.py` with:
- `StateFile` extends `dict` with `__missing__` for auto-population on cache miss
- Atomic writes (temp file + rename)
- Reconstruction functions for all stateful values

### Step 2: Update Hook Handlers

**All handlers**:
- Extract `session_id`, `transcript_path` from hook input
- Use existing `toolbox_root = get_toolbox_root(hook_input)` (already implemented)
- Wrap State operations in try/except to catch ValueError

---

#### handle_user_prompt_submit

**Before**:
```python
def handle_user_prompt_submit(hook_input):
    try:
        toolbox_root = get_toolbox_root(hook_input)
        if not toolbox_root:
            sys.exit(0)

        request_id = generate_request_id(hook_input)

        # Write to .current-request-id
        events_dir = Path(toolbox_root) / ".toolbox" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        current_id_file = events_dir / ".current-request-id"
        current_id_file.write_text(request_id)

        request_dir = create_request_directory(toolbox_root, request_id)

        # ... context.md initialization ...

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

        append_to_request_events(hook_input, toolbox_root)
    except Exception as e:
        print(f"[UserPromptSubmit] ERROR: {e}", file=sys.stderr)
    sys.exit(0)
```

**After**:
```python
def handle_user_prompt_submit(hook_input):
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

        # ... context.md initialization (unchanged) ...

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

        append_to_request_events(hook_input, toolbox_root)
    except ValueError as e:
        print(f"[UserPromptSubmit] State ERROR: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[UserPromptSubmit] ERROR: {e}", file=sys.stderr)
    sys.exit(0)
```

---

#### handle_subagent_start

**Before**:
```python
def handle_subagent_start(hook_input):
    try:
        toolbox_root = get_toolbox_root(hook_input)
        if toolbox_root:
            agent_id = hook_input.get("agent_id")
            agent_type = hook_input.get("agent_type", "unknown")

            if agent_id and agent_type != "unknown":
                agent_types_file = Path(toolbox_root) / ".toolbox" / "events" / ".agent-types.json"

                # Load existing mappings
                agent_types = {}
                if agent_types_file.exists():
                    try:
                        agent_types = json.loads(agent_types_file.read_text())
                    except Exception:
                        pass

                # Store this agent's type
                agent_types[agent_id] = agent_type

                # Write back
                agent_types_file.parent.mkdir(parents=True, exist_ok=True)
                agent_types_file.write_text(json.dumps(agent_types))

        append_to_request_events(hook_input)
    except Exception:
        pass
    sys.exit(0)
```

**After**:
```python
def handle_subagent_start(hook_input):
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
```

---

#### handle_subagent_stop

**Before**:
```python
def handle_subagent_stop(hook_input):
    try:
        toolbox_root = get_toolbox_root(hook_input)
        if not toolbox_root:
            sys.exit(0)

        request_id = get_current_request_id(toolbox_root)
        if not request_id:
            sys.exit(0)

        request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id
        agent_id = hook_input.get("agent_id", "unknown")

        # SubagentStop doesn't provide agent_type, so retrieve from storage
        agent_type = hook_input.get("agent_type", "unknown")
        if agent_type == "unknown":
            agent_types_file = Path(toolbox_root) / ".toolbox" / "events" / ".agent-types.json"
            if agent_types_file.exists():
                try:
                    agent_types = json.loads(agent_types_file.read_text())
                    agent_type = agent_types.get(agent_id, "unknown")
                except Exception:
                    pass

        # ... rest of handler ...
    except Exception as e:
        print(f"[SubagentStop] ERROR: {e}", file=sys.stderr)
    sys.exit(0)
```

**After**:
```python
def handle_subagent_stop(hook_input):
    try:
        toolbox_root = get_toolbox_root(hook_input)
        if not toolbox_root:
            sys.exit(0)

        session_id = hook_input.get("session_id")
        transcript_path = hook_input.get("transcript_path")
        agent_id = hook_input.get("agent_id", "unknown")

        with State(toolbox_root, session_id, transcript_path) as state:
            # Get request_id from state
            request_id = state._global.get("session_requests", {}).get(session_id)
            if not request_id:
                print(f"[SubagentStop] No request_id for session {session_id}", file=sys.stderr)
                sys.exit(0)

            request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id

            # Get agent_type from state (auto-reconstructed if missing)
            agent_type = state["agent_types"].get(agent_id, "unknown")

        # ... rest of handler unchanged ...
    except ValueError as e:
        print(f"[SubagentStop] State ERROR: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[SubagentStop] ERROR: {e}", file=sys.stderr)
    sys.exit(0)
```

---

#### handle_stop_event

**Before**:
```python
def handle_stop_event(hook_input):
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

        # ... rest of pruning logic ...
    except Exception as e:
        print(f"[Stop] ERROR: {e}", file=sys.stderr)
    sys.exit(0)
```

**After**:
```python
def handle_stop_event(hook_input):
    try:
        toolbox_root = get_toolbox_root(hook_input)
        if not toolbox_root:
            sys.exit(0)

        session_id = hook_input.get("session_id")
        transcript_path = hook_input.get("transcript_path")

        with State(toolbox_root, session_id, transcript_path) as state:
            # Get request_id and start_uuid from state
            request_id = state._global.get("session_requests", {}).get(session_id)
            if not request_id:
                print(f"[Stop] No request_id for session {session_id}", file=sys.stderr)
                sys.exit(0)

            request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id

            # Get start_uuid (auto-reconstructed if missing)
            start_uuid = state["start_uuid"]
            if not start_uuid:
                print(f"[Stop] No start_uuid for request {request_id}", file=sys.stderr)
                sys.exit(0)

        # ... rest of pruning logic unchanged ...
    except ValueError as e:
        print(f"[Stop] State ERROR: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[Stop] ERROR: {e}", file=sys.stderr)
    sys.exit(0)
```

### Step 3: Update Statusline

Modify `statusline.sh` to read `.global-state.json` instead of `.current-request-id`

### Step 4: Testing

**Manual validation**:
- Spawn agent in two terminal sessions
- Verify separate request directories created
- Verify no data corruption in `.global-state.json`

### Files Affected

- `ai-assisted-development/scripts/agent-lifecycle.py` - Core implementation
- `ai-assisted-development/scripts/debug/statusline.sh` - State lookup

## Reference

See [../claude-code-appendix-session-log-messages.md](../claude-code-appendix-session-log-messages.md) for session log and hook event message format details.
