# Trace System Simplification

## Problem

The trace system had unnecessary complexity:
- PreToolUse hooks that wrote to `/tmp` files
- Python script with graph traversal logic
- Complex parent-chain walking scripts
- Filesystem state to pass data between hooks

This violated Unix philosophy: use standard tools, read from source, avoid state files.

## Solution

Simplified to two bash scripts with zero filesystem state:

1. **statusline.sh** (46 lines) - Reads trace ID directly from transcript
2. **extract-trace.sh** (63 lines) - Uses grep/sed/tail to stream traces

## Design

### Statusline

Reads the most recent user prompt UUID directly from the transcript:

```bash
grep '"type":"user"' "$TRANSCRIPT" | tail -100 | \
  jq -r 'select((.message.content | type) == "string") | .uuid' | \
  tail -1
```

User prompts have string content. Tool results and command expansions have array content. This distinction identifies the trace root.

No hooks. No /tmp files. Just read from the source.

### Trace Extraction

Finds two boundaries:
1. Start: Line containing the trace ID
2. End: Next user prompt with string content (or EOF)

Extracts everything between:

```bash
# Find start line
START_LINE=$(grep -n "\"uuid\":\"$TRACE_PREFIX" "$TRANSCRIPT" | head -1 | cut -d: -f1)

# Find end line (next user prompt)
END_LINE=$(tail -n +$((START_LINE + 1)) "$TRANSCRIPT" | \
  grep -n '"type":"user"' | \
  while IFS=: read -r linenum line; do
    if echo "$line" | jq -e 'select((.message.content | type) == "string")' >/dev/null 2>&1; then
      echo $((START_LINE + linenum))
      break
    fi
  done)

# Extract range
sed -n "${START_LINE},$((END_LINE - 1))p" "$TRANSCRIPT"
```

Watch mode uses `tail -f` for streaming. The script outputs line-delimited JSON that composes with standard tools.

## What We Removed

**Deleted files:**
- `pre-tool-use-trace.sh` - PreToolUse hook (68 lines)
- `extract-trace-id.sh` - Parent chain walker (66 lines)
- `user-prompt-submit.sh` - Failed attempt at hook communication
- `/tmp/claude-trace-*` files - Session state

**Total reduction:** 134 lines of complex logic eliminated.

## Key Insight

Hooks cannot pass data to other components. The StatusLine hook documentation showed no mechanism for reading hook output. UserPromptSubmit hooks can add context to conversations, not to other hooks.

The solution: read directly from the source. Claude Code logs everything to transcripts. Use that instead of creating parallel state.

## Architecture

**Read from source:** Transcript files are the single source of truth.

**Use standard tools:** grep, sed, tail, jq instead of custom file watching.

**Simple boundaries:** A turn is everything between two user prompts. No graph traversal needed.

**Composable:** Outputs line-delimited JSON. Pipe through any tool.

## Usage

```bash
# Extract a trace
extract-trace.sh a019980f

# Stream new messages
extract-trace.sh a019980f -w

# Filter assistant messages
extract-trace.sh a019980f | jq 'select(.type == "assistant")'

# Count tool uses
extract-trace.sh a019980f | jq 'select(.message.content[]?.type == "tool_use")' | wc -l
```

## Implementation

**Files:**
- `ai-assisted-development/scripts/debug/statusline.sh` (46 lines)
- `ai-assisted-development/scripts/debug/extract-trace.sh` (63 lines)

**Dependencies:** bash, grep, sed, tail, jq (all standard)

**State:** None

## Lesson Learned

Question complexity. When you build something complex, verify that complexity is necessary. We assumed we needed hooks, state files, and graph traversal. The actual requirement was much simpler: read the last user message and extract a range of lines.

Always start with the simplest solution. Add complexity only when proven necessary.
