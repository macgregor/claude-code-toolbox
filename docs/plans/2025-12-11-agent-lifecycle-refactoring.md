---
name: agent-lifecycle-refactoring
description: >
  Refactoring plan for agent-lifecycle.py to extract core patterns and improve
  maintainability. Establishes clean separation between hook interface, orchestration,
  state management, and event handlers.
created: 2025-12-11
status: implemented
---

# Agent Lifecycle Refactoring Design

**Created**: 2025-12-11
**Status**: Implemented

---

## Problem

The `agent-lifecycle.py` file (627 lines) is becoming difficult to manage. Code mixes concerns:
- Hook interface protocol (stdin/stdout/exit codes)
- Event routing and orchestration
- State management
- Domain logic (parsing tags, writing files)
- Request lifecycle management

Need to establish cleaner patterns to support future extensions (e.g., agent-specific routing).

---

## Solution Summary

Extract 627-line `agent-lifecycle.py` into focused modules:
- Hook interface layer (maps stdin/exit codes)
- Orchestrator (coordinates event processing)
- State management (dual-file storage)
- Processing utilities (parse tags, transform data)
- Handler extension point (empty - for future business logic)

All existing logic moves to orchestrator framework methods. No business logic handlers exist yet.

---

## Design Principles

1. **YAGNI** - Don't over-engineer or future-proof excessively
2. **Clear separation** - Hook protocol vs orchestrator framework logic vs processing utilities vs extension points
3. **Event-specific framework methods** - Orchestrator has specific methods for specific events, not generic mega-functions
4. **Simple first** - Start with single files, split only when needed
5. **Best-effort execution** - Lifecycle tracking is observational and should never block user workflow
6. **Extension points** - Handler infrastructure exists for future business logic, but currently unused

---

## Core Patterns

### 1. Event Handler Pattern (Extension Point)

Extension point for future business logic. Currently unused.

**Interface**:
```python
class EventHandler(ABC):
    @abstractmethod
    def handle(self, context: RequestContext, event: EventData) -> RequestContext:
        """Process event with business logic."""
        pass
```

**When implemented**:
- Pure functions (no side effects)
- Receive normalized inputs
- Return modified context with declared operations
- Raise `BlockingError` (exit 2) or `NonBlockingError` (exit 1)

**Current state**: ABC defined, no implementations, `_get_handler()` returns None.

### 2. State Management

Existing pattern moves to `lifecycle/state.py`:
- `State` - unified interface to dual-file storage
- `StateFile` - file-backed dict with dirty tracking
- Context manager handles lifecycle

Orchestrator manages State lifecycle and persistence. `RequestContext` wraps state data for handler access.

### 3. Data Processing

Centralized in `lifecycle/processing.py`:
- Transform hook input → `EventData` (normalized, validated)
- Parse agent outputs (context/work tags from transcripts)
- Extract/validate fields from hook_input dict
- Generate request IDs
- Extract request-scoped session log snapshots

Orchestrator calls processing functions to transform data. Example: `_handle_subagent_stop()` calls `parse_context_tags()` and `parse_work_tags()`.

**Session log snapshots**: Extracts request-specific portion from full session log (start_uuid to stop event). Writes new file to `session-logs/`. Original log untouched. Files accumulate.

**Known issue**: Request boundary detection in interactive sessions may create multiple request directories instead of one. Deferred bug - handles basic case well, needs better understanding of session log structure for edge cases. Not blocking.

---

## Architecture Layers

### Layer 1: Hook Interface

**File**: `agent-lifecycle.py`

**Responsibility**: Bridge between Claude Code hooks and framework

**Flow**:
```python
def main():
    try:
        hook_input = json.load(sys.stdin)
        orchestrator = LifecycleOrchestrator()
        orchestrator.process(hook_input)
        sys.exit(0)
    except BlockingError as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except NonBlockingError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
```

Minimal layer - translates Python exceptions to hook exit codes. No business logic.

### Layer 2: Orchestrator

**File**: `lifecycle/orchestrator.py`

Coordinates hook processing, manages lifecycle, executes side effects.

**Framework logic** (built-in guarantees):
- Request directories
- User prompt capture
- Agent type tracking
- Agent output extraction
- Session log snapshots
- Hook event logging

**Business logic** (extension point): None registered. Handlers provide extension point for future domain-specific logic.

