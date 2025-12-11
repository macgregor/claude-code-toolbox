# Claude Code Toolbox - Project Context

**For AI agents working on this repository.**

## Project Goal

Build infrastructure for agent coordination using Claude Code platform. Incremental development: use features to build more advanced features. Build the minimal version of the next step. Avoid scope creep and over-engineering.

## Always Load

Core project documentation (always loaded via @):
- @ARCHITECTURE.md - System design and lifecycle tracking
- @CONTRIBUTING.md - Development workflow, building, testing, installing
- @README.md - User-facing overview and doc index

## Conditional Loading

Load these when relevant to your task:

**When developing plugin features or modifying agents**:
- docs/claude-code-reference.md - Claude Code platform features, limitations, patterns
- docs/agent-orchestration-patterns.md - Multi-agent coordination patterns (optional, for advanced workflows)

**When working with devcontainer**:
- docs/devcontainer.md - Isolated development environment

**When working with hook events or session logs**:
- docs/appendix/session-log-messages.md - Message formats for conversation history
- docs/appendix/hook-input-messages.md - Event notifications for automation

**Historical context only (likely outdated)**:
- docs/plans/ - Implementation plans (may not reflect current state)
- docs/research/ - Research documents (check before reinventing, but verify current state)

## Critical Patterns

### Plugin vs Project Files

**Plugin files** (installed to `~/.claude/plugins/.../`):
- `ai-assisted-development/agents/foo.md` - End user's system
- Use relative paths from plugin root

**Project files** (local to this repository):
- `.claude/agents/bar.md` - Development only
- Not available to end users

**Rule**: When building plugin features, reason about paths as they exist on end users' systems.

### Path Contexts

Three environments exist:
1. **Development**: `/workspace/` (this repository)
2. **Devcontainer**: Isolated `~/.claude` on volume, `/workspace/` mounted project, `/mnt/localhost-claude` read-only host config
3. **End user**: Plugin installed via marketplace to `~/.claude/plugins/.../`

Avoid hardcoding paths specific to development environment.

### Development Workflow

1. Read current implementation before modifying
2. Check docs/research/ for existing research (but verify current state)
3. Use Task tool with `claude-code-guide` for official Claude Code docs
4. Follow established patterns in codebase
5. Test changes with `make test` and `make install-plugin`

## Common Mistakes

**Path confusion**: Referencing development paths from plugin code that runs on end user's system

**Premature implementation**: Writing code before reading existing implementation

**Stale documentation**: docs/plans/ may not reflect current state - verify with source code

**Guessing schemas**: Claude Code plugin.json, marketplace.json, hooks.json have specific formats - research first

**Bypassing scripts**: Python scripts exist for deterministic operations - don't duplicate in agent prompts

## YAML Frontmatter Template

```yaml
---
name: document-name  # required: lowercase-with-hyphens, max 64 chars
description: >  # required: when should AI load this? max 1024 chars
  Clear statement of when AI should load this document.
categories: [category1, category2]  # optional: broad classification
tags: [tag1, tag2]  # optional: specific concepts
related_docs:  # optional: relative paths from project root
  - path/to/doc.md
complexity: basic  # optional: basic|intermediate|advanced
---
```
