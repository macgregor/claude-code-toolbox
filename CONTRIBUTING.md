---
name: contributing
description: >
  Use when setting up local development, running tests, building the plugin, or
  understanding development workflow. Covers installation, testing, and common gotchas.
categories: [workflow, development]
tags: [setup, testing, building, devcontainer]
related_docs:
  - ARCHITECTURE.md
  - docs/devcontainer.md
  - docs/claude-code-reference.md
complexity: basic
---

# Contributing

Get the repository working locally.

## Quick Start

```bash
# Clone and install
git clone https://github.com/macgregor/claude-code-toolbox.git
cd claude-code-toolbox
make install-plugin

# Verify
claude plugin list | grep ai-assisted-development
```

## Plugin Structure

```
.claude-plugin/
└── plugin.json              # Marketplace Manifest
ai-assisted-development/
├── .claude-plugin/
│   └── plugin.json          # Plugin Manifest
├── agents/                  # Subagent definitions
├── hooks/
│   └── hooks.json           # Hook configuration
├── src/                     # Source code used by hooks and agents
└── tests/                   # Unit tests
```

**What changes require reinstall:**
- Adding/removing agents, commands, or skills (requires reinstall + Claude restart for discovery)
- Modifying agent/command prompts (may require Claude restart due to caching)
- Changing `plugin.json` metadata

**What changes are "hot-swappable" (dangerous):**
- Hook handler scripts (`src/*.py`, `src/*.sh`) - changes apply immediately on next hook execution
- Hook configuration (`hooks/hooks.json`) - changes apply immediately on plugin reinstall

Hot-swappable changes are dangerous because they take effect without a restart, potentially breaking your active session.

## Development Workflow

### Build and Install

```bash
# Validate plugin manifests
make validate-plugin

# Install from local source (reinstalls if exists)
make install-plugin
```

The install target adds the repository as a local marketplace, removes any existing installation, and installs the plugin fresh.

### Testing

```bash
# Run all tests
make test

# Run lifecycle tests only
make test-lifecycle
```

Tests use Python unittest. See `ai-assisted-development/tests/` for test files.

### Debug Status Line

Enable statusline hook that sows plugin version, installed vs current git SHA, request ID, and request directory. Warning appears when local commits exist that aren't installed.

```json
// .claude/settings.json or .claude/settings.local.json
{
  "statusLine": {
    "type": "command",
    "command": "python ${CLAUDE_PLUGIN_ROOT}/src/agent-lifecycle.py"
  }
}
```

Example output (synced):
```
ai-assisted-development@claude-code-toolbox: v0.1.0
📦 Installed: a1b2c3d
📁 Request: 2025-12-11T00-15-32_e36738f5
💾 ~/.toolbox/events/2025-12-11T00-15-32_e36738f5/
```

Example output (out of sync):
```
ai-assisted-development@claude-code-toolbox: v0.1.0 ⚠️
📦 Installed: a1b2c3d | Current: f8e6b21
📁 Request: 2025-12-11T00-15-32_e36738f5
💾 ~/.toolbox/events/2025-12-11T00-15-32_e36738f5/
```

### Isolated Development

Use the devcontainer for filesystem isolation:

```bash
# CLI (one-time setup)
ln -s $(pwd)/devcontainer/scripts/claude-isolated ~/.local/bin/claude-isolated
ln -s $(pwd)/devcontainer/scripts/claude-isolated-shell ~/.local/bin/claude-isolated-shell

# Run isolated Claude Code
claude-isolated /path/to/project

# Connext a second terminal
claude-isolated-shell /path/to/project

# Rebuild container after changes
claude-isolated --rebuild /path/to/project
```

See [docs/devcontainer.md](docs/devcontainer.md) for VS Code setup and internals.

## Safely Updating Hook Handlers

**When to use this procedure:**
- Modifying any file in `src/` that hooks execute
- Changing `hooks/hooks.json` or `.claude/settings.json` hook configuration
- Moving/renaming files referenced by hooks

**Why this is dangerous:**
Hook changes are hot-swappable - they take effect on next execution without restart. Breaking a hook script (wrong paths, errors, blocking behavior, non-0 exit codes) has the potential to completely break Claude Code.

**Safe procedure:**

1. Disable hooks in `hooks.json`. 
    - If you arent sure which specific hooks to disable, replace entire contents with: `{"hooks": {}}`
    - This ensures broken hooks can't execute
2. Make code changes:
    - Make absolutely sure the changes are functional, tests are passing
    - triple check paths that go in `hooks.json` are correct for when installed as a plugin
    - missing paths, script errors and non-0 error codes have the potential to completely break claude code
3. Re-enable hooks.
    - be 100% sure everything is correct before you re-enable any hooks 

**Recovery if hooks break:**
- You cannot fix from within Claude Code
- Exit immediately (`/exit`)
- Restore `hooks/hooks.json` to `{"hooks": {}}` in separate terminal
- Reinstall plugin
- Fix the broken script
- Repeat safe procedure

## Development Gotchas

### Claude File Locations

**Plugin files** (in repository):
- `ai-assisted-development/agents/foo.md` - Installed to `~/.claude/plugins/.../agents/foo.md`
- Used by end users when plugin is installed

**Project files** (in repository):
- `.claude/agents/bar.md` - Local to this repository
- Only available when developing this specific project

When building the plugin, reason about paths as they'll exist on end users' systems, not your development environment.

### Path Confusion

Three path contexts exist:

1. **Devcontainer paths**: `/workspace`, `/home/claude-user/.claude`
2. **Localhost paths**: Your actual filesystem during local development
3. **End user paths**: Where the plugin runs when installed

Scripts and hooks must use paths that work for end users. Test in the devcontainer to catch localhost-specific assumptions.

**Rule of thumb**: All paths should work as if running on an end user's system with the plugin installed via marketplace.
