# Plugin Debugging & Versioning System

## Overview

Tools for debugging and versioning the ai-assisted-development plugin during development and use. Addresses two key problems:
1. Knowing exactly what version of the plugin is installed
2. Debugging agent/subagent behavior through trace logging

## Scope

### In Scope
- Statusline showing plugin version and trace extraction commands
- Trace logging system that extracts request flow from Claude Code's session logs
- Debug mode controlled by environment variable
- Development-only hook to detect plugin version mismatches

### Out of Scope
- Log analysis/visualization tools (future iteration)
- Automatic plugin updates
- Performance profiling

## Design

### 1. Debug Statusline

**Location**: `ai-assisted-development/scripts/debug/statusline.sh`

When `CLAUDE_TOOLBOX_DEBUG=1` is set, the statusline displays:
- Line 1: Plugin version, git SHA, and current trace ID
- Line 2: Full jq command to extract the trace

The statusline script:
- Reads plugin metadata from `~/.claude/plugins/installed_plugins.json`
- Reads current trace ID from `/tmp/claude-trace-{session_id}`
- Generates the jq extraction command using session's transcript path
- Outputs nothing when debug mode is disabled

**Output format**:
```
ai-assisted-development@claude-code-toolbox: v1.0.0 (5fff9f4) | Trace: abc12345
~/path/to/plugin/scripts/debug/extract-trace.py abc12345
```

Users copy the extraction command from the statusline and run it. The script finds the transcript path from cached trace info.

### 2. Trace Logging System

Uses OpenTelemetry-inspired distributed tracing concepts:
- **Trace ID**: User message UUID (root of all work for that request)
- **Span ID**: Tool use ID (unique identifier for each tool invocation)

Claude Code already logs all activity to session transcripts (`~/.claude/projects/{project}/{session_id}.jsonl`). Instead of duplicating logs, we extract the trace boundary and provide a command to filter the existing logs.

#### How It Works

**PreToolUse Hook** (first tool in a trace):
1. Receives JSON on STDIN with `tool_use_id` and `transcript_path`
2. Searches transcript for assistant message containing that `tool_use_id`
3. Walks `parentUuid` chain until finding `type: "user"` message
4. That user message's `uuid` is the trace_id
5. Stores trace_id in `/tmp/claude-trace-{session_id}` (for statusline to read)
6. Stores transcript path in `/tmp/claude-trace-info-{trace_id_prefix}` (for extraction script)

**Statusline Script** (runs on every message update):
1. Checks if `CLAUDE_TOOLBOX_DEBUG` env var is set
2. If not set: outputs nothing (statusline hidden)
3. If set:
   - Reads plugin metadata from installed_plugins.json
   - Reads trace_id from `/tmp/claude-trace-{session_id}`
   - Generates jq command using trace_id and transcript path
   - Outputs version info and extraction command

The statusline updates automatically after each message, showing the current trace.

#### Debug Mode

Enable trace logging by setting `CLAUDE_TOOLBOX_DEBUG=1` environment variable. Users can set this:
- In `.claude/settings.json` (if it supports env vars)
- Export in their shell
- Pass when launching Claude Code

Our scripts only check for the env var - don't care how it's set.

### 3. Development Plugin Sync Check

**Location**: `/workspace/.claude/settings.local.json` (this repo only, not packaged)

Project-specific hook that:
- Compares installed plugin git SHA vs workspace git HEAD
- Warns when out of sync during rapid development
- Uses `systemMessage` to alert developer

This is only useful when developing the plugin itself, not for users of the plugin.

## File Organization

```
ai-assisted-development/
  scripts/
    debug/
      statusline.sh                  # Statusline script for debug info
      extract-trace.py               # Extract trace logs by trace ID
      extract-trace-id.sh            # Extract trace_id from tool_use_id
      pre-tool-use-trace.sh          # PreToolUse hook for trace capture
  hooks/
    hooks.json                       # Hook configuration

.claude/                             # Development-only (this repo)
  settings.local.json                # Contains dev sync check hook and statusline config
  scripts/
    check-plugin-sync.sh             # Warns when installed plugin out of sync
```

## Implementation Details

### Statusline Script (`statusline.sh`)

