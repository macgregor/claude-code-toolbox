# Claude Code Toolbox

Development workflow agents for Claude Code. Research, synthesize, design, and review -- with structured output and validation.

## What This Does

The `ai-assisted-development` plugin provides specialized agents for common development tasks:

- **Web Research** -- Structured web research with validated report output
- **Codebase Research** -- Architectural analysis of repositories
- **Synthesis** -- Combine research reports into focused insights
- **Document Reviewer** -- Quality analysis of markdown documentation
- **Statusline** -- Shows plugin version and installation status in Claude Code

Agents produce validated, structured output using templates and validation scripts.

## Quick Start

### Install

```bash
git clone https://github.com/macgregor/claude-code-toolbox.git
cd claude-code-toolbox
make install-plugin
```

### Use on Your Projects

Navigate to any repository and use Claude Code normally:

```bash
cd ~/your-project
claude
```

Invoke agents via commands (e.g. `/web-research "topic"`) or spawn them directly.

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - Local development setup and testing
- [docs/devcontainer.md](docs/devcontainer.md) - Isolated development environment
- [docs/claude-code-reference.md](docs/claude-code-reference.md) - Platform features and constraints
- [docs/ai-learning-material.md](docs/ai-learning-material.md) - AI development resources
