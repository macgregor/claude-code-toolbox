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
INSTALL_PATH=$(jq -r ".plugins[\"$PLUGIN_ID\"].installPath // \"\"" "$INSTALLED_JSON" 2>/dev/null)

# Get current trace ID for this session
TRACE_ID=""
if [ -n "$SESSION_ID" ]; then
  TRACE_ID=$(cat "/tmp/claude-trace-$SESSION_ID" 2>/dev/null || echo "")
fi

# Build status line
if [ -z "$VERSION" ] || [ "$VERSION" = "unknown" ] || [ -z "$INSTALL_PATH" ]; then
  # Plugin not installed
  echo "${PLUGIN_ID}: ⚠️  Plugin not installed."
else
  if [ -n "$TRACE_ID" ]; then
    # Build extraction command with absolute path
    EXTRACT_SCRIPT="$INSTALL_PATH/scripts/debug/extract-trace.py"
    # Abbreviate home directory for display
    EXTRACT_DISPLAY="${EXTRACT_SCRIPT/#$HOME/\~}"

    # Show version + trace info
    echo "${PLUGIN_ID}: v${VERSION} (${INSTALLED_SHA:0:7}) | 🔍 Trace: [${TRACE_ID:0:8}]"
    echo "💾 $EXTRACT_DISPLAY ${TRACE_ID:0:8}"
  else
    # Just show version
    echo "${PLUGIN_ID}: v${VERSION} (${INSTALLED_SHA:0:7}) | 🐛 Debug mode active"
  fi
fi
