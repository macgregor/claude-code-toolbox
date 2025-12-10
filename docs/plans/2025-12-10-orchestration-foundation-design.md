# Agent Orchestration Foundation - Design

**Date**: 2025-12-10
**Status**: Ready for Implementation
**Experiments Completed**: 2025-12-10 (SessionStart env vars, session log timing, UUID boundaries)

---

## Overview

The orchestration system builds on Claude Code's hook infrastructure to provide request-scoped tracking and context management. Each user prompt becomes an isolated "request" with dedicated storage for context, logs, and work artifacts.

**Core Concept**: Use hooks to capture lifecycle events and organize them by request ID. The system maintains a running context file that agents can read and append to, enabling context sharing across agent boundaries without relying on Claude Code's automatic context propagation.

**Key Components**:

1. **Request ID System**: Deterministic, lexicographically-sortable IDs derived from hook input (timestamp + hash)
2. **Environment Variables**: Session-stable paths and IDs using `$CLAUDE_ENV_FILE`
3. **Directory Structure**: Per-request directories in `.toolbox/events/<request-id>/`
4. **Context Checkpointing**: `context.md` file with XML-tagged sections for orchestrators and agents
5. **Event Capture**: Hook events, agent transcripts, and session logs stored for debugging

**Data Flow**:
- `SessionStart`: Establish workspace root (`TOOLBOX_ROOT`) via `$CLAUDE_ENV_FILE`
- `UserPromptSubmit`: Generate request ID, write to file-based state, create directory structure, initialize `context.md`, capture start UUID from session log
- `SubagentStop`: Copy agent transcript, parse `<context>` and `<work>` tags, append to context.md and work/ directory
- `Stop`: Read start UUID, extract end UUID, prune session log to request boundaries
- All hooks: Append to `hook-events.jsonl` if within active request

**Design Goals**: Deterministic (derive state from hook input), resilient (graceful error handling), non-blocking (always exit 0), and simple (minimal dependencies).

---

## Directory Structure

```
{TOOLBOX_ROOT}/.toolbox/
    events/
        .current-request-id                       # File-based state: active request ID
        2025-12-10T12-02-22.062_a7f3b9/          # Request ID (timestamp + hash)
            .start-uuid                           # Start boundary UUID from session log
            context.md                            # Checkpointed context (XML-tagged)
            hook-events.jsonl                     # Hook events for this request
            errors.log                            # Best-effort error log
            work/                                 # Agent work products
                analysis-report.json
                intermediate-data.csv
            session-logs/                         # Claude Code session logs
                635aa831-db31-46c5-92de-36aa251cd600-pruned.jsonl  # Session log (pruned to request)
                agent-30184ffa.jsonl              # Subagent transcripts
                agent-0df6ea1e.jsonl
```

**File Purposes**:

- **`.current-request-id`**: File-based state containing active request ID (updated on each UserPromptSubmit). All hooks read this to determine if they're within an active request.

- **`.start-uuid`**: UUID boundary marker for session log pruning. Written during UserPromptSubmit, read during Stop to determine extraction range.

- **`context.md`**: Human-readable checkpoint file with XML sections (`<userPrompt>`, `<agent-{id}>`). Hooks parse agent `<context>` output and append to this file. Orchestrators read to understand prior work. Created on `UserPromptSubmit` with initial user prompt.

- **`hook-events.jsonl`**: Raw hook input events (one JSON object per line). Filtered to only include events during this request's lifecycle. Useful for debugging hook execution order and timing.

- **`errors.log`**: Best-effort error capture. Hook scripts attempt to write errors here, but ignore failures (e.g., disk full). Not critical path.

- **`work/`**: Agent work products extracted from `<work>` tags. Hooks parse agent output and write files to paths specified in `path` attribute.

- **`session-logs/`**: Contains pruned session transcript (log lines between UserPromptSubmit and Stop) and copies of all subagent transcripts from `agent_transcript_path`.

---