**Flow**:
```python
class LifecycleOrchestrator:
    def process(self, raw_hook_input: Dict[str, Any]):
        # 1. Parse and validate
        event_data = self._build_event_data(raw_hook_input)

        # 2. Determine request context
        toolbox_root = get_toolbox_root(raw_hook_input)
        if not toolbox_root:
            return

        request_id = self._get_or_create_request_id(event_data, toolbox_root)
        request_dir = Path(toolbox_root) / ".toolbox/events" / request_id

        # 3. Create request directory if needed
        if not request_dir.exists():
            self._create_request_directory(request_dir)

        # 4. Initialize context with state
        with State(toolbox_root, event_data.fields["session_id"],
                   event_data.fields.get("transcript_path")) as state:

            context = self._build_request_context(event_data, request_dir, state)

            # 5. Execute framework logic specific to this event
            #    IMPORTANT: Framework methods write files to disk IMMEDIATELY
            #    This ensures files exist before handlers run
            if event_data.hook_event_name == "UserPromptSubmit":
                self._handle_user_prompt_submit(context, event_data)
            elif event_data.hook_event_name == "SubagentStart":
                self._handle_subagent_start(context, event_data)
            elif event_data.hook_event_name == "SubagentStop":
                self._handle_subagent_stop(context, event_data)
            elif event_data.hook_event_name == "Stop":
                self._handle_stop(context, event_data)
            # SessionStart has no framework operations

            # 6. Optional business logic handler (currently none registered)
            #    Handlers can read framework files (already written to disk)
            #    Handlers return modified context with queued FileOperations
            handler = self._get_handler(event_data.hook_event_name)
            if handler:
                context = handler.handle(context, event_data)

            # 7. Execute side effects (best-effort - failures raise NonBlockingError)
            #    State changes persisted first, then handler file operations executed
            self._persist_state_changes(state, context)
            self._execute_file_operations(context)  # Executes handler-queued operations
            self._append_hook_event(request_dir, raw_hook_input)
```

**Key Methods**:

*Framework Logic* (specific to each event):
- `_build_event_data()` - Extract/validate fields, create EventData
- `_get_or_create_request_id()` - UserPromptSubmit creates, others lookup from state
- `_create_request_directory()` - Create directory structure on first event
- `_handle_user_prompt_submit()` - Write user prompt to context.md (direct file write - guaranteed state)
- `_handle_subagent_start()` - Update context.agent_types mapping (state change)
- `_handle_subagent_stop()` - Extract agent context/work tags, append to context.md, copy transcript to session_logs/ (direct file writes)
- `_handle_stop()` - Extract request-specific portion from full session log and write to session_logs/{session_id}-snapshot.jsonl (direct file write)
- `_persist_state_changes()` - Write State changes to .state.json and .global-state.json files
- `_execute_file_operations()` - Execute FileOperations queued by handlers (currently none - future extension point)
- `_append_hook_event()` - Append hook event to hook_events.jsonl (direct file write)

**File operations**:
- Framework files: Written directly (context.md, session_logs/, hook_events.jsonl, .state.json)
- Handler files: Declared via FileOperation, executed by `_execute_file_operations()` (unused)
- Framework writes files before handlers run, after state persists

**Extension points**:
- `_build_request_context()` - Load state into RequestContext
- `_get_handler()` - Route to handler (returns None)

### Layer 3: Domain Objects

**File**: `lifecycle/models.py`

**RequestContext** - Request-scoped framework state (mutable):
```python
@dataclass
class RequestContext:
    """Request-scoped state managed by lifecycle framework.

    Handlers receive this, modify it, and return it.
    Orchestrator persists changes to State files.
    """
    session_id: str
    request_id: str
    request_dir: Path  # Handlers can read files from here
    transcript_path: Path

    # Mutable state data
    agent_types: Dict[str, str]  # agent_id -> agent_type
    start_uuid: str | None

    # File operations to execute
    file_operations: List[FileOperation] = field(default_factory=list)
```

**EventData** - Normalized hook input (immutable):
```python
@dataclass(frozen=True)
class EventData:
    """Normalized hook input from Claude Code.

    Transforms anthropic's hook input JSON into validated data.
    Common fields: session_id, transcript_path, cwd, hook_event_name.
    Event-specific fields available via .fields dict.
    """
    hook_event_name: str
    raw_hook_input: str  # Original JSON for debugging
    fields: Dict[str, Any]  # All normalized/validated fields
```

**FileOperation** - Declarative file operation:
```python
@dataclass(frozen=True)
class FileOperation:
    """File operation to execute relative to request_dir.

    Write mode overwrites existing files (last write wins).
    Orchestrator determines full path based on operation type.
    """
    filename: str  # Flat filename only (validated: no path separators)
    content: str
    mode: Literal["write", "append", "copy"]
    operation_type: Literal["context", "work", "session_log"]

    def validate(self):
        """Raise BlockingError if filename is invalid (resilience, not security)."""
        if "/" in self.filename or "\\" in self.filename or ".." in self.filename:
            raise BlockingError(f"Invalid filename: {self.filename}")
```

### Layer 4: Handlers

**File**: `lifecycle/handlers.py`

**Contains**:
- `EventHandler` - Abstract base class for business logic extension point
- Handler implementations (currently none)

No handlers registered. `_get_handler()` returns None.

All logic lives in orchestrator framework methods:
- `SessionStart` - Logged only
- `UserPromptSubmit` - Write prompt to context.md
- `SubagentStart` - Update agent_types in state
- `SubagentStop` - Extract context/work tags, copy transcript
- `Stop` - Extract session log snapshot

Handlers provide extension point for future domain-specific logic.

---

## Module Structure

```
ai-assisted-development/src/
├── agent-lifecycle.py          # Hook interface layer (main entry)
└── lifecycle/
    ├── __init__.py
    ├── orchestrator.py         # LifecycleOrchestrator + directory creation
    ├── models.py               # RequestContext, EventData, FileOperation
    ├── processing.py           # Data transformation (hook parsing, tag extraction)
    ├── errors.py               # BlockingError, NonBlockingError
    ├── state.py                # State, StateFile classes (extracted)
    └── handlers.py             # EventHandler ABC + all implementations
```

