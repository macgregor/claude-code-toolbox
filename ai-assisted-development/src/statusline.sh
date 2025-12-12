#!/bin/bash

# Parse session data from stdin
SESSION_DATA=$(cat)
CWD=$(echo "$SESSION_DATA" | jq -r '.cwd // ""')
SESSION_ID=$(echo "$SESSION_DATA" | jq -r '.session_id // ""')

# Get plugin metadata
PLUGIN_ID="ai-assisted-development@claude-code-toolbox"
INSTALLED_JSON="$HOME/.claude/plugins/installed_plugins.json"
MARKETPLACES_JSON="$HOME/.claude/plugins/known_marketplaces.json"

# Try installed plugin first
VERSION=$(jq -r ".plugins[\"$PLUGIN_ID\"].version // \"unknown\"" "$INSTALLED_JSON" 2>/dev/null)
INSTALLED_SHA=$(jq -r ".plugins[\"$PLUGIN_ID\"].gitCommitSha // \"unknown\"" "$INSTALLED_JSON" 2>/dev/null)
INSTALL_PATH=$(jq -r ".plugins[\"$PLUGIN_ID\"].installPath // \"\"" "$INSTALLED_JSON" 2>/dev/null)

# Fallback to development mode (local marketplace)
if [ -z "$INSTALL_PATH" ] || [ "$INSTALL_PATH" = "null" ]; then
  MARKETPLACE_ROOT=$(jq -r '."claude-code-toolbox".installLocation // ""' "$MARKETPLACES_JSON" 2>/dev/null)
  if [ -n "$MARKETPLACE_ROOT" ]; then
    # In dev mode, plugin is under ai-assisted-development/ subdirectory
    INSTALL_PATH="$MARKETPLACE_ROOT/ai-assisted-development"
    if [ -f "$INSTALL_PATH/.claude-plugin/plugin.json" ]; then
      VERSION=$(jq -r '.version // "dev"' "$INSTALL_PATH/.claude-plugin/plugin.json" 2>/dev/null)
      INSTALLED_SHA="dev"
    fi
  fi
fi

# Check if we're in dev mode (installed SHA != current git HEAD)
CURRENT_SHA=""
DEV_MODE=false
if [ -n "$INSTALL_PATH" ]; then
  CURRENT_SHA=$(cd "$INSTALL_PATH" && git rev-parse HEAD 2>/dev/null)
  if [ -n "$CURRENT_SHA" ] && [ "$INSTALLED_SHA" != "$CURRENT_SHA" ]; then
    DEV_MODE=true
  fi
fi

# Get current request ID from global state
REQUEST_ID=""
REQUEST_DIR=""
if [ -n "$CWD" ] && [ -n "$SESSION_ID" ] && [ -f "$CWD/.toolbox/events/.global-state.json" ]; then
  REQUEST_ID=$(jq -r ".session_requests[\"$SESSION_ID\"] // \"\"" "$CWD/.toolbox/events/.global-state.json" 2>/dev/null)
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
