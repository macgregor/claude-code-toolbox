#!/bin/bash

# Parse session data from stdin
SESSION_DATA=$(cat)
CWD=$(echo "$SESSION_DATA" | jq -r '.cwd // ""')

# Get plugin metadata
PLUGIN_ID="ai-assisted-development@claude-code-toolbox"
INSTALLED_JSON="$HOME/.claude/plugins/installed_plugins.json"
VERSION=$(jq -r ".plugins[\"$PLUGIN_ID\"].version // \"unknown\"" "$INSTALLED_JSON" 2>/dev/null)
INSTALLED_SHA=$(jq -r ".plugins[\"$PLUGIN_ID\"].gitCommitSha // \"unknown\"" "$INSTALLED_JSON" 2>/dev/null)
INSTALL_PATH=$(jq -r ".plugins[\"$PLUGIN_ID\"].installPath // \"\"" "$INSTALLED_JSON" 2>/dev/null)

# Check if we're in dev mode (installed SHA != current git HEAD)
CURRENT_SHA=""
DEV_MODE=false
if [ -n "$INSTALL_PATH" ]; then
  CURRENT_SHA=$(cd "$INSTALL_PATH" && git rev-parse HEAD 2>/dev/null)
  if [ -n "$CURRENT_SHA" ] && [ "$INSTALLED_SHA" != "$CURRENT_SHA" ]; then
    DEV_MODE=true
  fi
fi

# Get current request ID
REQUEST_ID=""
REQUEST_DIR=""
if [ -n "$CWD" ] && [ -f "$CWD/.toolbox/events/.current-request-id" ]; then
  REQUEST_ID=$(cat "$CWD/.toolbox/events/.current-request-id" 2>/dev/null)
  if [ -n "$REQUEST_ID" ]; then
    REQUEST_DIR="$CWD/.toolbox/events/$REQUEST_ID"
  fi
fi

# Build status line
if [ -z "$VERSION" ] || [ "$VERSION" = "unknown" ] || [ -z "$INSTALL_PATH" ]; then
  echo "${PLUGIN_ID}: ⚠️  Plugin not installed."
else
  if [ "$DEV_MODE" = true ]; then
    echo "${PLUGIN_ID}: v${VERSION} ⚠️"
    echo "📦 Installed: ${INSTALLED_SHA:0:7} | Current: ${CURRENT_SHA:0:7}"
  else
    echo "${PLUGIN_ID}: v${VERSION}"
    echo "📦 Installed: ${INSTALLED_SHA:0:7}"
  fi

  if [ -n "$REQUEST_ID" ]; then
    # Show current request
    echo "📁 Request: ${REQUEST_ID}"
    # Abbreviate home directory for display
    REQUEST_DISPLAY="${REQUEST_DIR/#$HOME/\~}"
    echo "💾 $REQUEST_DISPLAY/"
  else
    echo "📁 No active request"
  fi
fi
