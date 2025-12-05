# Plugin Debugging & Versioning System

## Overview

Tools for debugging and versioning the ai-assisted-development plugin during development and use. Addresses two key problems:
1. Knowing exactly what version of the plugin is installed
2. Debugging agent/subagent behavior through trace logging

## Scope

### In Scope
- `/ai-assisted-development:version` command showing installed plugin metadata
- Trace logging system that extracts request flow from Claude Code's session logs
- Debug mode controlled by environment variable
- Development-only hook to detect plugin version mismatches

### Out of Scope
- Log analysis/visualization tools (future iteration)
- Automatic plugin updates
- Performance profiling

## Design

### 1. Version Command

**Location**: `ai-assisted-development/commands/version.md`
**Script**: `ai-assisted-development/scripts/version.sh`

The command calls a bash script (no AI reasoning) that:
- Reads `~/.claude/plugins/installed_plugins.json` to get:
  - Plugin version (semver)
  - Git commit SHA (critical for development)
  - Install/update timestamps
  - Install path
- Runs git commands in `$CLAUDE_PLUGIN_ROOT` to show:
  - Current HEAD SHA
  - Whether working directory is dirty
  - Commit date and message

**Output format**:
```
ai-assisted-development@claude-code-toolbox
Version: 1.0.0
Installed: 2025-12-05T02:25:29Z
Git SHA: 4fbbf0bd (installed)
Current: bba6f70 (2025-12-05, "generated a project CLAUDE.md")
Status: Out of sync - installed from older commit
```

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
5. Stores trace_id in `/tmp/claude-trace-{session_id}`

**Stop Hook** (when Claude returns control):
1. Checks if `CLAUDE_TOOLBOX_DEBUG` env var is set
2. If not set: exit silently
3. If set:
   - Reads trace_id from temp file
   - Generates jq command to extract that trace from the transcript
   - Returns JSON with `systemMessage` showing the command
   - Cleans up temp file

**Hook JSON Output**:
```json
{
  "continue": true,
  "systemMessage": "[Trace c61df7c2] Extract: jq 'select(.uuid == \"c61df7c2...\" or (.parentUuid // \"\" | contains(\"c61df7c2...\")))' ~/.claude/projects/-workspace/{session_id}.jsonl"
}
```

The `systemMessage` field displays the extraction command directly to the user.

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
  commands/
    version.md                       # Slash command wrapper
  scripts/
    version.sh                       # Version info script
    extract-trace-id.sh              # Extract trace_id from tool_use_id
    pre-tool-use-trace.sh            # PreToolUse hook for trace capture
    stop-trace.sh                    # Stop hook for trace display
  hooks/
    hooks.json                       # Hook configuration

.claude/                             # Development-only (this repo)
  settings.local.json                # Contains dev sync check hook
```

## Implementation Details

### Version Script (`version.sh`)

```bash
#!/bin/bash

PLUGIN_ID="ai-assisted-development@claude-code-toolbox"
INSTALLED_JSON="$HOME/.claude/plugins/installed_plugins.json"

# Extract metadata from installed_plugins.json
VERSION=$(jq -r ".plugins[\"$PLUGIN_ID\"].version" "$INSTALLED_JSON")
INSTALLED_SHA=$(jq -r ".plugins[\"$PLUGIN_ID\"].gitCommitSha" "$INSTALLED_JSON")
INSTALLED_AT=$(jq -r ".plugins[\"$PLUGIN_ID\"].installedAt" "$INSTALLED_JSON")

# Get current state from plugin directory
cd "$CLAUDE_PLUGIN_ROOT"
CURRENT_SHA=$(git rev-parse HEAD 2>/dev/null | cut -c1-7)
COMMIT_MSG=$(git log -1 --format="%s" 2>/dev/null)
COMMIT_DATE=$(git log -1 --format="%ai" 2>/dev/null)

echo "$PLUGIN_ID"
echo "Version: $VERSION"
echo "Installed: $INSTALLED_AT"
echo "Git SHA: ${INSTALLED_SHA:0:7} (installed)"
echo "Current: $CURRENT_SHA ($COMMIT_DATE, \"$COMMIT_MSG\")"

if [ "${INSTALLED_SHA:0:7}" != "$CURRENT_SHA" ]; then
  echo "Status: Out of sync - installed from different commit"
else
  echo "Status: In sync"
