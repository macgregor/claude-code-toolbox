---
name: hook-input-messages
description: >
  Use when implementing hooks or parsing hook event data. Documents all hook event types,
  message schemas, and usage patterns for lifecycle tracking and automation.
categories: [reference, platform]
tags: [hooks, events, automation, lifecycle]
related_docs:
  - docs/claude-code-reference.md
  - docs/appendix/session-log-messages.md
  - ARCHITECTURE.md
complexity: intermediate
---

# Claude Code Hook Input Messages

**Last Updated**: 2025-12-10

---

## Overview

Hook input messages are event notifications passed to hook scripts during Claude Code lifecycle events. They enable automation, orchestration, and observability without modifying agent behavior.

**Location**: `.toolbox/events/{request_id}/hook-events.jsonl`

**Message Structure**: Flat JSON objects with `hook_event_name` field identifying the event type

**Common Fields**: All hook inputs include `session_id`, `transcript_path`, `cwd`, `hook_event_name`

**Key Difference from Session Logs**: Hook inputs are NOT conversation messages - they are event notifications passed to hook scripts. They lack the nested `message` structure and conversation-oriented fields like `isSidechain`, `uuid`, `timestamp`.

---

## Hook Event Types

### UserPromptSubmit

Fired when a user submits a prompt to Claude Code.

```json
{
  "session_id": "338a2bf2-9a80-4ec6-8cc6-cac916b62270",
  "transcript_path": "/home/claude-user/.claude/projects/-workspace/338a2bf2-9a80-4ec6-8cc6-cac916b62270.jsonl",
  "cwd": "/workspace",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "we modified document-reviewer agent. spawn it and have it review ARCHITECTURE.md"
}
```

**Use Cases**:
- Capture user intent at request boundaries
- Initialize request-scoped state
- Log user prompts for analysis

---

### PreToolUse

Fired before a tool is executed.

```json
{
  "session_id": "338a2bf2-9a80-4ec6-8cc6-cac916b62270",
  "transcript_path": "/home/claude-user/.claude/projects/-workspace/338a2bf2-9a80-4ec6-8cc6-cac916b62270.jsonl",
  "cwd": "/workspace",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "PreToolUse",
  "tool_name": "Task",
  "tool_input": {
    "description": "Review ARCHITECTURE.md document",
    "prompt": "Please review the ARCHITECTURE.md document...",
    "subagent_type": "ai-assisted-development:document-reviewer"
  },
  "tool_use_id": "toolu_vrtx_01Ps8LMbrdRojFTY5x3sS4ik"
}
```

**Use Cases**:
- Validate tool inputs before execution
- Block operations with Exit Code 2
- Log tool invocations

---

### PostToolUse

Fired after a tool completes execution.

```json
{
  "session_id": "338a2bf2-9a80-4ec6-8cc6-cac916b62270",
  "transcript_path": "/home/claude-user/.claude/projects/-workspace/338a2bf2-9a80-4ec6-8cc6-cac916b62270.jsonl",
  "cwd": "/workspace",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "PostToolUse",
  "tool_name": "Glob",
  "tool_input": {
    "pattern": "ARCHITECTURE.md",
    "path": "/workspace"
  },
  "tool_response": {
    "filenames": ["/workspace/ARCHITECTURE.md"],
    "durationMs": 495,
    "numFiles": 1,
    "truncated": false
  },
  "tool_use_id": "toolu_vrtx_01VLsDasyRDWbqSEdh87PFvu"
}
```

**Use Cases**:
- Extract data from tool responses
- Log tool execution metrics
- Trigger downstream workflows

---

### SubagentStart

Fired when a subagent begins execution.

```json
{
  "session_id": "338a2bf2-9a80-4ec6-8cc6-cac916b62270",
  "transcript_path": "/home/claude-user/.claude/projects/-workspace/338a2bf2-9a80-4ec6-8cc6-cac916b62270.jsonl",
  "cwd": "/workspace",
  "hook_event_name": "SubagentStart",
  "agent_id": "83c40a7b",
  "agent_type": "ai-assisted-development:document-reviewer"
}
```

**Use Cases**:
- Track agent lifecycle
- Initialize agent-scoped state
- Log agent invocations

**Note**: Fires for BOTH slash command and Task tool invocations. Requires matcher configuration (use `"*"` to capture all agents).

---

### SubagentStop

Fired when a subagent completes execution.

```json
{
  "session_id": "338a2bf2-9a80-4ec6-8cc6-cac916b62270",
  "transcript_path": "/home/claude-user/.claude/projects/-workspace/338a2bf2-9a80-4ec6-8cc6-cac916b62270.jsonl",
  "cwd": "/workspace",
  "hook_event_name": "SubagentStop",
  "agent_id": "83c40a7b",
  "agent_transcript_path": "/home/claude-user/.claude/projects/-workspace/agent-83c40a7b.jsonl"
}
```

