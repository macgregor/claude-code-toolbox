# Claude Code Platform Reference

**Purpose**: Technical reference for Claude Code platform features, limitations, and best practices
**Audience**: AI agents building Claude Code plugins
**Updated**: 2025-12-10

---

## Table of Contents

1. [Platform Features](#platform-features)
2. [System Limitations](#system-limitations)
3. [Performance Optimization](#performance-optimization)
4. [Best Practices](#best-practices)
5. [Anti-Patterns](#anti-patterns)
6. [References](#references)

---

## Platform Features

### Agents (Subagents)

Markdown files with YAML frontmatter spawning isolated agent instances.

**Location**: `.claude/agents/` or plugin `agents/` directory

**Spawning**: `Task(subagent_type="agent-name", prompt="task description")`

**Features**:
- Isolated context windows with specialized system prompts
- Configurable tool access via `allowed-tools`
- Model selection: `sonnet`, `opus`, `haiku`, `inherit`
- Resumable conversations via `resume` parameter (requires `agentId` from initial invocation)

**Built-in Agents**:
- `general-purpose`: Multi-step tasks, code search, execution
- `plan`: Research and planning (use during plan mode or invoke directly)
- `explore`: Read-only codebase exploration (optimized for file discovery)

**Limitations**:
- Subagents cannot spawn other subagents (use slash commands for orchestration)
- Subagent context not automatically available to parent (requires explicit bridging via files)

**Reference**: [Subagents Documentation](https://code.claude.com/docs/en/sub-agents)

---

### Skills

Auto-discovered directories with SKILL.md for context-based invocation.

**Location**: `~/.claude/skills/` (personal) or `.claude/skills/` (project)

**Structure**:
- `SKILL.md` with YAML frontmatter: `name`, `description`, `allowed-tools`
- Optional supporting files

**Features**:
- Progressive disclosure: metadata → instructions → resources
- Automatic invocation based on context (no explicit user request)

**Limitations**:
- Agents don't reliably use skills without reinforcement via hooks and prompt engineering
- Currently better to inline prompts in agents rather than relying on skills

**Reference**: [Skills Documentation](https://code.claude.com/docs/en/skills)

---

### Hooks

Automated commands at lifecycle events for workflow automation and quality gates.

**Events**: PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStart, SubagentStop, SessionStart, PreCompact, Notification

**Configuration**: `hooks.json` with matchers for specific tools/agents

**Features**:
- Exit Code 2 blocks operation and shows error message
- Prompt-based hooks for context-aware decisions
- Enable deterministic workflow automation without user interruption

**SubagentStart/SubagentStop Behavior**:
- Fires for BOTH slash command and Task tool invocations
- Requires matcher configuration (use `"*"` to capture all agents)
- Restrictive matchers (e.g., `"matcher": "document-reviewer"`) only fire for matching agents
- Added in Claude Code v2.0.43
- Event sequence: PreToolUse (Task) → SubagentStart → agent execution → SubagentStop → PostToolUse (Task)
- Session initialization may spawn internal agents (visible in hooks)

**Hook Matcher Best Practices**:
- Use `"*"` for universal lifecycle tracking (all tools/agents)
- Use specific tool names for targeted behavior (e.g., `"matcher": "Task"`)
- Use agent names for agent-specific hooks (e.g., `"matcher": "document-reviewer"`)
- SubagentStart/SubagentStop matchers apply to agent type names, not tool names

**Security**:
- Hooks run with current environment credentials
- Consider security implications when executing commands

**Reference**: [Hooks Guide](https://code.claude.com/docs/en/hooks-guide)

---

### Plugins

Distributable packages bundling commands, agents, MCP servers, and hooks.

**Structure**:
- `.claude-plugin/plugin.json` (manifest)
- `marketplace.json` (marketplace metadata)

**Features**:
- Install via `/plugin` command
- `${CLAUDE_PLUGIN_ROOT}` environment variable for portable paths (only available to scripts executed by hooks)
- `strict` flag controls manifest inheritance

**Limitations**:
- `${CLAUDE_PLUGIN_ROOT}` not available to agent-executed bash commands by default

**Reference**: [Plugin Marketplaces](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces)

---

### Slash Commands

User-facing shortcuts executing workflows or spawning agents.

**Location**: `.claude/commands/` as markdown files

**Frontmatter**: `description`, `allowed-tools`, `model`, `argument-hint`

**Features**:
- Invoked via `/command-name` or programmatically via SlashCommand tool
- Good for orchestrating multiple agents sequentially

**Reference**: [Plugin Structure](https://claude-plugins.dev/skills/@anthropics/claude-code/plugin-structure)

---

### MCP (Model Context Protocol)

Standardized connections to data sources and external tools.

**Architecture**: JSON-RPC based client-server communication

**Primitives**:
- Server-side: Prompts, Resources, Tools
- Client-side: Roots, Sampling

**Pre-built Servers**: Google Drive, Slack, GitHub, Git, Postgres, Puppeteer

**Reference**: [MCP Introduction](https://www.anthropic.com/news/model-context-protocol)

---

### Memory System

Persistent cross-session context via CLAUDE.md files.

**Hierarchy**: enterprise → user → project levels

**Features**:
- Automatic loading at session start
- Cross-session state persistence
- Reference files via `@docs/architecture.md` syntax

**Reference**: [Memory Management](https://code.claude.com/docs/en/memory)

---

## System Limitations

### Context Management

**Context Rot**: Model recall decreases as token count increases

**Constraints**:
- Context is finite, precious resource requiring strategic curation
- Long contexts decrease performance and increase costs

**Mitigation**: Use sub-agents for context isolation, just-in-time loading, and compaction at checkpoints. See [Performance Optimization](#performance-optimization).

**Reference**: [Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

### Agent Execution

**Limitations**:
- No universal agent identifier (track via environment variables, metadata, hooks)
- Subagent context not automatically available to parent (requires explicit bridging)
- Session history stored in `~/.claude/projects/` for resumption

**Recommendations**:
- Maximum ~10 parallel subagents per workflow
- Use file-based state for cross-agent communication (see [Cross-Agent Communication](#cross-agent-communication))

---

### Tool and Permission Constraints

**Sandboxing**: Reduces permission prompts by 84% via automatic allow/block

**Tool Access**: Controlled via `allowed-tools` in frontmatter

**Bash Tool**: Terminal operations only (use specialized tools for file operations: Read, Write, Edit, Grep, Glob)

---

### Performance Constraints

**Structured Outputs**: Incompatible with citations and message prefilling

**Background Execution**: Bash tool supports background tasks (10-minute max timeout)

---

## Performance Optimization

### Parallel Tool Execution

**Critical**: Batch independent operations in single message for 40-60% speedup.

**Recommended Batching Limits**:
- WebSearch/WebFetch: 3-5 calls per message
- Grep searches: 5-7 patterns
- Read operations: 5 files
- Glob patterns: 3-5 patterns per message

**Agent Prompt Template**:
```markdown
CRITICAL: Use parallel execution for independent operations.
Execute multiple WebSearch/Grep/Read calls in a SINGLE message when no dependencies exist.
DO NOT execute tools sequentially when they can run in parallel.
```

**Benefits**:
- Reduced API call overhead
- Lower context switching costs
- Faster overall execution

---

### Model Selection Strategy

**Haiku**: Fast deterministic tasks, data gathering, simple execution

**Sonnet**: Complex reasoning, planning, synthesis, validation

**Opus**: Maximum capability for critical decisions

**Typical Workflow**: Sonnet (plan) → Haiku (execute) → Sonnet (review)

---

### Context Caching

**Mechanism**: Schema compilation and repeated information cached for 24 hours

**Impact**: Primary optimization for long context scenarios

**Tradeoff**: First compilation has higher latency

---



## Best Practices

### Hook-Based Quality Gates

Use SubagentStop hooks with Exit Code 2 to block progression until quality standards met.

**Implementation**:
- Prompt-based hook evaluates agent output
- Exit with code 2 if below threshold
- Shows error message to agent for retry/refinement

**Use Cases**: Validation before handoff, output quality checks, compliance verification

---

### Cross-Agent Communication

**File-Based State Transfer**: Hooks write JSON/Markdown artifacts, receiving agent reads files. Requires explicit contracts for data format.

**Persistent State**: Use CLAUDE.md for cross-session state (hierarchical loading: enterprise → user → project)

---

## Anti-Patterns

### Hook Configuration

**❌ Restrictive Hook Matchers for Lifecycle Tracking**:
- DON'T: Use agent-specific matchers (e.g., `"matcher": "document-reviewer"`) for lifecycle tracking
- DO: Use `"*"` matcher for universal SubagentStart/SubagentStop tracking
- **Impact**: Missing events, incomplete observability
- **Common mistake**: SubagentStop fires but SubagentStart doesn't

---

### Tool Usage

**❌ Sequential When Parallel Possible**:
- DON'T: Execute independent tool calls in separate messages
- DO: Batch 3-5 independent calls in single message
- **Impact**: 40-60% slower execution

**❌ Wrong Model Selection**:
- DON'T: Use Sonnet for simple data retrieval
- DO: Use Haiku for deterministic tasks, Sonnet for reasoning
- **Impact**: Higher costs, slower execution

---

## Appendices

- [Session Log Messages](appendix/session-log-messages.md) - Message formats for conversation history and session state
- [Hook Input Messages](appendix/hook-input-messages.md) - Event notifications for automation and orchestration

---

## References

### Official Documentation
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)