## Environment Variables

**Contract**: Session-wide state persisted via `$CLAUDE_ENV_FILE` mechanism (SessionStart only).

**Confirmed Behavior**: Experiments confirmed that SessionStart hook can write to `$CLAUDE_ENV_FILE` and variables become available to all subsequent hooks in the session. Writing from other hook events is unconfirmed and not relied upon.

**Session-Wide Variable**:

- `TOOLBOX_ROOT`: Workspace root path (set once on SessionStart, stable across directory changes)

**Request-Scoped State** (file-based, NOT env vars):

- `.toolbox/events/.current-request-id`: Contains active request ID (updated on each UserPromptSubmit)

**Lifecycle**:
1. SessionStart establishes `TOOLBOX_ROOT` via `$CLAUDE_ENV_FILE`
2. UserPromptSubmit writes request ID to `.toolbox/events/.current-request-id`
3. All subsequent hooks read `TOOLBOX_ROOT` from env and request ID from file

**Why file-based for request ID**: Experiments confirmed that only SessionStart can write to `$CLAUDE_ENV_FILE`. Since request ID doesn't exist at session start, we must use file-based state for request-scoped data.

**Agent Context Access**: Agents don't need to discover context files. They output `<context>` and `<work>` tags, and hooks parse this output to route content to `context.md` and `work/` directory.

---

## Request ID Generation

**Requirements**:
- Deterministic: Same hook input produces same ID
- Unique: No collisions across requests
- Lexicographically sortable: Chronological ordering via timestamp prefix
- Zero dependencies: Standard library only

**Format**: `{timestamp}_{hash}`

Example: `2025-12-10T12-02-22.062247_a7f3b9c2`

**Derivation**:
- Timestamp: From `hook_input["timestamp"]` (already ISO format from hook)
- Hash: SHA256 of `{session_id}{timestamp}{prompt}`, truncated to 8 characters
- Colons in timestamp replaced with hyphens for filesystem safety

**Properties**:
- Sortable: Directory listings show chronological order
- Deterministic: Re-running same hook input generates identical ID
- Unique: Hash component prevents collisions from rapid-fire prompts
- Human-readable: Can identify request time at a glance

**Usage**: Generated once on UserPromptSubmit, used for directory name and stored in `TOOLBOX_CURRENT_REQUEST_ID` env var.

---

## Hook Event Handlers

**Contract**: Each hook event performs specific orchestration tasks. All operations are best-effort with graceful error handling.

**General Pattern**: All handlers read request ID from `.toolbox/events/.current-request-id` file and append to `hook-events.jsonl` if request is active. Some have additional actions.

### SessionStart
**Triggers**: Once per Claude Code session (not per request)

**Actions**:
- Capture `cwd` from hook input
- Write `TOOLBOX_ROOT={cwd}` to `$CLAUDE_ENV_FILE`
- Create `.toolbox/events/` directory structure if not exists

**Output**: None (silent success)

---

### SessionEnd
**Triggers**: Session termination

**Actions**:
- Append to `hook-events.jsonl` if within request
- No additional orchestration actions

**Output**: None (silent success)

---

### UserPromptSubmit
**Triggers**: Each user prompt submission

**Actions**:
- Generate request ID from hook input
- Write request ID to `.toolbox/events/.current-request-id` (file-based state)
- Read last line of session log at `transcript_path`, extract UUID, write to `.toolbox/events/{request_id}/.start-uuid`
- Create directory structure: `.toolbox/events/{request_id}/`
- Initialize `context.md` with `<userPrompt>` section containing the prompt
- Create empty directories: `work/`, `session-logs/`
- Create empty files: `hook-events.jsonl`, `errors.log`
- Append raw hook event to `hook-events.jsonl`

**Output**: None (silent success)

---

### PreToolUse
**Triggers**: Before tool execution

**Actions**:
- Append to `hook-events.jsonl` if within request

**Output**: None (silent success)

---

