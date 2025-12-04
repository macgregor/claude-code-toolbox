# Claude Code Toolbox

A Claude Code plugin providing agents, skills, commands, and MCP servers for productive development workflows.

For learning resources see [AI Learning Materials](./docs/ai-learning-material.md)

## Overview

This plugin provides:

- **Agents**: Code review and analysis agents
- **Skills**: Workflow skills for planning, brainstorming, git management, and more
- **Commands**: Slash commands for common workflows
- **MCP Servers**: Placeholder
- **Hooks**: Automated tasks like episodic memory sync and Chrome debugging setup

## Installation

### Clone the Repository

```bash
git clone https://github.com/macgregor/claude-code-toolbox.git
cd claude-code-toolbox
```

### Install the Plugin

**Option A: Install directly**

```bash
claude plugin install .
```

**Option B: Symlink for easier development**

```bash
ln -s $(pwd) ~/.claude/plugins/claude-code-toolbox
claude plugin install ~/.claude/plugins/claude-code-toolbox
```

Option B is recommended if you plan to customize the plugin, as it allows changes to take effect with just a reload command.

### Optional: Symlink CLAUDE.md

The `CLAUDE.md` file contains personal workflow preferences and context. You can symlink it to use it globally:

```bash
ln -s $(pwd)/CLAUDE.md ~/.claude/CLAUDE.md
```

Note: This overwrites any existing `~/.claude/CLAUDE.md`. Back up your current file first if needed.

## Usage

### Reloading After Changes

When you modify agents, skills, commands, hooks, or plugin.json:

```bash
/plugin reload claude-code-toolbox
```

Changes take effect immediately without reinstalling or restarting Claude Code.

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

### Adding New Agents, Skills, or Commands

1. Add your new file to the appropriate directory (`agents/`, `skills/`, or `commands/`)
2. Update `.claude-plugin/plugin.json` to include the new file path
3. Reload the plugin: `/plugin reload claude-code-toolbox`

### Customizing CLAUDE.md

The `CLAUDE.md` file contains workflow preferences and instructions for Claude. Edit it to match your personal workflow and coding standards.

### Plugin Structure

```
.claude-plugin/
  plugin.json          # Plugin manifest
agents/                # Custom agents
skills/                # Agent skills
hooks/
  hooks.json          # Hook definitions
scripts/               # Scripts called by hooks
CLAUDE.md             # Personal context
```
