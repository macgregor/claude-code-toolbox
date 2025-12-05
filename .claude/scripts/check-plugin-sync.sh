#!/bin/bash
# Development-only: Check if installed plugin is out of sync with workspace

PLUGIN_ID="ai-assisted-development@claude-code-toolbox"
INSTALLED_JSON="$HOME/.claude/plugins/installed_plugins.json"

# Read hook data from stdin
HOOK_DATA=$(cat)

# Only check once per session
SESSION_ID=$(echo "$HOOK_DATA" | jq -r '.session_id' 2>/dev/null)
if [ -n "$SESSION_ID" ] && [ -f "/tmp/plugin-sync-checked-$SESSION_ID" ]; then
  exit 0
fi

# Get installed SHA (check both file existence and plugin entry)
INSTALLED_SHA=""
if [ -f "$INSTALLED_JSON" ]; then
  INSTALLED_SHA=$(jq -r ".plugins[\"$PLUGIN_ID\"].gitCommitSha" "$INSTALLED_JSON" 2>/dev/null)
fi

if [ -z "$INSTALLED_SHA" ] || [ "$INSTALLED_SHA" = "null" ]; then
  cat <<EOF
{
  "continue": true,
  "systemMessage": "⚠️  Plugin not installed. Run 'make install-plugin' from the repo directory to install."
}
EOF
  exit 0
fi

# Get workspace HEAD (pwd should be project root when hook runs)
WORKSPACE_SHA=$(git rev-parse HEAD 2>/dev/null)
if [ -z "$WORKSPACE_SHA" ]; then
  exit 0
fi

# Mark as checked
if [ -n "$SESSION_ID" ]; then
  touch "/tmp/plugin-sync-checked-$SESSION_ID"
fi

# Compare
if [ "${INSTALLED_SHA:0:7}" != "${WORKSPACE_SHA:0:7}" ]; then
  cat <<EOF
{
  "continue": true,
  "systemMessage": "⚠️  Plugin out of sync: installed=${INSTALLED_SHA:0:7}, workspace=${WORKSPACE_SHA:0:7}. Run 'make install-plugin' from the repo directory to sync."
}
EOF
fi

exit 0