### PostToolUse
**Triggers**: After successful tool execution

**Actions**:
- Append to `hook-events.jsonl` if within request

**Output**: None (silent success)

---

### PostToolUseFailure
**Triggers**: After failed tool execution

**Actions**:
- Append to `hook-events.jsonl` if within request

**Output**: None (silent success)

**Note**: Could track failures separately in future enhancement

---

### PermissionRequest
**Triggers**: When tool requires permission decision

**Actions**:
- Append to `hook-events.jsonl` if within request
- No orchestration actions (permissions handled by user/config)

**Output**: None (silent success)

---

### SubagentStart
**Triggers**: When subagent begins execution

**Actions**:
- Append to `hook-events.jsonl` if within request

**Output**: None (silent success)

---

### SubagentStop
**Triggers**: When subagent completes execution

**Actions**:
- Append to `hook-events.jsonl` if within request
- Get `agent_transcript_path` from hook input
- Copy agent transcript to `{request_id}/session-logs/agent-{agent_id}.jsonl`
- Parse agent transcript (JSONL format, same structure as session log):
  - Read last assistant message from transcript
  - Extract message content (contains `<context>` and `<work>` tags)
- Parse `<context>` tags from final output:
  - Extract content, wrap with `<agent-{agent_id} type="{agent_type}">`
  - Append to `{request_id}/context.md`
- Parse `<work>` tags from final output:
  - Extract content and `relpath` attribute
  - Write content to `{request_id}/{relpath}` (path is relative to request directory)

**Error Handling**: Best-effort operations, graceful failure (log to stderr, don't block)

**Output**: None (silent success)

---

### Stop
**Triggers**: End of request handling (user prompt response complete)

**Actions**:
- Append to `hook-events.jsonl` if within request
- Extract and prune session log:
  - Read start UUID from `.toolbox/events/{request_id}/.start-uuid`
  - Read last line of session log to get end UUID (this IS the Stop event)
  - Extract all lines between start and end indices (inclusive of both boundaries)
  - Copy pruned log to `{request_id}/session-logs/{session_id}-pruned.jsonl`

**Note**: The last line when Stop hook fires IS the Stop event itself. We include it in the pruned log (inclusive boundaries).

**Error Handling**: Best-effort, graceful failure

**Output**: None (silent success)

---

### PreCompact
**Triggers**: Before context compaction

**Actions**:
- Append to `hook-events.jsonl` if within request

**Output**: None (silent success)

---

### Notification
**Triggers**: System notifications (e.g., idle prompt)

**Actions**:
- Append to `hook-events.jsonl` if within request

**Output**: None (silent success)

---

## Error Handling Strategy

**Principle**: Never block Claude Code execution. All operations are best-effort with graceful degradation.

**Error Handling Contract**:

1. **All file operations wrapped in try/except**
   - Catch all exceptions, don't let errors propagate
   - Log error context to stderr
   - Continue execution, exit 0

2. **Best-effort error log**
   - Attempt to write errors to `{request_id}/errors.log`
   - If error log write fails (disk full, permissions, etc.), swallow the error
   - Don't let error logging block the main error handler

3. **Output channels**
   - **stdout**: Info messages (visible in verbose mode ctrl+o)
   - **stderr**: Error messages (visible in verbose mode ctrl+o)
   - **Exit code**: Always 0 (non-blocking)

**Error Categories**:

- **Critical path failures**: Request ID generation, env var setup → Log to stderr, skip orchestration for this event
- **File operation failures**: Directory creation, file writes, transcript copies → Log to stderr, continue
- **Missing dependencies**: `TOOLBOX_ROOT` not set, `$CLAUDE_ENV_FILE` unavailable → Use fallbacks, log warnings

**Example Scenarios**:
- Can't create `.toolbox/events/` → Log error, skip request tracking, Claude continues normally
- Can't copy agent transcript → Log error, continue (transcript still available in Claude's project dir)
- Can't prune session log → Log error, continue (full session log still available)

