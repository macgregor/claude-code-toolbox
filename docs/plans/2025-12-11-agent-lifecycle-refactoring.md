---
name: agent-lifecycle-refactoring
description: >
  Refactoring plan for agent-lifecycle.py to extract core patterns and improve
  maintainability. Establishes clean separation between hook interface, orchestration,
  state management, and event handlers.
created: 2025-12-11
status: design
---

# Agent Lifecycle Refactoring Design

**Created**: 2025-12-11
**Status**: Design

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

## Design Principles

1. **YAGNI** - Don't over-engineer or future-proof excessively
2. **Pure handlers** - Handlers should have no side effects (testable)
3. **Clear separation** - Hook protocol vs orchestration vs domain logic
4. **Forward-looking** - Easy to extend with routing logic later, but don't implement it yet
5. **Simple first** - Start with single files, split only when needed

---

## Core Patterns

### 1. Event Handler Pattern

**Interface**:
```python
class EventHandler(ABC):
    @abstractmethod
    def handle(self, context: RequestContext, event: EventData) -> RequestContext:
        """Process event and return modified context."""
        pass
```

**Characteristics**:
- Handlers are pure - no direct side effects
- Receive clean, normalized inputs
- Return modified context with declared operations
- Can raise `BlockingError` (exit 2) or `NonBlockingError` (exit 1)

### 2. State Management

**Existing Pattern** (already implemented):
- `State` class provides unified interface to dual-file storage
- `StateFile` handles file-backed dict with dirty tracking
- State lifecycle managed via context manager

**Enhancement**:
- Extract to `lifecycle/state.py` module
- `RequestContext` wraps state data for handler access
- Orchestrator manages State lifecycle and persistence

### 3. Data Processing

**Responsibilities**:
- Transform hook input → `EventData` (normalized, validated)
- Parse agent outputs (context/work tags)
- Extract/validate fields from hook_input dict
- Generate request IDs

**Centralized** in `lifecycle/processing.py`

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

**Key Points**:
- Minimal - just protocol translation
- Maps Python exceptions → hook exit codes
- No business logic

### Layer 2: Orchestrator

**File**: `lifecycle/orchestrator.py`

**Responsibility**: Coordinate hook processing, manage lifecycle, execute side effects

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

        # 3. Initialize context with state
        with State(toolbox_root, event_data.fields["session_id"],
                   event_data.fields.get("transcript_path")) as state:

            context = self._build_request_context(event_data, request_dir, state)

            # 4. Route to handler
            handler = self._get_handler(event_data.hook_event_name)
            updated_context = handler.handle(context, event_data)

            # 5. Execute side effects
            self._execute_file_operations(updated_context)
            self._persist_state_changes(state, context, updated_context)
            self._append_hook_event(request_dir, raw_hook_input)
```

**Key Methods**:
- `_build_event_data()` - Extract/validate fields, create EventData
- `_get_or_create_request_id()` - UserPromptSubmit creates, others lookup
- `_build_request_context()` - Load state data into RequestContext
- `_get_handler()` - Route event name to handler instance
- `_execute_file_operations()` - Write/append files from context
- `_persist_state_changes()` - Compare contexts, update State

**Also contains**:
- `create_request_directory()` - Directory structure creation (side effect owned by orchestrator)

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
    """File operation to execute relative to request_dir."""
    path: str  # Relative path (validated: no traversal, no duplicates)
    content: str
    mode: Literal["write", "append", "copy"]

    def validate(self):
        """Raise BlockingError if path is unsafe."""
        if "/" in self.path or "\\" in self.path or ".." in self.path:
            raise BlockingError(f"Invalid path: {self.path}")
```

### Layer 4: Handlers

**File**: `lifecycle/handlers.py`

**Contains**:
- `EventHandler` - Abstract base class
- All handler implementations (SubagentStop, SubagentStart, UserPromptSubmit, Stop, etc.)
- `PassthroughHandler` - For events that just need logging

