# SubagentStart Hook Monitoring - Session Context

**Date**: 2025-12-10
**Status**: Ready to test SubagentStart hook behavior

## What We're Testing

We're investigating when the `SubagentStart` hook fires vs `SubagentStop`. SubagentStart was added in Claude Code v2.0.43, but we've observed it only fires under certain conditions.

## What We've Discovered

### Confirmed Facts
1. ✅ **SubagentStart exists** - Added in v2.0.43, confirmed in CHANGELOG and TypeScript SDK
2. ✅ **Our hooks are configured correctly** - `/workspace/ai-assisted-development/hooks/hooks.json` has SubagentStart with `"*"` matcher
3. ✅ **SubagentStart DOES fire** - We captured it in session `86900956` when user manually executed `/web-research` slash command
4. ✅ **SubagentStart does NOT fire** - When programmatically invoking subagents via Task tool in session `09a4897a`

### Key Finding
**Slash command invocation** (e.g., `/web-research`) triggers SubagentStart
**Task tool invocation** (programmatic) does NOT trigger SubagentStart

### Evidence
Session 86900956 (slash command):
```json
{"event":"SubagentStart","agent_id":"81544944","session":"86900956"}
{"event":"SubagentStart","agent_id":"83f44e1a","session":"86900956"}
```

Session 09a4897a (Task tool):
```json
{"event":"SubagentStop","agent_id":"453b2866","session":"09a4897a"}  // No SubagentStart!
{"event":"SubagentStop","agent_id":"3c126dfb","session":"09a4897a"}  // No SubagentStart!
```

## Current Setup

### Session-Scoped Logging
Hook events are now logged to TWO locations to prevent session clobbering:

1. **Global log** (all sessions): `/workspace/tmp/hook-events.jsonl`
2. **Per-session logs**: `/workspace/tmp/hook-logs/{session_id}.jsonl`

### Hook Configuration
Location: `/workspace/ai-assisted-development/hooks/hooks.json`

Configured events:
- PreToolUse, PostToolUse
- UserPromptSubmit, Notification, Stop
- SessionStart, PreCompact
- **SubagentStart** ← We're testing this
- **SubagentStop** ← This works reliably

### Logging Script
Location: `/workspace/ai-assisted-development/scripts/agent-lifecycle.py`

All hook events are logged with:
- `timestamp` (ISO format)
- `event` (hook event name)
- All fields from hook input (session_id, agent_id, etc.)

## Test Plan

### Setup (DONE)
- [x] Updated logging to be session-scoped
- [x] Committed changes to git
- [x] Created monitoring context file

### Test Execution (IN PROGRESS)
1. **Start two new Claude Code sessions**:
   - Monitoring session (reads logs)
   - Test session (triggers hooks)

2. **In test session, execute**:
   - Slash command: `/web-research <some query>`
   - This should trigger SubagentStart

3. **In monitoring session, watch for**:
   - New session file appearing in `/workspace/tmp/hook-logs/`
   - SubagentStart events in that session's log

## Monitoring Commands

### Watch for new sessions
```bash
ls -lt /workspace/tmp/hook-logs/
```

### Monitor specific session
Replace `{SESSION_ID}` with the new session ID:
```bash
# Watch file grow in real-time
tail -f /workspace/tmp/hook-logs/{SESSION_ID}.jsonl

# Count events by type
jq -r '.event' /workspace/tmp/hook-logs/{SESSION_ID}.jsonl | sort | uniq -c

# Show SubagentStart events
grep SubagentStart /workspace/tmp/hook-logs/{SESSION_ID}.jsonl | jq .

# Show all subagent events
jq -c 'select(.event == "SubagentStart" or .event == "SubagentStop") | {event, agent_id, timestamp}' /workspace/tmp/hook-logs/{SESSION_ID}.jsonl
```

### Compare with global log
```bash
# Show all SubagentStart events across all sessions
jq -c 'select(.event == "SubagentStart") | {event, agent_id, session: .session_id[0:8]}' /workspace/tmp/hook-events.jsonl
```

## Expected Results

If slash command triggers SubagentStart:
- SessionStart event
- SubagentStart event(s) with agent_id
- PreToolUse/PostToolUse events
- SubagentStop event(s) matching the agent_ids

If Task tool does NOT trigger SubagentStart:
- PreToolUse for Task tool
- SubagentStop event with agent_id
- NO SubagentStart event

## Research Documents

For more context, see:
- `/workspace/docs/research/web/2025-12-10-claude-code-hooks-subagents-observability.md` - Comprehensive research on hooks
- `/workspace/docs/claude-code-agent-considerations.md` - General agent architecture

## Git Status

Latest relevant commits:
```
66f5705 feat(hooks): add session-scoped logging to prevent clobbering
dcd6fad fix: restore SubagentStart hook (new hook from ~3 weeks ago)
e1ebad7 fix(hooks): prevent SubagentStop infinite loop for non-JSON agents
```

Plugin is ready for testing. All changes committed and pushed.

## Questions to Answer

1. Does slash command invocation (`/web-research`) trigger SubagentStart?
2. Does Task tool invocation trigger SubagentStart?
3. Are there other conditions that affect when SubagentStart fires?
4. What's the difference in how Claude Code handles slash commands vs Task tool?

---

**Next Steps**: Monitor the test session and observe whether SubagentStart fires when the slash command is executed.
