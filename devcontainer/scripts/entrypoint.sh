#!/bin/bash
set -e

# Ensure Claude Code is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Files/dirs to symlink from localhost ~/.claude
# Supports globs (e.g., "agents/*.md")
LINKS=(
  "CLAUDE.md"
  "skills"
  "agents"
  "commands"
  "hooks"
)

# Marketplaces to install (git URL or owner/repo)
# Example: "anthropics/claude-code"
MARKETPLACES=()

# Plugins to install (name or name@marketplace)
# Example: "pr-review-toolkit@claude-code-plugins"
PLUGINS=()

# Link localhost config files to ~/.claude
mkdir -p ~/.claude

for pattern in "${LINKS[@]}"; do
  for item in /mnt/localhost-claude/$pattern; do
    [ -e "$item" ] || continue
    rel_path="${item#/mnt/localhost-claude/}"
    mkdir -p "$(dirname ~/.claude/$rel_path)"
    ln -sfn "$item" ~/.claude/$rel_path
  done
done

# Install/update marketplaces
for marketplace in "${MARKETPLACES[@]}"; do
  output=$(claude plugin marketplace add "$marketplace" 2>&1) || {
    # Extract marketplace name from error: "Marketplace 'name' is already installed"
    if [[ "$output" =~ Marketplace\ \'([^\']+)\'\ is\ already\ installed ]]; then
      name="${BASH_REMATCH[1]}"
      claude plugin marketplace update "$name" || true
    fi
  }
done

# Install plugins (idempotent)
for plugin in "${PLUGINS[@]}"; do
  claude plugin install "$plugin"
done

# Execute command passed to container
exec "$@"
