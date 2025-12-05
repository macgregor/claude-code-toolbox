#!/bin/bash

if [ -z "$CLAUDE_TOOLBOX_DEBUG" ]; then
  exit 0
fi

HOOK_DATA=$(cat)
SESSION_ID=$(echo "$HOOK_DATA" | jq -r '.session_id')
TRANSCRIPT=$(echo "$HOOK_DATA" | jq -r '.transcript_path')
TOOL_USE_ID=$(echo "$HOOK_DATA" | jq -r '.tool_use_id')

# Extract trace_id for this request
TRACE_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/debug/extract-trace-id.sh" <<< "$HOOK_DATA")

# Debug logging
echo "$(date '+%H:%M:%S') tool:${TOOL_USE_ID:0:12} -> trace:${TRACE_ID:0:8}" >> /tmp/trace-debug.log

if [ "$TRACE_ID" = "unknown" ]; then
  exit 0
fi

# Check if we already have a trace for this session
EXISTING_TRACE=""
if [ -f "/tmp/claude-trace-$SESSION_ID" ]; then
  EXISTING_TRACE=$(cat "/tmp/claude-trace-$SESSION_ID")
fi

# Only update if this is a new trace (new user message/turn)
if [ "$EXISTING_TRACE" != "$TRACE_ID" ]; then
  echo "$(date '+%H:%M:%S') UPDATE: ${EXISTING_TRACE:0:8} -> ${TRACE_ID:0:8}" >> /tmp/trace-debug.log

  # Store trace ID for statusline (session-based)
  echo "$TRACE_ID" > "/tmp/claude-trace-$SESSION_ID"

  # Store transcript path for extraction (trace-based)
  echo "$TRANSCRIPT" > "/tmp/claude-trace-info-${TRACE_ID:0:8}"
fi

exit 0
