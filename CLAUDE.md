# Claude Code Toolbox - Project Context

## Project Goal

The claude-code-toolbox is meant to be an incremental development approach to progressively build up to sophisticated claude code agent based workflows. As we build features we will use them to build more advanced features and so on. We should always be trying to build the minimal version of the next step. Always look out for scope creep and over engineering.

## Context Loading

**Load when developing plugin features, modifying agents**:
- @docs/claude-code-reference.md - Claude Code platform features, limitations, best practices
- @docs/agent-orchestration-patterns.md - Custom multi-agent coordination patterns (optional, for advanced workflows)

**Check before inventing solutions**:
- `docs/research/` - We may have already researched your question

## Critical Path Patterns

### Plugin Installation Paths

Plugin runs from `~/.claude/plugins/rhoai/rhoai-security-scanner/`, NOT `/workspace/`.

```bash
# Correct: Relative paths from plugin root
./agents/security-scanner.md
./scripts/generate-scan-metadata.py

# Wrong: Absolute paths to development workspace
/workspace/rhoai-security-scanner/agents/security-scanner.md
```

**Rule**: `/workspace/` contains repos being scanned, not the plugin. Agents use relative paths.

### Devcontainer Path Isolation

When working in devcontainer:
- `/mnt/localhost-claude` - Read-only view of host `~/.claude`
- `~/.claude` - Isolated container home (claude-home volume)
- `/workspace` - Project being worked on (this repo OR others)

Don't confuse localhost paths with container paths when debugging.

### Research-First Development

Before implementing:
1. Check `docs/research/` for existing research
2. Use Task tool with `claude-code-guide` subagent for official docs
3. Read current implementation before modifying
4. Look for concrete examples in source

**Pattern**: Read → Research → Plan → Implement

Avoids: guessing schemas, hallucinating APIs, reimplementing existing code.

## Common Mistakes

**Path confusion**: Referencing `/workspace/devcontainer/` from plugin code running in `~/.claude/plugins/`

**Premature implementation**: Writing code before reading existing implementation or checking research docs

**Plan document staleness**: `docs/plans/` may not reflect final implementation - use for historical context only

**Guessing schemas**: Claude Code plugin.json, marketplace.json, hooks.json have specific formats - research before modifying

**Ignoring scripts**: Python scripts exist for deterministic operations - don't duplicate their logic in agent prompts

## Development Workflow

1. **Read current state** - Files, docs, constraints
2. **Check research** - `docs/research/` and `claude-code-guide` subagent
3. **Load relevant docs** - Conditional loading per task type
4. **Implement** - Following established patterns
5. **Validate** - Tests, schema validation, self-review checklists
