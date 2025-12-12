---
name: state-simplification
description: >
  Simplification of state management after agent-lifecycle refactoring.
  Removes State abstraction in favor of explicit JSON file management in orchestrator.
created: 2025-12-12
status: planning
---

# State Management Simplification

**Created**: 2025-12-12
**Status**: Planning

---

## Problem

The State abstraction (`lifecycle/state.py`) was designed before the major agent-lifecycle refactoring (docs/plans/2025-12-11-agent-lifecycle-refactoring.md). Now that we have LifecycleOrchestrator managing the entire hook processing flow, State's abstractions no longer fit:

1. **Lazy loading fights explicit control** - State's `__missing__` auto-reconstruction conflicts with orchestrator's explicit flow control
2. **Framework logic leaked in** - `_find_request_id()` and `_find_start_uuid()` are reconstruction logic that belongs in orchestrator
3. **Routing abstraction is thin** - Dual-file routing adds complexity without significant value
4. **_TrackedDict complexity unused** - Orchestrator writes complete dicts, not incremental nested mutations

The orchestrator is in the business of managing state. Dealing with JSON files is an implementation detail, but it's simple enough to handle directly without a separate abstraction layer.

---

## Solution Summary

Remove State abstraction entirely. Orchestrator manages two JSON files directly using simple helper methods.

**What's removed:**
- `lifecycle/state.py` - State, StateFile, _TrackedDict classes
- `tests/test_lifecycle_state.py` - State tests

**What's added to orchestrator:**
- Simple JSON load/save helpers
- State file path encapsulation
- Explicit state management in `process()` flow

**What stays the same:**
- Dual-file storage (`.global-state.json` and `.state.json`)
- Atomic writes (temp file + rename)
- Same data structures
- Same orchestration flow

---

## Design

### State File Paths

Encapsulate filenames as instance attributes (easy to parameterize later):

```python
class LifecycleOrchestrator:
    """Coordinates hook processing, manages lifecycle, executes side effects."""

    def __init__(self):
        self._global_state_file = ".global-state.json"
        self._request_state_file = ".state.json"
```

### JSON Helpers

Generic load/save with atomic writes:

```python
def _load_json(self, path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}

def _save_json(self, path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2))
    temp.rename(path)
```

### State File Accessors

Encapsulate paths and file operations:

```python
def _global_state_path(self, toolbox_root: str) -> Path:
    return Path(toolbox_root) / ".toolbox" / "events" / self._global_state_file

def _request_state_path(self, request_dir: Path) -> Path:
    return request_dir / self._request_state_file

def _load_global_state(self, toolbox_root: str) -> dict:
    return self._load_json(self._global_state_path(toolbox_root))

def _save_global_state(self, toolbox_root: str, data: dict) -> None:
    self._save_json(self._global_state_path(toolbox_root), data)

def _load_request_state(self, request_dir: Path) -> dict:
    return self._load_json(self._request_state_path(request_dir))

def _save_request_state(self, request_dir: Path, data: dict) -> None:
    self._save_json(self._request_state_path(request_dir), data)
```

---

## Method Changes

### `_get_or_create_request_id()`

**Before:**
```python
def _get_or_create_request_id(self, event_data: EventData, toolbox_root: str) -> str:
    if event_data.hook_event_name == "UserPromptSubmit":
        return generate_request_id(event_data.fields)

    session_id = event_data.fields.get("session_id")
    transcript_path = event_data.fields.get("transcript_path")

    with State(toolbox_root, session_id, transcript_path) as state:
        return state._global.get("session_requests", {}).get(session_id, "")
```

**After:**
```python
def _get_or_create_request_id(self, event_data: EventData, toolbox_root: str) -> str:
    if event_data.hook_event_name == "UserPromptSubmit":
        return generate_request_id(event_data.fields)

    session_id = event_data.fields.get("session_id")
    global_state = self._load_global_state(toolbox_root)
    return global_state.get("session_requests", {}).get(session_id, "")
```

### `_build_request_context()`

