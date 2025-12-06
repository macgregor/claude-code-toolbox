# Claude Code Toolbox - Project Context

## Project Goal

The claude-code-toolbox is meant to be an incremental development approach to progressively build up to sophisticated claude code agent based workflows. As we build features we will use them to build more advanced features and so on. We should always be trying to build the minimal version of the next step. Always look out for scope creep and over engineering.

## Plugin Development Anti-Patterns

### Pattern: Research Before Guessing
**Evidence**: commits 4fbbf0b, bba6f70
**Context**: Plugin development (plugin.json schema, marketplace.json format, validation rules)
**Guidance**: ALWAYS research first before making changes:
- Look for applicable research docs in `docs/research/` (we may have already done the research)
- Use Task tool with `claude-code-guide` subagent to search official docs
- Look for concrete examples in documentation
- Look for working examples in source code
- Check validation output for specific error messages that contain hints
**Example**: See `docs/research/` for existing research reports on Claude Code features

## Path Context Awareness

### Pattern: Plugin Installation Paths
**Evidence**: commits bba6f70, 2a8470f
**Context**: When code runs as an installed Claude Code plugin
**Guidance**:
- Plugin location: `~/.claude/plugins/claude-code-toolbox/`
- Agents/skills referenced relative to plugin root
- **Never use** `/workspace/` paths in plugin code - workspace is for the projects being worked on
**Example**: Agent files in plugin referenced as `./agents/web-research.md`, not `/workspace/ai-assisted-development/agents/web-research.md`

### Pattern: Devcontainer Path Isolation
**Evidence**: commits 2a8470f, a4553a5
**Context**: When running in the isolated devcontainer
**Guidance**:
- Localhost `~/.claude` mounted read-only at `/mnt/localhost-claude`
- Container's isolated `~/.claude` on `claude-home` volume
- `/workspace` contains the project being worked on (could be this repo or others)
**Example**: See `docs/plans/2025-12-04-devcontainer-design.md` for complete isolation strategy

### Pattern: Common Path Confusion Errors
**Evidence**: commits bba6f70, 2a8470f
**Context**: Path-related bugs in plugin and devcontainer code
**Guidance**: Avoid these mistakes:
- Trying to reference `/workspace/devcontainer/scripts/` from plugin code that runs from `~/.claude/plugins/`
- Confusing localhost file paths with container paths when debugging
- Not recognizing when we're working inside vs outside the devcontainer

## Implementation Process

### Pattern: Context-First Development
**Evidence**: commits bba6f70, 98e05b6
**Context**: Before suggesting any code modifications
**Guidance**: Follow this checklist:
1. **Read the current implementation** - Read relevant files to understand what exists
2. **Read design docs** - Check `docs/plans/` for architecture decisions already made
3. **Understand constraints** - This repo has specific constraints (Podman-only, isolated ~/.claude, etc.)
4. **Look for applicable research docs** - Check `docs/research/` for research that could improve your implementation
**Example**: Before modifying devcontainer, read `docs/plans/2025-12-04-devcontainer-design.md` to understand isolation rationale

## Devcontainer Development Notes

### Pattern: General-Purpose Devcontainer Design
**Evidence**: commits 2a8470f, a4553a5
**Context**: The devcontainer is GENERAL-PURPOSE, not specific to this repo
**Guidance**:
- Can be used for ANY project, not just claude-code-toolbox development
- DO NOT add repo-specific configuration to devcontainer (Containerfile, entrypoint.sh, etc.)
- Project-specific hooks/scripts belong in `<repo>/.claude/`, NOT in devcontainer config
- Public plugins (for general use) CAN be added to entrypoint.sh PLUGINS array
- THIS repo's marketplace and plugin must be installed manually when working on this repo:
  ```bash
  make install-plugin  # Installs marketplace and plugin (idempotent)
  ```
**Example**: The `ai-assisted-development` plugin is installed via Makefile, not baked into devcontainer image

### Pattern: Devcontainer Isolation Architecture
**Evidence**: commits 2a8470f, a4553a5
**Context**: Devcontainer design evolved to solve path portability issues
**Guidance**:
- Container maintains **isolated** `~/.claude` on persistent volume (includes its own plugins)
- Localhost `~/.claude` mounted read-only at `/mnt/localhost-claude` for selective config sync
- Plugins are installed IN THE CONTAINER, not synced from localhost (absolute path issues)
- `/workspace` in container maps to project directory on localhost
**Example**: See `docs/plans/2025-12-04-devcontainer-design.md` for full rationale

### Pattern: Devcontainer Configuration Changes
**Evidence**: commits 2a8470f, 88e1689
**Context**: When modifying devcontainer config files
**Guidance**:
- Containerfile layer ordering matters for cache efficiency
- entrypoint.sh is baked into image (requires rebuild to change)
- Both CLI (`claude-isolated`) and VS Code use same setup
**Example**: Changes to entrypoint.sh require `make rebuild-container` to take effect

## Plugin Development Workflow

### Pattern: Plugin Testing and Validation
**Evidence**: commits 4fbbf0b, 817f6d9, 32f89b1
**Context**: This repo IS a Claude Code plugin/marketplace
**Guidance**: Testing changes:
- `claude plugin validate ./` - Validate marketplace
- `claude plugin validate ./ai-assisted-development/` - Validate specific plugin
- `/plugin reload claude-code-toolbox` - Reload after changes (if symlinked)
- Agent files must be listed as array of `.md` paths, not directory path
**Example**: See `ai-assisted-development/.claude-plugin/plugin.json` where agents are listed as `["./agents/web-research.md", "./agents/codebase-research.md", ...]`

## Agent Development Patterns

### Pattern: Two-Layer Architecture (Command → Agent)
**Evidence**: commit 6b5156c
**Context**: Agent architecture evolved from three-layer to two-layer pattern
**Guidance**: Do not use skill layer - agents cannot reliably invoke skills via Skill tool. Commands should directly launch agents via Task tool. Move complete workflow into agent definition rather than splitting across command→skill→agent.
**Example**: See `ai-assisted-development/agents/web-research.md` which contains full workflow, invoked directly by command

### Pattern: Performance Optimization via Parallel Execution
**Evidence**: commits f02da8a, 5ef3654, 36267ca
**Context**: Agent performance optimization
**Guidance**:
- Use haiku model for faster execution in research/indexing agents
- Batch operations: 3-5 WebSearch/Glob calls in single message, 5-7 Grep searches, 5 Read calls
- Add CRITICAL markers in agent prompts to prevent sequential operations
- Emphasize parallel execution explicitly in agent instructions
**Example**: `ai-assisted-development/agents/context-indexing.md` batches 5 Glob patterns and 5 Read calls per message
