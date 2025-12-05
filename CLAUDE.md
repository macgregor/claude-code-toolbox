# Claude Code Toolbox - Project Context

## Project Goal

The claude-code-toolbox is meant to be an incremental development approach to progressively build up to sophisticated claude code agent based workflows. As we build features we will use them to build more advanced features and so on. We should always be trying to build the minimal version of the next step. If we get too ambitious too fast we will fail. Always look out for scope creep and over engineering. Sophisticated abilities will come from many small advancements.

## Critical: Research, Don't Guess

When working with Claude Code plugin system specifics (plugin.json schema, marketplace.json format, validation rules), **ALWAYS research first**:
- Look for applicable research docs in `docs/research/` (we may have already done the research)
- Use Task tool with `claude-code-guide` subagent to search official docs
- Look for concrete examples in documentation
- Look for working examples in source code
- Check validation output for specific error messages that contain hints


**Anti-pattern seen repeatedly**: Guessing at plugin.json field formats, trying random solutions in a loop.
**Correct approach**: Use research tools, read error messages carefully, find official examples.

## Path Context Awareness

This repo involves multiple path contexts that must not be confused:

### Plugin Installation Paths
When code runs as an installed Claude Code plugin:
- Plugin location: `~/.claude/plugins/claude-code-toolbox/`
- Agents/skills referenced relative to plugin root
- **Never use** `/workspace/` paths in plugin code - workspace is for the projects being worked on

### Devcontainer Paths
When running in the isolated devcontainer:
- Localhost `~/.claude` mounted read-only at `/mnt/localhost-claude`
- Container's isolated `~/.claude` on `claude-home` volume
- `/workspace` contains the project being worked on (could be this repo or others)
- Understand which environment you're operating in before suggesting changes

### Common Mistakes
- Trying to reference `/workspace/devcontainer/scripts/` from plugin code that runs from `~/.claude/plugins/`
- Confusing localhost file paths with container paths when debugging
- Not recognizing when we're working inside vs outside the devcontainer

## Implementation Changes

Before suggesting modifications:
1. **Read the current implementation** - Read relevant files to understand what exists
2. **Read design docs** - Check `docs/plans/` for architecture decisions already made
3. **Understand constraints** - This repo has specific constraints (Podman-only, isolated ~/.claude, etc.)
4. **Look for applicable research docs** - Check `docs/research/` for research that could improve your implementation

Don't redesign from scratch without understanding why current approach was chosen.

## Devcontainer-Specific Notes

The devcontainer design evolved to solve path portability issues:
- Container maintains **isolated** `~/.claude` on persistent volume
- Selective config sync from localhost via read-only mounts + symlinks
- Only `/workspace` couples to localhost filesystem
- See `docs/plans/2025-12-04-devcontainer-design.md` for full rationale

When modifying devcontainer config:
- Containerfile layer ordering matters for cache efficiency
- entrypoint.sh is baked into image (requires rebuild to change)
- Both CLI (`claude-isolated`) and VS Code use same setup

## Plugin Development Workflow

This repo IS a Claude Code plugin/marketplace. Testing changes:
- `claude plugin validate ./` - Validate marketplace
- `claude plugin validate ./ai-assisted-development/` - Validate specific plugin
- `/plugin reload claude-code-toolbox` - Reload after changes (if symlinked)
- Agent files must be listed as array of `.md` paths, not directory path
