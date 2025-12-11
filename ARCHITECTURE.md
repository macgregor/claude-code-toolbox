# Architecture

**Last Updated**: 2025-12-10

---

## Overview

Claude Code Toolbox provides infrastructure for multi-agent orchestration. The system uses [Claude Code hooks](docs/claude-code-reference.md#hooks) to observe agent execution and persist context, enabling agents to coordinate across sessions without tight coupling.

---

## Agent Lifecycle Foundation

### Purpose

Capture what happens during a user request: what the user asked for, which agents ran, what context they produced, and what work they generated.

### How It Works

**Request Scoping**: Each user prompt creates a request directory under `.toolbox/events/`. Everything related to that request—user prompt, agent outputs, session logs, hook events—goes there.

**Hook Integration**: Lifecycle hooks (SessionStart, UserPromptSubmit, SubagentStart, SubagentStop, Stop) observe execution and extract data:
- User prompts captured in `context.md`
- Agent `<context>` tags extracted and appended to `context.md`
- Agent `<work filename="...">` tags create files in `work/` directory
- Session logs pruned to request boundaries
- All hook events logged for debugging

**Why Hooks**: Hooks run outside agent context, allowing passive observation. Agents don't need to know about the orchestration system—they just output tags if they want to share context or create artifacts.

### What Gets Stored

Each request directory contains:
- `context.md` - User prompt + agent context extracts
- `work/` - Files agents create via `<work>` tags
- `session-logs/` - Agent transcripts and pruned session log
- `hook-events.jsonl` - Complete audit trail
- `.state.json` - Request-scoped state (start_uuid, agent_types)

Global state stored at `.toolbox/events/.global-state.json` maps session_id → request_id for concurrent session support

### Why This Design

**Agent Independence**: Agents remain simple. They output text tags; the system extracts them. No special tools or coordination logic required.

**Request Isolation**: Each request is self-contained. No cross-contamination between requests, easy to analyze or replay individual requests.

**File-Based State**: No databases or external services. Works anywhere Claude Code runs. Human-inspectable for debugging.

---

## Future Systems

As new orchestration capabilities are added (multi-agent workflows, work queues, session resumption), they will be documented here.
