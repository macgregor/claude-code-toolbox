# Claude Code Toolbox

Infrastructure for agent coordination. Track agent execution, persist context across sessions, and build multi-agent workflows.

## What This Does

The `ai-assisted-development` plugin observes agent execution via hooks and stores:
- User prompts and agent outputs
- Agent-created artifacts
- Session logs pruned to request boundaries
- Complete audit trail

Agents coordinate without coupling. They output tags; the system extracts them. No special tools required.

See [ARCHITECTURE.md](ARCHITECTURE.md) for design details.

## Quick Start

### Install

```bash
git clone https://github.com/macgregor/claude-code-toolbox.git
cd claude-code-toolbox
make install-plugin
```

### Use on Your Projects

Navigate to any repository and use Claude Code normally. The plugin tracks execution automatically:

```bash
cd ~/your-project
claude
```

Check `.toolbox/events/` for captured context and artifacts.

### Debug Mode

Enable statusline with plugin version, trace ID, and log extraction command:

```json
// .claude/settings.json or .claude/settings.local.json
{
  "statusLine": {
    "type": "command",
    "command": "ai-assisted-development/scripts/debug/statusline.sh"
  }
}
```

See [Plugin Debug System](docs/plugin-debug-system.md).

### Isolated Development (Optional)

Run Claude Code in a container for filesystem isolation:

```bash
# One-time setup
ln -s $(pwd)/devcontainer/scripts/claude-isolated ~/.local/bin/claude-isolated

# Use
claude-isolated /path/to/project
```

See [docs/devcontainer.md](docs/devcontainer.md) for VS Code integration.

## Documentation

**Using:**
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and lifecycle tracking
- [docs/devcontainer.md](docs/devcontainer.md) - Isolated development environment

**Building:**
- [CONTRIBUTING.md](CONTRIBUTING.md) - Local development setup and testing
- [docs/claude-code-reference.md](docs/claude-code-reference.md) - Platform features and constraints

**Learning:**
- [docs/ai-learning-material.md](docs/ai-learning-material.md) - AI development resources
