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
    "command": "ai-assisted-development/scripts/debug/statusline.sh"
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

## Architecture

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and lifecycle tracking
- [docs/claude-code-reference.md](docs/claude-code-reference.md) - Platform features and constraints

## Plugin Structure

```
ai-assisted-development/
├── .claude-plugin/
│   └── plugin.json          # Manifest
├── agents/                  # Subagent definitions
├── scripts/                 # Hook handlers
│   └── agent-lifecycle.py   # Core lifecycle tracking
└── hooks.json              # Hook configuration
```

Changes to hooks or scripts require plugin reinstall (`make install-plugin`).

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