**Import Structure**:
- `agent-lifecycle.py` imports only `LifecycleOrchestrator` and error classes
- `orchestrator.py` imports models, handlers, state, processing
- `handlers.py` imports models, errors, processing functions

**File Size Guidelines**:
- Start with single `handlers.py` file
- If it exceeds ~500 lines, split into `handlers/` directory
- Other modules should remain focused and small

**Public API** (`lifecycle/__init__.py`):
```python
from .orchestrator import LifecycleOrchestrator
from .errors import BlockingError, NonBlockingError

__all__ = ["LifecycleOrchestrator", "BlockingError", "NonBlockingError"]
```

Tests can import from submodules directly (e.g., `from lifecycle.handlers import SubagentStopHandler`).

---

## Error Handling

**Custom Exceptions**:

```python
class BlockingError(Exception):
    """Raised to block operation and show error to agent (exit code 2)."""
    pass

class NonBlockingError(Exception):
    """Raised to log error but allow operation to continue (exit code 1)."""
    pass
```

**Flow**:
1. Handlers raise `BlockingError` for validation failures
2. Orchestrator raises `NonBlockingError` for I/O failures
3. Hook interface catches and maps to exit codes (2 or 1)
4. Errors written to stderr
5. Claude Code receives exit code

**Best-effort semantics**:
- I/O failures logged, agent continues (exit 1)
- Validation failures block agent (exit 2)
- Lifecycle tracking never breaks user workflow

**Benefits**:
- Pythonic (no manual exit codes)
- Clear semantics (blocking vs non-blocking)
- Hook layer owns protocol
- Failures don't cascade

---

## Benefits

**Testability**:
- Pure handlers (no mocking file I/O or State)
- Test: context + event → verify operations

**Extensibility**:
- New domain logic: add handler, register in `_get_handler()`
- New framework guarantees: add framework method
- Agent-specific routing: extend `_get_handler()` logic
- New file types: extend `operation_type` mapping

**Maintainability**:
- Clear separation of concerns
- Single responsibility per module
- Easy to locate code
- State isolated for evolution

**Forward-looking**:
- Extension points clear
- Agent-specific handlers later (no restructure)
- Operation pattern extends beyond files

---

## Migration Map

This refactor reorganizes code without rewriting logic. Here's what moves where:

### Code That Moves Unchanged

**State classes** (lines 18-190) → `lifecycle/state.py`:
- `StateFile` class
- `State` class

**Processing functions** → `lifecycle/processing.py`:
- `get_toolbox_root()` (line 192)
- `generate_request_id()` (line 224)
- `create_request_directory()` (line 244)
- `parse_context_tags()` (line 281)
- `parse_work_tags()` (line 288)

### Event Handlers Become Methods

Existing functions wrap into `LifecycleOrchestrator` methods. Logic stays identical:

- `handle_user_prompt_submit()` → `._handle_user_prompt_submit()`
- `handle_subagent_start()` → `._handle_subagent_start()`
- `handle_subagent_stop()` → `._handle_subagent_stop()`
- `handle_stop_event()` → `._handle_stop()`
- `handle_session_start()` → `._handle_session_start()`
- Other handlers → `._append_hook_event()` (simplified - they just log events)

### New Code

**Models** (`lifecycle/models.py`):
- `RequestContext` - wraps state data for handler access
- `EventData` - normalized hook input
- `FileOperation` - declarative file operations (unused now, extension point)

**Errors** (`lifecycle/errors.py`):
- `BlockingError` - validation failures (exit 2)
- `NonBlockingError` - I/O failures (exit 1)

**Handlers** (`lifecycle/handlers.py`):
- `EventHandler` ABC - extension point (no implementations)

**Orchestrator** (`lifecycle/orchestrator.py`):
- `LifecycleOrchestrator` class - wraps existing handler functions
- `._build_event_data()` - new, extracts fields from hook_input
- `._get_or_create_request_id()` - new, wraps generate_request_id logic
- `._build_request_context()` - new, loads state into RequestContext
- `._get_handler()` - new, returns None (extension point)
- `._persist_state_changes()` - new, wraps state.save()
- `._execute_file_operations()` - new, extension point (unused)

### What Changes

**main()** in `agent-lifecycle.py`:
- Replaces event dispatch with `LifecycleOrchestrator().process()`
- Adds exception handling for BlockingError/NonBlockingError

**Event routing**:
- Was: if/elif chain calling functions
- Now: if/elif chain calling orchestrator methods

Everything else is code movement, not rewriting.

---

## Implementation Notes

No migration path needed. This plugin exists only locally in development. No production users, no backwards compatibility concerns. Implement the design directly.

---

## Open Questions

None.

---

## References

- Current implementation: `ai-assisted-development/src/agent-lifecycle.py`
- Hook events: `docs/appendix/hook-input-messages.md`
- State management: Previous refactor established State/StateFile pattern
