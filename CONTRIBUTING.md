---
name: contributing
description: >
  Use when setting up local development, running tests, building the plugin, or
  understanding development workflow. Covers installation, testing, and common gotchas.
categories: [workflow, development]
tags: [setup, testing, building, devcontainer]
related_docs:
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
└── marketplace.json         # Marketplace Manifest
ai-assisted-development/
├── .claude-plugin/
│   └── plugin.json          # Plugin Manifest
├── agents/                  # Subagent definitions
├── commands/                # Slash commands
├── hooks/
│   └── hooks.json           # Hook configuration (currently empty)
├── scripts/                 # Validation scripts for agent output
├── src/
│   └── statusline.py        # Statusline display script
├── templates/               # Report templates for agents
└── tests/                   # Unit tests
```

**What changes require reinstall:**
- Adding/removing agents, commands, or skills (requires reinstall + Claude restart for discovery)
- Modifying agent/command prompts (may require Claude restart due to caching)
- Changing `plugin.json` metadata

**What changes are "hot-swappable":**
- The statusline script (`src/statusline.py`) - changes apply immediately
- Validation scripts (`scripts/*.sh`) - changes apply immediately

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
```

Tests use Python unittest. See `ai-assisted-development/tests/` for test files.

### Debug Status Line

Shows plugin version and installed git SHA. Warning appears when local commits exist that aren't installed (dev mode only).

```json
// .claude/settings.json or .claude/settings.local.json
{
  "statusLine": {
    "type": "command",
    "command": "ai-assisted-development/src/statusline.py"
  }
}
```

Example output (synced):
```
ai-assisted-development@claude-code-toolbox: v1.0.0
📦 Installed: a1b2c3d
```

Example output (out of sync):
```
ai-assisted-development@claude-code-toolbox: v1.0.0 ⚠️
📦 Installed: a1b2c3d | Current: f8e6b21
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

## Hooks

No hooks are currently active (`hooks.json` is empty). If hooks are added in the future, note that hook changes are hot-swappable and take effect without restart. Breaking a hook script can completely break Claude Code. Test thoroughly before enabling.

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