```bash
#!/bin/bash

# Only show debug info if debug mode enabled
if [ -z "$CLAUDE_TOOLBOX_DEBUG" ]; then
  exit 0
fi

# Parse session data from stdin
SESSION_DATA=$(cat)
SESSION_ID=$(echo "$SESSION_DATA" | jq -r '.session_id // ""')
TRANSCRIPT=$(echo "$SESSION_DATA" | jq -r '.transcript_path // ""')

# Get plugin metadata
PLUGIN_ID="ai-assisted-development@claude-code-toolbox"
INSTALLED_JSON="$HOME/.claude/plugins/installed_plugins.json"
VERSION=$(jq -r ".plugins[\"$PLUGIN_ID\"].version // \"unknown\"" "$INSTALLED_JSON" 2>/dev/null)
INSTALLED_SHA=$(jq -r ".plugins[\"$PLUGIN_ID\"].gitCommitSha // \"unknown\"" "$INSTALLED_JSON" 2>/dev/null)

# Get current trace ID for this session
TRACE_ID=""
if [ -n "$SESSION_ID" ]; then
  TRACE_ID=$(cat "/tmp/claude-trace-$SESSION_ID" 2>/dev/null || echo "")
fi

# Build status line
if [ -n "$TRACE_ID" ]; then
  # Show version + trace info
  echo "Plugin: v${VERSION} (${INSTALLED_SHA:0:7}) | Trace: ${TRACE_ID:0:8}"
  echo "jq 'select(.uuid == \"$TRACE_ID\" or (.parentUuid // \"\" | contains(\"$TRACE_ID\")))' $TRANSCRIPT"
else
  # Just show version
  echo "Plugin: v${VERSION} (${INSTALLED_SHA:0:7}) | Debug mode active"
fi
```

### Trace Extraction Script (`extract-trace.py`)

