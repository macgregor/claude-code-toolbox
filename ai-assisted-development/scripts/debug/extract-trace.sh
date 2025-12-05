#!/bin/bash
# Extract all messages in a trace from Claude Code transcript.
# A trace is all messages between a user prompt and the next user prompt (or EOF).

TRACE_PREFIX="${1:-}"
WATCH_MODE="${2:-}"

if [ -z "$TRACE_PREFIX" ]; then
  echo "Usage: $0 <trace_id_prefix> [-w|--watch]" >&2
  exit 1
fi

# Find most recent transcript
PROJECT_DIR="$HOME/.claude/projects/-workspace"
TRANSCRIPT=$(ls -t "$PROJECT_DIR"/*.jsonl 2>/dev/null | head -1)

if [ -z "$TRANSCRIPT" ]; then
  echo "Error: No transcript found" >&2
  exit 1
fi

# Find start boundary: line number of trace ID
START_LINE=$(grep -n "\"uuid\":\"$TRACE_PREFIX" "$TRANSCRIPT" | head -1 | cut -d: -f1)

if [ -z "$START_LINE" ]; then
  echo "Error: No message found with trace ID starting with $TRACE_PREFIX" >&2
  exit 1
fi

# Find end boundary: next user prompt after start (or EOF)
END_LINE=$(tail -n +$((START_LINE + 1)) "$TRANSCRIPT" | \
  grep -n '"type":"user"' | \
  while IFS=: read -r linenum line; do
    if echo "$line" | jq -e 'select((.message.content | type) == "string")' >/dev/null 2>&1; then
      echo $((START_LINE + linenum))
      break
    fi
  done)

# Extract the range
if [ "$WATCH_MODE" = "-w" ] || [ "$WATCH_MODE" = "--watch" ]; then
  # Watch mode: output current trace then follow new lines until next user prompt
  if [ -n "$END_LINE" ]; then
    sed -n "${START_LINE},${END_LINE}p" "$TRANSCRIPT"
  else
    tail -n +$START_LINE "$TRANSCRIPT"
  fi

  # Continue streaming and stop at next user prompt
  tail -n 0 -f "$TRANSCRIPT" | while IFS= read -r line; do
    if echo "$line" | jq -e 'select(.type == "user" and (.message.content | type) == "string")' >/dev/null 2>&1; then
      break
    fi
    echo "$line"
  done
else
  # Regular mode: extract the range
  if [ -n "$END_LINE" ]; then
    sed -n "${START_LINE},$((END_LINE - 1))p" "$TRANSCRIPT"
  else
    tail -n +$START_LINE "$TRANSCRIPT"
  fi
fi
