# Claude Code Toolbox

A local marketplace of Claude Code plugins for productive development workflows.

For learning resources see [AI Learning Materials](./docs/ai-learning-material.md)

## Overview

This marketplace currently includes:

### ai-assisted-development plugin

- **Agents**: Web research agent for gathering technical information
- **Skills**: Workflow skills for web research and technical investigations
- **Commands**: Slash commands for research workflows
- **Hooks**: Automated tasks like episodic memory sync and Chrome debugging setup

## Installation

### Clone the Repository

```bash
git clone https://github.com/macgregor/claude-code-toolbox.git
cd claude-code-toolbox
```

### Install via Local Marketplace

Start a Claude Code session and run:

```
/plugin marketplace add /path/to/claude-code-toolbox
/plugin install ai-assisted-development@claude-code-toolbox
```

This approach allows you to iterate on plugin changes easily during development.

### Optional: Symlink CLAUDE.md

The `CLAUDE.md` file contains personal workflow preferences and context. You can symlink it to use it globally:

```bash
ln -s $(pwd)/CLAUDE.md ~/.claude/CLAUDE.md
```

Note: This overwrites any existing `~/.claude/CLAUDE.md`. Back up your current file first if needed.

## Usage

### Reloading After Changes

When you modify agents, skills, commands, hooks, or plugin.json:

```
/plugin uninstall ai-assisted-development@claude-code-toolbox
/plugin install ai-assisted-development@claude-code-toolbox
```

Changes take effect immediately without restarting Claude Code.

### (optional) Isolated Development Container

Run Claude Code in an isolated container to limit blast radius when working on projects:

```bash
claude-isolated /path/to/repo

# youre now inside the devcontainer
# use claude code as usual
[claude-user@fedora workspace]$ claude

# or the convenience alias to run claude without permisison checks
[claude-user@fedora workspace]$ claude-dangerous
```

If claude-code-toolbox is installed on your local file system, it will be available to claude in the devcontainer.

See [devcontainer documentation](./docs/devcontainer.md) for setup and usage details, including how to integrate with vscode.

## Development & Customization

### Repository Structure

```
.claude-plugin/
  marketplace.json                    # Marketplace index
ai-assisted-development/              # Individual plugin
  .claude-plugin/
    plugin.json                       # Plugin manifest
  agents/                             # Custom agents
  skills/                             # Agent skills
  commands/                           # Slash commands
  hooks/
    hooks.json                        # Hook definitions
  scripts/                            # Scripts called by hooks
  templates/                          # Template files
CLAUDE.md                             # Personal context
devcontainer/                         # Isolated dev environment
```

### Adding New Agents, Skills, or Commands

1. Add your new file to the appropriate directory in `ai-assisted-development/` (`agents/`, `skills/`, or `commands/`)
2. Reload the plugin:
   ```
   /plugin uninstall ai-assisted-development@claude-code-toolbox
   /plugin install ai-assisted-development@claude-code-toolbox
   ```

### Creating New Plugins

1. Create a new directory at the repository root (e.g., `my-new-plugin/`)
2. Add the plugin structure:
   ```
   my-new-plugin/
     .claude-plugin/
       plugin.json
     agents/
     skills/
     commands/
   ```
3. Update `.claude-plugin/marketplace.json` to include the new plugin
4. Install the new plugin: `/plugin install my-new-plugin@claude-code-toolbox`

### Customizing CLAUDE.md

The `CLAUDE.md` file contains workflow preferences and instructions for Claude. Edit it to match your personal workflow and coding standards.
