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

### Isolated Development

Use the devcontainer for filesystem isolation:

```bash
# CLI (one-time setup)
ln -s $(pwd)/devcontainer/scripts/claude-isolated ~/.local/bin/claude-isolated
ln -s $(pwd)/devcontainer/scripts/claude-isolated-shell ~/.local/bin/claude-isolated-shell

# Run isolated Claude Code
claude-isolated /path/to/project

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
