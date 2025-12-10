# Claude Code Platform Reference

**Purpose**: Technical reference for Claude Code platform features, limitations, and best practices
**Audience**: AI agents building Claude Code plugins
**Updated**: 2025-12-10

---

## Table of Contents

1. [Platform Features](#platform-features)
2. [System Limitations](#system-limitations)
3. [Performance Optimization](#performance-optimization)
4. [Context Engineering](#context-engineering)
5. [Best Practices](#best-practices)
6. [Anti-Patterns](#anti-patterns)
7. [References](#references)

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
- Subagent context NOT automatically available to parent (requires explicit bridging via files)

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

**Use Cases**:
- Project-specific instructions
- Agent coordination state
- External memory for workflows

**Reference**: [Memory Management](https://code.claude.com/docs/en/memory)

---

## System Limitations

### Context Management

**Context Rot**: Model recall decreases as token count increases

**Constraints**:
- Context is finite, precious resource requiring strategic curation
- Long contexts decrease performance and increase costs

**Mitigation**:
- Use sub-agents for context isolation
- Just-in-time loading (load data only when needed)
- Compaction at checkpoints

**Reference**: [Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

### Agent Execution

**Limitations**:
- No universal agent identifier (track via environment variables, metadata, hooks)
- Subagent context NOT automatically available to parent
- Session history stored in `~/.claude/projects/` for resumption

**Recommendations**:
- Maximum ~10 parallel subagents per workflow
- Use file-based state for cross-agent communication

---

### Tool and Permission Constraints

**Sandboxing**: Reduces permission prompts by 84% via automatic allow/block

**Tool Access**: Controlled via `allowed-tools` in frontmatter

**Bash Tool**: Terminal operations only (use specialized tools for file operations: Read, Write, Edit, Grep, Glob)

---

### Performance Constraints

**Schema Compilation**:
- First compilation has higher latency
- 24-hour cache for repeated compilations

**Structured Outputs**: Incompatible with citations and message prefilling

**Token Efficiency**: Markdown ~15% more token-efficient than JSON (but less validated)

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

### Just-in-Time Loading

**Pattern**: Maintain lightweight identifiers, load data only when needed

**Benefits**:
- Avoids context bloat
- Reduces token usage
- Enables larger agent libraries

**Implementation**: Reference data by ID/path, use tools to fetch on-demand

**Reference**: [Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

## Context Engineering

### Writing Context (External Memory)

**CLAUDE.md Files**: Platform-provided persistent project knowledge
- Hierarchical loading (enterprise → user → project)
- Cross-session state persistence
- Automatic loading at session start

**File-Based State**: Inter-agent communication workaround
- JSON/Markdown artifacts for data exchange
- Hooks write context files for parent access

---

### Selecting Context (Retrieval)

**Information Positioning**: Critical info at beginning or end of context (better recall)

**Tool Description Filtering**: Only fetch relevant tools (reduces context overhead)

---

### Compressing Context (Summarization)

**Progressive Summarization**: Compress across iterations

**Hierarchical Processing**: Use sub-agents to process and summarize chunks

**Compaction**: Workflow compaction at checkpoints (automatic in Claude Code)

---

### Isolating Context (Sub-agents)

**Benefits**:
- Separate context windows prevent pollution
- Enable parallelization of tasks
- Fresh agent spawning when context limits reached

**Handoff Contracts**: Preserve necessary context across agent boundaries

---

### System Prompt Design Principles

**Clarity and Structure**:
- Use simple, direct language at appropriate altitude
- Avoid overly complex brittle logic
- Avoid vague high-level guidance
- Organize with clear sections (XML tags or Markdown headings)

**Concrete Examples**:
- Multishot prompting with 3-5 diverse examples
- Demonstrate desired output format and style
- Avoid edge-case stuffing
- Show patterns to follow, not just rules

**Tool Design**:
- Self-contained operations
- Robust to errors with clear error messages
- Clear descriptions of intended use
- Token-efficient (minimize overhead)
- Verbose, explicit parameter descriptions

**Structured Template**:
```markdown
# Agent Role
[Clear, specific role definition]

## Core Responsibilities
1. [Specific responsibility]
2. [Specific responsibility]

## Workflow
1. [Concrete step with tool usage]
2. [Concrete step with tool usage]

## Output Format
[Exact format with examples]

## Quality Criteria
- [Specific, measurable criterion]
```

---

### Token Efficiency Techniques

**Markdown vs JSON**:
- Markdown ~15% more token-efficient than JSON
- Use JSON Schema for strict validation needs
- Use Markdown for human readability and efficiency

**Progressive Disclosure** (for Skills):
- Load metadata first (always)
- Load instructions on-demand
- Load resources as-needed
- Enables large agent libraries without context bloat

**CLAUDE.md Pattern**:
- Lightweight, project-specific instruction format
- Quick parsing without verbose documentation
- Dos/don'ts with version-specific instructions
- File-scoped commands (type check, format, lint per file)

---

## Best Practices

### Agent Design

**Single Responsibility**: One goal, one input, one output, one handoff rule per agent

**Example**:
```yaml
---
name: spec-tester
description: Writes and executes comprehensive test suites for validated specifications
model: haiku
tools: [Read, Write, Edit, Bash, Grep, Glob]
---
```

**Clear Boundaries**: Prevent context pollution, enable focused debugging

---

### Hook-Based Quality Gates

**Pattern**: Use SubagentStop hooks with Exit Code 2 to block progression until quality standards met

**Implementation**:
- Prompt-based hook evaluates agent output
- Exit with code 2 if below threshold
- Shows error message to agent for retry/refinement

**Use Cases**: Validation before handoff, output quality checks, compliance verification

---

### Cross-Agent Communication

**File-Based State Transfer**: Workaround for isolated contexts
- Hooks write JSON/Markdown artifacts
- Receiving agent reads files
- Explicit contracts for data format

**Memory Systems**: Use CLAUDE.md for persistent state across sessions

---

## Anti-Patterns

### Context Management

**❌ Uniform Context Loading**:
- DON'T: Load all possible data upfront
- DO: Just-in-time loading with lightweight identifiers
- **Impact**: Context bloat, decreased performance

**❌ Ignoring Context Rot**:
- DON'T: Assume perfect recall in long contexts
- DO: Use sub-agents for context isolation
- **Impact**: Degraded accuracy, missed information

**❌ Missing External Memory**:
- DON'T: Rely solely on context window for state
- DO: Use CLAUDE.md files for cross-session persistence
- **Impact**: Loss of continuity across sessions

---

### Agent Design

**❌ Vague Descriptions**:
- DON'T: "A helpful agent for development tasks"
- DO: "Writes and executes Python unit tests using pytest framework"
- **Impact**: Poor auto-invocation, unclear scope

**❌ Multiple Responsibilities**:
- DON'T: Single agent handling planning, execution, review, deployment
- DO: Separate agents for each concern
- **Impact**: Context pollution, harder debugging

**❌ Skipping Examples**:
- DON'T: Provide only abstract instructions
- DO: Include 3-5 concrete examples of desired behavior
- **Impact**: Inconsistent outputs, misinterpretation

---

### Tool Usage

**❌ Sequential When Parallel Possible**:
- DON'T: Execute independent WebSearch calls in separate messages
- DO: Batch 3-5 independent calls in single message
- **Impact**: 40-60% slower execution

**❌ Wrong Model Selection**:
- DON'T: Use Sonnet for simple data retrieval
- DO: Use Haiku for deterministic tasks, Sonnet for reasoning
- **Impact**: Higher costs, slower execution

**❌ Missing Tool Descriptions**:
- DON'T: Minimal or unclear tool parameter descriptions
- DO: Verbose, explicit descriptions with examples
- **Impact**: Tool selection errors, invalid inputs

---

### Hook Configuration

**❌ Restrictive Hook Matchers**:
- DON'T: Use agent-specific matchers (e.g., `"matcher": "document-reviewer"`) for lifecycle tracking
- DO: Use `"*"` matcher for universal SubagentStart/SubagentStop tracking
- **Impact**: Missing events, incomplete observability, debugging difficulties
- **Common mistake**: SubagentStop fires but SubagentStart doesn't (due to restrictive matcher)

---

## References

### Official Documentation
- [Subagents](https://code.claude.com/docs/en/sub-agents)
- [Skills](https://code.claude.com/docs/en/skills)
- [Hooks Guide](https://code.claude.com/docs/en/hooks-guide)
- [Plugin Marketplaces](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces)
- [MCP Introduction](https://www.anthropic.com/news/model-context-protocol)
- [Memory Management](https://code.claude.com/docs/en/memory)
- [Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)

### Research Papers
- [ReAct: Synergizing Reasoning and Acting](https://arxiv.org/abs/2210.03629)
- [AI Agentic Programming Survey](https://arxiv.org/html/2508.11126v1)
- [Agent Data Protocol](https://arxiv.org/html/2510.24702v1)
- [Prompt Format Impact](https://arxiv.org/html/2411.10541v1)

### Research Documents (this repository)
- [Agentic Development Practices](../web/2025-12-05-agentic-development-practices-claude-code.md)
- [Claude Code Features & Architecture](../web/2025-12-05-claude-code-features-architecture.md)
- [Context Engineering Techniques](../web/2025-12-05-context-engineering-ai-agents.md)
- [Multi-Agent Orchestration Patterns](../web/2025-12-05-multi-agent-orchestration-claude-code.md)
- [Agent Performance Optimization](../web/2025-12-05-claude-code-agent-performance.md)
- [TodoWrite & Checkpointing](../web/2025-12-06-todowrite-checkpointing.md)
- [Agent Identifiers](../web/2025-12-06-claude-code-agent-identifiers.md)
- [LLM Agent Control Loops](../web/2025-12-06-llm-agent-control-loops.md)
- [AI Agent Communication Formats](../web/2025-12-06-ai-agent-communication-formats.md)
- [Concurrent Agent Execution](../web/2025-12-06-claude-code-concurrent-agents.md)