**Note**: Missing `agent_type` field (present in SubagentStart but not SubagentStop).

**Use Cases**:
- Extract agent outputs via XML tags (`<context>`, `<work>`)
- Validate agent output quality (Exit Code 2 blocks progression)
- Trigger handoffs to next agent
- Append agent context to parent scope

---

### Stop

Fired when the assistant stops generating a response.

```json
{
  "session_id": "338a2bf2-9a80-4ec6-8cc6-cac916b62270",
  "transcript_path": "/home/claude-user/.claude/projects/-workspace/338a2bf2-9a80-4ec6-8cc6-cac916b62270.jsonl",
  "cwd": "/workspace",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "Stop",
  "stop_hook_active": false
}
```

**Use Cases**:
- Checkpoint state at response boundaries
- Trigger post-response workflows
- Log response completion

---

### SessionStart

Fired when a new Claude Code session begins.

**Note**: SessionStart hook event is expected to exist based on hook configuration patterns, but was not observed in the analyzed logs. It may not be generated in typical workflows or may require specific configuration.

**Expected location**: `.toolbox/events/{request_id}/hook-events.jsonl`

**Expected fields**: Similar to other hook events with `session_id`, `transcript_path`, `cwd`, `hook_event_name: "SessionStart"`

**Expected use cases**:
- Initialize session-scoped state
- Set up monitoring/logging
- Load session context

---

### SessionEnd

Fired when a Claude Code session ends.

```json
{
  "session_id": "338a2bf2-9a80-4ec6-8cc6-cac916b62270",
  "transcript_path": "/home/claude-user/.claude/projects/-workspace/338a2bf2-9a80-4ec6-8cc6-cac916b62270.jsonl",
  "cwd": "/workspace",
  "hook_event_name": "SessionEnd",
  "reason": "clear"
}
```

**Use Cases**:
- Clean up session-scoped state
- Archive session artifacts
- Log session completion

---

### Notification

Fired when Claude Code generates a notification.

```json
{
  "session_id": "338a2bf2-9a80-4ec6-8cc6-cac916b62270",
  "transcript_path": "/home/claude-user/.claude/projects/-workspace/338a2bf2-9a80-4ec6-8cc6-cac916b62270.jsonl",
  "cwd": "/workspace",
  "hook_event_name": "Notification",
  "message": "Claude is waiting for your input",
  "notification_type": "idle_prompt"
}
```

**Use Cases**:
- Track system notifications
- Trigger alerts based on notification type
- Log user interaction patterns

---

## Hook Configuration

Hooks are configured in `hooks.json` with matchers for specific events:

```json
{
  "SubagentStart": [
    {
      "matcher": "*",
      "command": "callback"
    }
  ],
  "SubagentStop": [
    {
      "matcher": "*",
      "command": "callback"
    }
  ]
}
```

**Matcher Best Practices**:
- Use `"*"` for universal lifecycle tracking (all tools/agents)
- Use specific tool names for targeted behavior (e.g., `"matcher": "Task"`)
- Use agent names for agent-specific hooks (e.g., `"matcher": "document-reviewer"`)
- SubagentStart/SubagentStop matchers apply to agent type names, not tool names

---

## Exit Code Behavior

Hooks can control execution flow via exit codes:

- **Exit Code 0**: Success, continue normally
- **Exit Code 2**: Block operation and show error message to agent
- **Other codes**: Treated as errors, operation continues

**Quality Gate Pattern**:
```bash
# In SubagentStop hook
if ! validate_agent_output; then
  echo "Error: Agent output below quality threshold" >&2
  exit 2
fi
```

This blocks progression until the agent produces acceptable output.

---

## Use Cases

Hook input messages enable:

**Lifecycle Tracking**:
- Monitor agent execution (SubagentStart/SubagentStop)
- Track tool usage (PreToolUse/PostToolUse)
- Capture request boundaries (UserPromptSubmit/Stop)

**Automation Workflows**:
- Extract agent outputs via XML tags
- Trigger downstream processes
- Coordinate multi-agent workflows

**Quality Gates**:
- Validate outputs before handoffs
- Block operations until standards met
- Enforce workflow constraints

**Observability**:
- Log complete execution history
- Analyze agent behavior patterns
- Debug workflow issues

---

## Related Documentation

- [Session Log Messages](session-log-messages.md) - Conversation history and state
- [Claude Code Reference](../claude-code-reference.md#hooks) - Hook configuration and patterns
