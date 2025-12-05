# Plugin Debug System

Shows plugin version and extracts conversation traces for debugging agent behavior.

## Quick Start

Add to `.claude/settings.local.json`:

```json
{
  "env": {
    "CLAUDE_TOOLBOX_DEBUG": "1"
  },
  "statusLine": {
    "type": "command",
    "command": "ai-assisted-development/scripts/debug/statusline.sh"
  }
}
```

The statusline displays:
```
ai-assisted-development@claude-code-toolbox: v1.0.0 (5fff9f4) | Trace: fbb2e753
~/.claude/plugins/claude-code-toolbox/scripts/debug/extract-trace.py fbb2e753
```

Copy and run the extraction command to see full conversation logs.

## How It Works

### Statusline

Shows plugin version, git SHA, and current trace ID. Reads metadata from `~/.claude/plugins/installed_plugins.json` and trace ID from `/tmp/claude-trace-{session_id}`.

**Implementation**: `ai-assisted-development/scripts/debug/statusline.sh`

### Trace System

Uses distributed tracing concepts:
- **Trace ID**: User message UUID (identifies a conversation turn)
- **Span ID**: Tool use ID (identifies individual tool invocations)

Claude Code logs to `~/.claude/projects/{project}/{session_id}.jsonl`. This system provides extraction tools rather than duplicating logs.

### Trace Extraction

Run with trace ID from statusline:
```bash
~/.claude/plugins/claude-code-toolbox/scripts/debug/extract-trace.py fbb2e753
```

Walks the parent chain to collect all messages in the conversation turn. Stops at the next user message boundary.

**Implementation**: `ai-assisted-development/scripts/debug/extract-trace.py`

### Trace Capture

A PreToolUse hook runs before each tool execution. When `CLAUDE_TOOLBOX_DEBUG=1`:

1. Extracts trace ID by walking parent chain from tool use to user message
2. Compares to existing trace ID for this session
3. Updates `/tmp/claude-trace-{session_id}` if new turn detected

**Implementation**: `ai-assisted-development/scripts/debug/pre-tool-use-trace.sh`

**State files**:
- `/tmp/claude-trace-{session_id}` - Current trace ID
- `/tmp/claude-trace-info-{trace_id}` - Transcript path

## Claude Code Discovery: Tool Results as User Messages

Tool results appear in transcripts as `type: "user"` messages whose `parentUuid` points to an assistant message. This differs from actual user prompts.

**Message flow**:
```
user (prompt) UUID: abc123
  └─> assistant
      └─> assistant (with tool use) UUID: def456
          └─> user (tool result) UUID: ghi789  ← appears as "user" type!
              └─> assistant
```

Walking the parent chain encounters the tool result first. Naive implementations stop there, causing trace ID to change on every tool use. The fix skips user messages whose parent is an assistant message.

**Implementation**: See `extract-trace-id.sh` for the parent chain walking logic that handles this case.

## Disabling Debug Mode

Set to `0` or remove the configuration:

```json
{
  "env": {
    "CLAUDE_TOOLBOX_DEBUG": "0"
  }
}
```

## Design

**Statusline over Stop hooks**: Stop hooks didn't display output (`stop_hook_active:false`). Statusline updates automatically and is always visible.

**Extract, don't duplicate**: Claude Code logs everything. Duplicating wastes space and creates sync issues.

**Temp files for state**: Session isolation, automatic cleanup, no path passing required.

**Python for extraction**: Tree traversal with turn boundary detection. jq was complex and error-prone.

## Troubleshooting

**Statusline not showing**: Check `CLAUDE_TOOLBOX_DEBUG=1` is set. Verify statusline command path. Reload: `/plugin reload ai-assisted-development@claude-code-toolbox`

**Trace ID not updating**: Expected within a turn. Updates only when you submit a new prompt. If stuck, check `/tmp/claude-trace-*` files.

**Extraction fails**: Verify trace ID in statusline. Check `/tmp/claude-trace-info-{trace_id}` exists.

**Empty extraction**: Trace ID may be from different session. Try full UUID instead of prefix.

## Implementation Files

```
ai-assisted-development/scripts/debug/
  statusline.sh              # Statusline display
  extract-trace.py           # Extract conversation turn
  extract-trace-id.sh        # Find root user message UUID
  pre-tool-use-trace.sh      # PreToolUse hook
```

See `docs/plans/2025-12-05-plugin-debugging-versioning.md` for detailed design and rationale.