**Before:**
```python
def _build_request_context(self, event_data: EventData, request_dir: Path, state: State) -> RequestContext:
    return RequestContext(
        session_id=event_data.fields.get("session_id", ""),
        request_id=state._global.get("session_requests", {}).get(event_data.fields.get("session_id"), ""),
        request_dir=request_dir,
        transcript_path=Path(event_data.fields.get("transcript_path", "")),
        agent_types=state["agent_types"],
        start_uuid=state["start_uuid"]
    )
```

**After:**
```python
def _build_request_context(self, event_data: EventData, request_dir: Path, request_id: str) -> RequestContext:
    request_state = self._load_request_state(request_dir)
    return RequestContext(
        session_id=event_data.fields.get("session_id", ""),
        request_id=request_id,
        request_dir=request_dir,
        transcript_path=Path(event_data.fields.get("transcript_path", "")),
        agent_types=request_state.get("agent_types", {}),
        start_uuid=request_state.get("start_uuid")
    )
```

### `process()`

**Before:**
```python
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
```

**After:**
```python
# 4. Register request_id for UserPromptSubmit
session_id = event_data.fields.get("session_id")
if event_data.hook_event_name == "UserPromptSubmit":
    global_state = self._load_global_state(toolbox_root)
    if "session_requests" not in global_state:
        global_state["session_requests"] = {}
    global_state["session_requests"][session_id] = request_id
    self._save_global_state(toolbox_root, global_state)

# 5. Build context from state files
context = self._build_request_context(event_data, request_dir, request_id)

# 6. Execute framework logic specific to this event
if event_data.hook_event_name == "UserPromptSubmit":
    self._handle_user_prompt_submit(context, event_data)
elif event_data.hook_event_name == "SubagentStart":
    self._handle_subagent_start(context, event_data)
elif event_data.hook_event_name == "SubagentStop":
    self._handle_subagent_stop(context, event_data)
elif event_data.hook_event_name == "Stop":
    self._handle_stop(context, event_data)

# 7. Persist state changes
self._persist_state_changes(toolbox_root, request_dir, context)

# 8. Execute side effects
self._execute_file_operations(context)

# 9. Log hook event
self._append_hook_event(request_dir, raw_hook_input)
```

### `_persist_state_changes()`

**Before:**
```python
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
```

**After:**
```python
def _persist_state_changes(self, toolbox_root: str, request_dir: Path, context: RequestContext):
    request_state = self._load_request_state(request_dir)

    # Extract start_uuid from session log if not already set
    if context.transcript_path.exists() and not request_state.get("start_uuid"):
        with open(context.transcript_path, 'r') as f:
            lines = f.readlines()
            if lines:
                last_msg = json.loads(lines[-1])
                start_uuid = last_msg.get("uuid", "")
                if start_uuid:
                    request_state["start_uuid"] = start_uuid

    # Persist agent_types changes (SubagentStart)
    if context.agent_types:
        request_state["agent_types"] = context.agent_types

    self._save_request_state(request_dir, request_state)
```

---

## Files Changed

**Modified:**
- `ai-assisted-development/src/lifecycle/orchestrator.py` - All refactoring above

**Deleted:**
- `ai-assisted-development/src/lifecycle/state.py` - Entire file
- `ai-assisted-development/tests/test_lifecycle_state.py` - Entire file

**Unchanged:**
- Historical plan documents remain as-is

---

## Benefits

**Simplicity:**
- Fewer abstractions (no State, StateFile, _TrackedDict)
- Explicit load/save instead of hidden context manager behavior
- Clear data flow (load → modify → save)

**Maintainability:**
- Orchestrator owns state management completely
- No framework logic hidden in storage layer
- Easy to understand: just JSON files

**Flexibility:**
- File paths easily parameterizable (instance attributes)
- Can add caching later if needed
- Can change storage format without affecting public API

---

## Implementation Notes

This is a pure simplification refactor. No new functionality, no behavior changes. The orchestrator already controls the state lifecycle - we're just removing the abstraction that was fighting it.

---

## Testing

Existing orchestrator tests should continue to pass. State-specific tests are deleted since State class is removed.
