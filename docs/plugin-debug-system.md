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
ai-assisted-development@claude-code-toolbox: v1.0.0 (7fe1652) | 🔍 Trace: [a019980f]
💾 ~/.claude/plugins/claude-code-toolbox/scripts/debug/extract-trace.sh a019980f
```

Copy and run the extraction command to see the full conversation turn.

## How It Works

### Statusline

`statusline.sh` receives session data on stdin from Claude Code. It reads plugin metadata from `~/.claude/plugins/installed_plugins.json` and finds the current trace ID by reading the transcript directly.

The trace ID is the UUID of the most recent user prompt (messages with string content, not tool results).

**Implementation**: `ai-assisted-development/scripts/debug/statusline.sh` (46 lines)

### Trace Extraction

`extract-trace.sh` extracts all messages in a conversation turn. A turn starts at a user prompt and ends at the next user prompt or end of file.

```bash
# Extract current turn
extract-trace.sh a019980f

# Stream new messages in real-time
extract-trace.sh a019980f -w

# Filter with jq
extract-trace.sh a019980f | jq 'select(.type == "assistant")'
```

The script:
1. Finds the most recent transcript in `~/.claude/projects/-workspace/`
2. Uses `grep -n` to find the start line (trace ID match)
3. Searches forward for the next user prompt (end boundary)
4. Extracts the range with `sed` or streams with `tail -f`

**Implementation**: `ai-assisted-development/scripts/debug/extract-trace.sh` (63 lines)

### Architecture

**Zero filesystem state**: The statusline reads directly from the transcript. No hooks write state to `/tmp`. No communication between components.

**Pure streaming**: Uses standard Unix tools (`grep`, `sed`, `tail`, `jq`) instead of custom file watching or tree traversal.

**Composable**: Output is line-delimited JSON. Pipe through `jq`, `grep`, `tail`, or any standard tool.

## Disabling Debug Mode

Remove the environment variable:

```json
{
  "env": {
    "CLAUDE_TOOLBOX_DEBUG": "0"
  }
}
```

## Troubleshooting

**Statusline shows "Debug mode active"**: The transcript has no user prompts with string content yet. Send a message and the trace ID will appear.

**Trace ID not updating**: Expected. The trace ID stays the same throughout your conversation turn. It changes only when you submit a new prompt.

**Extraction returns nothing**: Check that the trace ID exists in the transcript. Try the full UUID instead of the prefix.

**Wrong transcript**: The script finds the most recent `.jsonl` file. If multiple sessions are active, specify the transcript path manually.

## Implementation Files

```
ai-assisted-development/scripts/debug/
  statusline.sh              # Display plugin version and trace ID
  extract-trace.sh           # Extract conversation turn (bash + streaming)
```

## Design Rationale

**Read from source**: Claude Code logs everything to transcript files. Read directly from the source instead of duplicating data.

**Let Linux do the work**: Use `grep`, `sed`, and `tail -f` instead of custom file watching. These tools are fast, reliable, and composable.

**Simple boundaries**: A turn is everything between two user prompts. Find the boundaries and extract the range. No graph traversal needed.