**Key Constraint**: Orchestration system failures must not interfere with Claude Code's primary function (answering user prompts).

---

## Context.md Structure and Usage

**Purpose**: Checkpoint file for cross-agent context sharing and workflow resumption.

**Format**: Markdown with XML-tagged sections for structured parsing.

**Initial Structure** (created on UserPromptSubmit):
```markdown
<userPrompt>
{prompt text from hook_input}
</userPrompt>

<!-- Hooks append agent context below as agents complete -->
```

**Agent Output Pattern**:

Agents output structured data with `<context>` and `<work>` tags in their responses. Hooks (SubagentStop, PostToolUse) parse this output and route it to appropriate locations:

**Agent Output Example**:
```markdown
<context>
Searched: Python programming overview 2025
Key findings: Python 22.85% TIOBE rating, AI/ML dominance, Rust integration trend
Report: work/python-research-2025-12-10.json
</context>

<work relpath="work/python-research-2025-12-10.json" abspath="/absolute/path/to/.toolbox/events/2025-12-10T12-02-22.062_a7f3b9/work/python-research-2025-12-10.json">
{
  "summary": "Python ecosystem 2025 analysis",
  "findings": [...]
}
</work>
```

**Note**: The `relpath` attribute is relative to the request directory (`{request_id}/`). The optional `abspath` attribute provides the absolute path for clarity. Hooks use `relpath` to write files.

**Hook Processing**:
- SubagentStop parses agent output for `<context>` tags
- Wraps content with `<agent-{id} type="{type}">` tags
- Appends to `context.md`
- Extracts `<work>` tagged content and writes to specified paths in `work/` directory

**Final Context.md Example**:
```markdown
<userPrompt>
Research Python programming trends for 2025
</userPrompt>

<agent-30184ffa type="web-research">
Searched: Python programming overview 2025
Key findings: Python 22.85% TIOBE rating, AI/ML dominance, Rust integration trend
Report: work/python-research-2025-12-10.json
</agent-30184ffa>
```

**Design Principles**:
- **Hooks manage infrastructure**: Agents remain unaware of orchestration system
- **XML tags**: Enable structured parsing for routing and extraction
- **Agent IDs**: Match subagent IDs from hooks for traceability
- **Append-only**: Sequential narrative of agent work
- **Human-readable**: Designed for both parsing and human debugging

**Use Cases**:
1. Orchestrators read context.md to understand prior agent work
2. Humans debug workflows by reading chronological narrative
3. Checkpointing: Capture state for workflow resumption
4. Traceability: Link agent outputs to specific agent executions

---

## Session Log Pruning

**Objective**: Extract only log events related to current request from full session transcript.

**Challenge**: Session transcript at `transcript_path` contains all activity for the session (potentially multiple user prompts).

**Confirmed Approach** (validated via experiments):

**Session Log Timing**: Experiments confirmed that Claude Code writes the user message to the session log approximately 32ms BEFORE the UserPromptSubmit hook fires. This allows us to read the last line during the hook to capture the start UUID.

**UUID Boundary Extraction**:

1. **On UserPromptSubmit hook**:
   - Read session log at `transcript_path`
   - Get last line (the user message just written)
   - Parse JSON, extract `uuid` field
   - Store start UUID in `.toolbox/events/{request_id}/.start-uuid`

2. **On Stop hook**:
   - Read session log at `transcript_path`
   - Get last line (this IS the Stop event)
   - Parse JSON, extract `uuid` field for end boundary
   - Read `.toolbox/events/{request_id}/.start-uuid` for start boundary
   - Extract all lines between start and end line indices (inclusive of both boundaries)
   - Write to `{request_id}/session-logs/{session_id}-pruned.jsonl`

**Implementation Detail**: Simple line-based extraction works reliably - find line index where `uuid == start_uuid`, find line index where `uuid == end_uuid`, extract slice between indices. No complex parentUuid chain walking needed.