fi
```

### Trace Extraction Script (`extract-trace-id.sh`)

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
CURRENT_UUID="$MESSAGE_UUID"
while [ -n "$CURRENT_UUID" ]; do
  MESSAGE=$(grep "\"uuid\":\"$CURRENT_UUID\"" "$TRANSCRIPT" | head -1)
  TYPE=$(echo "$MESSAGE" | jq -r '.type')

  if [ "$TYPE" = "user" ]; then
    echo "$CURRENT_UUID"
    exit 0
  fi

  CURRENT_UUID=$(echo "$MESSAGE" | jq -r '.parentUuid')
  if [ "$CURRENT_UUID" = "null" ]; then
    CURRENT_UUID=""
  fi
done

echo "unknown"
```

### PreToolUse Hook (`pre-tool-use-trace.sh`)

```bash
#!/bin/bash

if [ -z "$CLAUDE_TOOLBOX_DEBUG" ]; then
  exit 0
fi

HOOK_DATA=$(cat)
SESSION_ID=$(echo "$HOOK_DATA" | jq -r '.session_id')

# Check if trace already started for this session
if [ -f "/tmp/claude-trace-$SESSION_ID" ]; then
  exit 0
fi

# Extract trace_id for this request
TRACE_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/extract-trace-id.sh" <<< "$HOOK_DATA")

if [ "$TRACE_ID" != "unknown" ]; then
  echo "$TRACE_ID" > "/tmp/claude-trace-$SESSION_ID"
fi

exit 0
```

### Stop Hook (`stop-trace.sh`)

```bash
#!/bin/bash

if [ -z "$CLAUDE_TOOLBOX_DEBUG" ]; then
  exit 0
fi

HOOK_DATA=$(cat)
SESSION_ID=$(echo "$HOOK_DATA" | jq -r '.session_id')
TRANSCRIPT=$(echo "$HOOK_DATA" | jq -r '.transcript_path')

TRACE_ID=$(cat "/tmp/claude-trace-$SESSION_ID" 2>/dev/null)

if [ -z "$TRACE_ID" ]; then
  exit 0
fi

# Generate jq command to extract this trace
JQ_CMD="jq 'select(.uuid == \"$TRACE_ID\" or (.parentUuid // \"\" | contains(\"$TRACE_ID\")))' $TRANSCRIPT"

# Clean up
rm -f "/tmp/claude-trace-$SESSION_ID"

# Return JSON with systemMessage
cat <<EOF
{
  "continue": true,
  "systemMessage": "[Trace ${TRACE_ID:0:8}] Extract: $JQ_CMD"
}
EOF
```

### Hook Configuration (`hooks/hooks.json`)

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/scripts/pre-tool-use-trace.sh"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/scripts/stop-trace.sh"
      }]
    }]
  }
}
```

## Usage

### Checking Plugin Version

```
/ai-assisted-development:version
```

Shows installed version, git SHA, and sync status.

### Enabling Trace Logging

Add to `.claude/settings.local.json`:
```json
{
  "env": {
    "CLAUDE_TOOLBOX_DEBUG": "1"
  }
}
```

Or export before launching Claude Code:
```bash
export CLAUDE_TOOLBOX_DEBUG=1
claude
```

When enabled, the Stop hook will display a command to extract the trace after each request completes.

### Extracting a Trace

Run the jq command shown by the Stop hook:
```bash
jq 'select(.uuid == "c61df7c2..." or (.parentUuid // "" | contains("c61df7c2...")))' ~/.claude/projects/-workspace/{session_id}.jsonl
```

This shows all messages and tool uses for that specific user request.

## Design Rationale

### Why Not Duplicate Logs?

Claude Code already logs everything to session transcripts. Duplicating that data would:
- Waste disk space
- Create sync issues (what if logs diverge?)
- Add complexity for no benefit

Instead, we provide the trace boundary and let users extract from the existing logs when needed.

### Why systemMessage?

The Stop hook's `systemMessage` JSON field displays directly to the user without getting lost in tool output. If this doesn't work well in practice, we can pivot to writing `.claude/last-trace.txt` as a backup.

### Why Environment Variable for Debug Mode?

Simple, standard, flexible. Users can set it however they want - project settings, shell export, command-line. We don't need to reinvent configuration systems.

### Why Project-Specific Trace Files?

Traces are debugging artifacts related to specific project work. Keeping them with the project (`.claude/logs/traces/`) makes them easy to find, share, and clean up. Global logs would mix traces from different projects.

## Future Iterations

Potential enhancements:
- Trace visualization tools
- Performance metrics (span duration, tool call frequency)
- Trace comparison (before/after optimizations)
- Automatic trace archival/cleanup
- Integration with external observability tools