Python script that performs tree traversal to extract all messages in a conversation turn. Stops at the next user message boundary to avoid including multiple turns.

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def find_transcript(trace_id_prefix):
    """Find transcript path from trace info file or most recent."""
    trace_info = Path(f"/tmp/claude-trace-info-{trace_id_prefix}")
    if trace_info.exists():
        return trace_info.read_text().strip()

    # Fallback to most recent
    project_dir = Path.home() / ".claude/projects/-workspace"
    if project_dir.exists():
        transcripts = sorted(project_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if transcripts:
            return str(transcripts[0])
    return None

def extract_trace(transcript_path, trace_id_prefix):
    """Extract all messages in a conversation turn."""
    messages = []
    with open(transcript_path) as f:
        for line in f:
            messages.append(json.loads(line))

    # Find root message
    root = next((m for m in messages if m['uuid'].startswith(trace_id_prefix)), None)
    if not root:
        return []

    # Build set of all UUIDs in trace by following parent chain
    # Stop when we hit another user message (next turn)
    trace_uuids = {root['uuid']}
    changed = True
    while changed:
        changed = False
        for msg in messages:
            parent_uuid = msg.get('parentUuid')
            if parent_uuid and parent_uuid in trace_uuids and msg['uuid'] not in trace_uuids:
                # Stop if this is a user message (marks start of next turn)
                if msg.get('type') == 'user':
                    continue
                trace_uuids.add(msg['uuid'])
                changed = True

    # Return messages in original order
    return [m for m in messages if m['uuid'] in trace_uuids]

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: extract-trace.py <trace-id-prefix>", file=sys.stderr)
        sys.exit(1)

    trace_id = sys.argv[1]
    transcript = find_transcript(trace_id)

    if not transcript:
        print(f"Error: No transcript found for trace {trace_id}", file=sys.stderr)
        sys.exit(1)

    for msg in extract_trace(transcript, trace_id):
        print(json.dumps(msg))
```

### Trace ID Extraction Script (`extract-trace-id.sh`)

Walks the parent chain to find the root user message UUID. Uses content structure analysis to distinguish actual user input from system-generated messages.

```bash
#!/bin/bash
# Extract trace_id from tool_use_id by walking transcript parent chain

HOOK_DATA=$(cat)
TOOL_USE_ID=$(echo "$HOOK_DATA" | jq -r '.tool_use_id')
TRANSCRIPT=$(echo "$HOOK_DATA" | jq -r '.transcript_path')

# Find the message containing this tool_use_id
MESSAGE_UUID=$(grep "$TOOL_USE_ID" "$TRANSCRIPT" | jq -r 'select(.message.content[]?.id == "'"$TOOL_USE_ID"'") | .uuid' | head -1)

if [ -z "$MESSAGE_UUID" ]; then
  echo "unknown"
  exit 0
fi

# Walk up parent chain to find user message
# Use content structure to distinguish real user input from system messages
CURRENT_UUID="$MESSAGE_UUID"
while [ -n "$CURRENT_UUID" ]; do
  MESSAGE=$(grep "\"uuid\":\"$CURRENT_UUID\"" "$TRANSCRIPT" | head -1)
  TYPE=$(echo "$MESSAGE" | jq -r '.type')
  PARENT_UUID=$(echo "$MESSAGE" | jq -r '.parentUuid')

  if [ "$TYPE" = "user" ]; then
    # Check content structure to distinguish message types
    CONTENT_TYPE=$(echo "$MESSAGE" | jq -r '.message.content | type')

    if [ "$CONTENT_TYPE" = "array" ]; then
      # Check if tool result (array with tool_result type)
      FIRST_ELEM_TYPE=$(echo "$MESSAGE" | jq -r '.message.content[0].type // empty')
      if [ "$FIRST_ELEM_TYPE" = "tool_result" ]; then
        # Tool result - keep walking
        CURRENT_UUID="$PARENT_UUID"
        continue
      fi

      # Check if command expansion (array with parent=user)
      if [ "$PARENT_UUID" != "null" ] && [ -n "$PARENT_UUID" ]; then
        PARENT_MESSAGE=$(grep "\"uuid\":\"$PARENT_UUID\"" "$TRANSCRIPT" | head -1)
        PARENT_TYPE=$(echo "$PARENT_MESSAGE" | jq -r '.type')

        if [ "$PARENT_TYPE" = "user" ]; then
          # Command expansion - keep walking
          CURRENT_UUID="$PARENT_UUID"
          continue
        fi
      fi

      # Unknown array type - keep walking to be safe
      CURRENT_UUID="$PARENT_UUID"
      continue
    fi

    # String content = real user message (prompt or command)
    echo "$CURRENT_UUID"
    exit 0
  fi

  CURRENT_UUID="$PARENT_UUID"
  if [ "$CURRENT_UUID" = "null" ]; then
    CURRENT_UUID=""
  fi
done

echo "unknown"
```

### PreToolUse Hook (`pre-tool-use-trace.sh`)

Captures trace ID on tool use and updates when the trace changes (new user turn detected).

```bash
#!/bin/bash

if [ -z "$CLAUDE_TOOLBOX_DEBUG" ]; then
  exit 0
fi

HOOK_DATA=$(cat)
SESSION_ID=$(echo "$HOOK_DATA" | jq -r '.session_id')
TRANSCRIPT=$(echo "$HOOK_DATA" | jq -r '.transcript_path')
TOOL_USE_ID=$(echo "$HOOK_DATA" | jq -r '.tool_use_id')

# Get existing trace for this session
EXISTING_TRACE=$(cat "/tmp/claude-trace-$SESSION_ID" 2>/dev/null || echo "")

# Extract trace_id for this request
TRACE_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/debug/extract-trace-id.sh" <<< "$HOOK_DATA")

# Only update if this is a new trace (new user message/turn)
if [ "$EXISTING_TRACE" != "$TRACE_ID" ]; then
  echo "$TRACE_ID" > "/tmp/claude-trace-$SESSION_ID"
  echo "$TRANSCRIPT" > "/tmp/claude-trace-info-${TRACE_ID:0:8}"
fi

exit 0
```

### Hook Configuration (`hooks/hooks.json`)

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/scripts/debug/pre-tool-use-trace.sh"
      }]
    }]
  }
}
```

## Usage

### Enabling Debug Mode

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

Or export before launching Claude Code:
```bash
export CLAUDE_TOOLBOX_DEBUG=1
claude
```

When enabled, the statusline will display:
- Plugin version and git SHA
- Current trace ID
- Extraction command to retrieve the trace logs

### Extracting a Trace

Copy the extraction command directly from the statusline and run it:
```bash
ai-assisted-development/scripts/debug/extract-trace.py abc12345
```

The script automatically finds the transcript path from cached trace info in `/tmp/claude-trace-info-{trace_id}`.

This shows all messages and tool uses for that specific user request in JSON format.

## Design Rationale

### Why Not Duplicate Logs?

Claude Code logs everything to session transcripts. Duplicating logs would waste disk space, create sync issues, and add complexity. We provide the trace boundary and extract from existing logs when needed.

### Why Statusline Instead of Stop Hooks?

Initial design used Stop hooks with `systemMessage`, but `stop_hook_active:false` in hook data prevented output. Statusline is always visible when debug mode is enabled, updates automatically, provides persistent trace info, and avoids hook output mechanisms.

### Why Environment Variable for Debug Mode?

Simple, standard, flexible. Users set it in project settings, shell export, or command-line.

### Why Temporary Trace Files?

Two temp file types provide clean separation:
- `/tmp/claude-trace-{session_id}` - Current trace ID for statusline
- `/tmp/claude-trace-info-{trace_id}` - Transcript path for extraction

Session-specific isolation, automatic cleanup, no transcript path passing, simple read/write, no project directory clutter.

## Claude Code Internals Discovered

### User Message Taxonomy

Through experimental analysis of actual Claude Code transcripts, we discovered that `type: "user"` messages fall into exactly **four categories**. Distinguishing them requires examining **content structure**, not just parent relationships.

#### The Four User Message Types

1. **Real User Prompts** (ACCEPT as trace root)
   - Content: `string` (plain text)
   - Parent: `null` (first message) OR `assistant` (continuation)
   - Example: `"@file.py i want to add..."`

2. **Slash Command Messages** (ACCEPT as trace root)
   - Content: `string` containing `<command-message>` tags
   - Parent: `assistant` (previous response)
   - Example: `"<command-message>brainstorm is running…</command-message>\n<command-name>/brainstorm</command-name>..."`
   - Note: Represents user's actual slash command input

3. **Tool Results** (SKIP - continue walking)
   - Content: `array` with first element `type: "tool_result"`
   - Parent: `assistant` (the tool use)
   - Example: `[{"tool_use_id": "toolu_...", "type": "tool_result", "content": "..."}]`

4. **Slash Command Expansions** (SKIP - continue walking)
   - Content: `array` with first element `type: "text"`
   - Parent: `user` (the command message)
   - Example: `[{"type": "text", "text": "# Brainstorming Ideas Into Designs\n\n..."}]`
   - Note: System-generated skill prompt expansion, not direct user input

#### Detection Logic

The correct approach checks **content structure**:

```python
def should_accept_as_trace_root(message, parent_message):
    if message['type'] != 'user':
        return False

    content = message['message']['content']

    # SKIP: Array content (tool results and command expansions)
    if isinstance(content, list):
        if content and content[0].get('type') == 'tool_result':
            return False  # Tool result

        if parent_message and parent_message.get('type') == 'user':
            return False  # Command expansion

        return False  # Unknown array type - be conservative

    # ACCEPT: All string content (prompts AND command messages)
    if isinstance(content, str):
        return True

    return False
```

#### Why Parent-Based Detection Fails

The initial implementation tried to skip user messages with assistant parents, assuming they were all tool results. This failed because:
- **Regular continuations** have assistant parents (user types more after Claude responds)
- **Slash commands** have assistant parents (system creates command message after previous response)
- Only **content structure** reliably distinguishes message types

#### Impact on Trace ID Stability

**Before fix**: Checking only parent type caused trace ID instability when:
- User types slash commands (command message incorrectly skipped)
- System compacts conversation (creates new user message chains)

**After fix**: Checking content structure provides stable trace IDs because:
- All actual user input (prompts + commands) has string content → accepted
- All system-generated messages (tool results + expansions) have array content → skipped
- Trace ID stays constant throughout the entire user turn

#### Message Flow Examples

**Slash command flow**:
```
User types: /brainstorm ...
→ 59882ffa: type=user, content=string (command tags) ← TRACE ROOT ✓
  → 43a2d09c: type=user, content=array, parent=59882ffa (expansion) ← SKIP
    → Assistant responses with tool uses...
      → d950c17a: type=user, content=array (tool result) ← SKIP
```

**Regular prompt flow**:
```
User types: plain text
→ 43bc5c08: type=user, content=string, parent=null ← TRACE ROOT ✓
  → Assistant responses with tool uses...
    → d950c17a: type=user, content=array (tool result) ← SKIP
```

#### Research Methodology

This taxonomy was discovered through:
1. Examining actual transcript data from current sessions
2. Classifying all user messages by content type and structure
3. Testing trace extraction on slash command chains
4. Cross-referencing with Claude Code documentation (found docs were outdated)
5. Validating with comprehensive test cases

Analysis documented in `/tmp/trace-analysis-2025-12-05.md`.

## Future Iterations

Potential enhancements:
- Trace visualization tools
- Performance metrics (span duration, tool call frequency)
- Trace comparison (before/after optimizations)
- Automatic trace archival/cleanup
- Integration with external observability tools