**Example - SubagentStopHandler**:
```python
class SubagentStopHandler(EventHandler):
    def handle(self, context: RequestContext, event: EventData) -> RequestContext:
        agent_id = event.fields["agent_id"]
        transcript_path = Path(event.fields["agent_transcript_path"])
        agent_type = context.agent_types.get(agent_id, "unknown")

        # Read agent transcript (handler can read directly)
        if not transcript_path.exists():
            return context

        final_output = self._extract_final_output(transcript_path)

        # Parse tags (using processing.py utilities)
        contexts = parse_context_tags(final_output)
        work_items = parse_work_tags(final_output)

        # Validate
        for item in work_items:
            if "/" in item["filename"] or ".." in item["filename"]:
                raise BlockingError(f"Invalid filename: {item['filename']}")

        # Check for duplicates by reading existing files
        existing = list((context.request_dir / "work").glob("*"))
        for item in work_items:
            if any(f.name == item["filename"] for f in existing):
                raise BlockingError(f"Duplicate file: {item['filename']}")

        # Declare operations (no direct writes)
        if contexts:
            context_content = f'\n<agent-{agent_id} type="{agent_type}">\n'
            for ctx in contexts:
                context_content += ctx + '\n'
            context_content += f'</agent-{agent_id}>\n'

            context.file_operations.append(
                FileOperation(path="context.md", content=context_content, mode="append")
            )

        for item in work_items:
            context.file_operations.append(
                FileOperation(
                    path=f"work/{item['filename']}",
                    content=item["content"],
                    mode="write"
                )
            )

        # Copy transcript
        context.file_operations.append(
            FileOperation(
                path=f"session-logs/agent-{agent_id}.jsonl",
                content=transcript_path.read_text(),
                mode="write"
            )
        )

        return context
```

**Handler Characteristics**:
- Pure business logic
- Read from `context.request_dir` as needed
- Declare writes via `context.file_operations`
- Raise errors for control flow
- No direct file I/O for writes

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
1. Handlers/orchestrator raise typed exceptions
2. Hook interface layer catches and maps to exit codes
3. Error messages written to stderr
4. Claude Code receives exit code and acts accordingly

**Benefits**:
- Pythonic error handling (no manual exit codes in business logic)
- Clear semantic difference (blocking vs non-blocking)
- Hook interface owns protocol details

---

## Benefits

### Testability
- Handlers are pure functions - easy to unit test
- No mocking file I/O or State in handler tests
- Test: given context + event → verify returned operations

### Extensibility
- New hook events: add handler, register in orchestrator
- Agent-specific routing (future): extend `orchestrator._get_handler()`
- New side effects: extend `FileOperation` modes or add new operation types

### Maintainability
- Clear separation of concerns
- Each module has single responsibility
- Easy to locate code (hook protocol vs orchestration vs handlers)
- State management isolated for future evolution

### Forward-Looking
- Routing logic extension point clear (`_get_handler()`)
- Can add agent-specific handlers later without restructuring
- Operation pattern extensible (not just files - could add external API calls, etc.)

---

## Migration Strategy

1. **Create module structure**
   - Create `lifecycle/` directory and empty files
   - Add `__init__.py` exports

2. **Extract State** (lowest risk)
   - Move State/StateFile to `lifecycle/state.py`
   - Update imports in `agent-lifecycle.py`
   - Run tests

3. **Extract errors and models**
   - Create `BlockingError`, `NonBlockingError` in `lifecycle/errors.py`
   - Create domain objects in `lifecycle/models.py`
   - No behavioral changes yet

4. **Extract processing utilities**
   - Move parsing functions to `lifecycle/processing.py`
   - Move `get_toolbox_root`, `generate_request_id` to processing
   - Update imports

5. **Create orchestrator skeleton**
   - Implement `LifecycleOrchestrator.process()` flow
   - Keep using old handler functions temporarily
   - Test with one event type (e.g., UserPromptSubmit)

6. **Migrate handlers one-by-one**
   - Start with simplest (PassthroughHandler)
   - Convert each `handle_*` function to handler class
   - Update orchestrator routing
   - Test each handler migration

7. **Clean up old code**
   - Remove old `handle_*` functions from `agent-lifecycle.py`
   - Simplify `agent-lifecycle.py` to just hook interface
   - Final test pass

---

## Open Questions

None - design is complete and ready for implementation.

---

## References

- Current implementation: `ai-assisted-development/src/agent-lifecycle.py`
- Hook events: `docs/appendix/hook-input-messages.md`
- State management: Previous refactor established State/StateFile pattern