**Message Structure** (confirmed):
- All messages have: `uuid`, `parentUuid` (or null), `type`, `timestamp`, `sessionId`
- User messages: `type: "user"`, `message.role: "user"`
- Assistant messages: `type: "assistant"`, `message.role: "assistant"`
- System messages: `type: "system"`
- File snapshots: `type: "file-history-snapshot"`

---

## Testing Strategy

**Unit Testing Approach**:
- Test file: `ai-assisted-development/scripts/agent-lifecycle-test.py`
- Framework: Python standard library `unittest` (no dependencies)
- Test data: Real hook input examples from `.tmp/hook-logs/` and session logs

**Test Coverage**:

1. **Request ID Generation**
   - Deterministic: Same input produces same ID
   - Uniqueness: Different inputs produce different IDs
   - Sortability: Lexicographic ordering matches chronological
   - Format validation: Matches expected pattern

2. **Directory Structure Creation**
   - Creates all required directories
   - Handles existing directories gracefully
   - Creates `context.md` with correct initial content

3. **Hook Event Filtering**
   - Appends only when request ID is set
   - Skips when no active request
   - Valid JSONL output

4. **Context.md Initialization**
   - Properly formats `<userPrompt>` section
   - Escapes XML special characters in prompt text

5. **Error Handling**
   - Graceful failure on permission errors
   - Graceful failure on disk full
   - All operations return exit 0

**Test Data Sources**:
- Hook inputs: `.tmp/hook-logs/{session-id}.jsonl`
- Session logs: `~/.claude/projects/-workspace/{session-id}.jsonl`
- Create mock examples for edge cases

---

## Implementation Phases

**Experiments Completed** (2025-12-10):
- Confirmed SessionStart can write to `$CLAUDE_ENV_FILE`, variables available to all subsequent hooks
- Confirmed session log writes user message ~32ms BEFORE UserPromptSubmit hook fires
- Confirmed session log message structure (uuid, parentUuid, type, timestamp fields)
- Validated simple line-based UUID boundary extraction
- Determined hooks manage all orchestration, agents output `<context>` and `<work>` tags

**Phase 1 - Core Infrastructure**:
- Implement request ID generation
- SessionStart handler: Set `TOOLBOX_ROOT`
- UserPromptSubmit handler: Create directory structure, initialize `context.md`
- Basic hook event logging to `hook-events.jsonl`
- Unit tests for core functionality

**Phase 2 - Agent Integration**:
- SubagentStop handler: Copy agent transcripts, parse agent output for `<context>` and `<work>` tags
- Implement context.md append logic (wrap with `<agent-{id}>` tags)
- Implement work file extraction and writing
- Test with real subagent executions outputting structured tags

**Phase 3 - Session Log Pruning**:
- Implement UUID extraction in UserPromptSubmit (read last line, store start UUID)
- Stop handler: Read start UUID, extract end UUID, prune and copy session logs
- Validate boundary extraction correctness with multi-request sessions

**Phase 4 - Enhanced Features** (future):
- Advanced orchestrator patterns and templates
- Context summarization for long-running workflows
- Work artifact indexing and search

**Success Criteria**:
- Complete event logs for multi-agent workflows (hook-events.jsonl, session logs, agent transcripts)
- Agents output `<context>` and `<work>` tags, hooks route to appropriate locations
- Human-readable context.md provides chronological narrative of agent work
- Zero disruption to Claude Code operation (all errors graceful, exit 0)

---

## Dependencies

- Python 3.x (standard library only)
- Claude Code v2.0.43+ (for SubagentStart hook)
- No external Python packages

---

## References

- `docs/claude-code-reference.md` - Claude Code platform features
- `docs/research/web/2025-12-10-claude-code-hooks-subagents-observability.md` - Hooks research
- `ai-assisted-development/hooks/hooks.json` - Current hook configuration
- `ai-assisted-development/scripts/agent-lifecycle.py` - Current implementation
