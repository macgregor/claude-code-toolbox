# Claude Code Agent Design Considerations

**Document Purpose**: Comprehensive reference for designing high-quality Claude Code agents  
**Target Audience**: AI systems and developers building agent markdown files  
**Last Updated**: 2025-12-09

---

## Table of Contents

1. [Claude Code Features](#claude-code-features)
2. [System Limitations](#system-limitations)
3. [Agent Architecture Patterns](#agent-architecture-patterns)
4. [Performance Optimization](#performance-optimization)
5. [Context Engineering](#context-engineering)
6. [Multi-Agent Coordination](#multi-agent-coordination)
7. [Quality Assurance Patterns](#quality-assurance-patterns)
8. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
9. [References](#references)

---

## Claude Code Features

### Core Extension Mechanisms

**Agents** (Subagents)
- Markdown files with YAML frontmatter in `.claude/agents/` or plugin `agents/` directory
- Isolated context windows, specialized system prompts, configurable tools
- Spawned via Task tool: `Task(subagent_type="agent-name", prompt="task description")`
- Support resumable conversations via `resume` parameter, requires `agentId` which is returned in the message when the agent is originally invoked
- Model selection: `sonnet`, `opus`, `haiku`, or `inherit` from parent
- Built-in agents: `general-purpose`, `plan`, `explore`
    - `plan` subagent: use during plan mode, can also be invoked. conduct research and gather information about your codebase before presenting a plan
    - `explore` subagent: lightweight agent optimized for searching and analyzing codebases. It operates in strict read-only mode and is designed for rapid file discovery and code exploration.
- **Limitation**: subagents cannot spawn other subagents, use slash commands to orchestrate multiple agents.
- **Reference**: [Subagents Documentation](https://code.claude.com/docs/en/sub-agents)

**Skills**
- Auto-discovered directories with `SKILL.md` and optional supporting files
- YAML frontmatter: `name`, `description`, `allowed-tools`
- Context-based automatic invocation (no explicit user request needed)
- Stored in `~/.claude/skills/` (personal) or `.claude/skills/` (project)
- Progressive disclosure: metadata → instructions → resources
- **Limitation**: agents often dont reliably use skills without a lot of reinforcement using hooks and prompt engineering to encourage specific skill usage. For now its better not to use skills for agents and instead inline prompts instead.
- **Reference**: [Skills Documentation](https://code.claude.com/docs/en/skills)

**Hooks**
- Automated commands at lifecycle events: PreToolUse, PostToolUse, UserPromptSubmit, Stop, SubagentStop, SessionStart, PreCompact, Notification
- Configuration in `hooks.json` with matchers for specific tools
- Exit Code 2 blocks operation and shows error (enables quality gates)
- Prompt-based hooks for context-aware decisions
- Enable deterministic workflow automation without interruption
- **Reference**: [Hooks Guide](https://code.claude.com/docs/en/hooks-guide)

**Plugins**
- Bundle commands, agents, MCP servers, hooks into distributable packages
- Structure: `.claude-plugin/plugin.json` + `marketplace.json`
- Install via `/plugin` command
- `${CLAUDE_PLUGIN_ROOT}` environment variable for portable paths (**NOTE** currently only available to scripts executed by hooks, if an agent manually runs a bash command it will not have access to this env variable out of the box)
- `strict` flag controls manifest inheritance
- **Reference**: [Plugin Marketplaces](https://docs.claude.com/en/docs/claude-code/plugin-marketplaces)

**Slash Commands**
- User-facing shortcuts stored in `.claude/commands/` as markdown files
- YAML frontmatter: `description`, `allowed-tools`, `model`, `argument-hint`
- Invoked via `/command-name` or programmatically via SlashCommand tool
- Can trigger agents, execute workflows, or run specific tasks
- good for orchestration
- **Reference**: [Plugin Structure](https://claude-plugins.dev/skills/@anthropics/claude-code/plugin-structure)

**MCP (Model Context Protocol)**
- Standardized connections to data sources and external tools
- JSON-RPC based communication between clients and servers
- Primitives: Prompts, Resources, Tools (server-side); Roots, Sampling (client-side)
- Pre-built servers: Google Drive, Slack, GitHub, Git, Postgres, Puppeteer
- **Reference**: [MCP Introduction](https://www.anthropic.com/news/model-context-protocol)

**Memory System**
- `CLAUDE.md` files for persistent project context (automatic loading)
- Hierarchical: enterprise → user → project levels
- Cross-session state persistence for agent coordination
- Acts as external memory for multi-agent workflows
- reference common files like `@docs/architecture.md`
- **Reference**: [Memory Management](https://code.claude.com/docs/en/memory)

---

## System Limitations

### Context Management
- Models experience "context rot" - recall decreases as token count increases
- Context is a precious, finite resource requiring strategic curation
- Long contexts lead to decreased performance and higher costs
- **Mitigation**: Use compaction, sub-agents for isolation, just-in-time loading
- **Reference**: [Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

### Agent Execution
- No universal agent identifier - tracking via environment variables, metadata, hooks
- Subagent context NOT automatically available to parent (requires explicit bridging)
- Maximum ~10 parallel subagents recommended per workflow
- Session history stored in `~/.claude/projects/` for resumption

### Tool and Permission Constraints
- Hooks run with current environment credentials (security consideration)
- Sandboxing reduces permission prompts by 84% via automatic allow/block
- Tool access controlled via `allowed-tools` in frontmatter
- Bash tool for terminal operations only - use specialized tools for file operations

### Performance Constraints
- First schema compilation has higher latency (24-hour cache)
- Structured outputs incompatible with citations and message prefilling
- Markdown ~15% more token-efficient than JSON but less validated
- Background task execution via Bash tool (10-minute max timeout)

---

## Agent Architecture Patterns

### Single Responsibility Principle
**Pattern**: One goal, one input, one output, one handoff rule per agent

Example frontmatter:
```yaml
---
name: spec-tester
description: Writes and executes comprehensive test suites for validated specifications
model: haiku
tools: [Read, Write, Edit, Bash, Grep, Glob]
---
```

- Average 3.4 components per plugin in successful implementations
- Clear role boundaries prevent context pollution
- **Example**: [wshobson/agents](https://github.com/wshobson/agents) - 85 agents across 63 plugins

### Progressive Disclosure
**Pattern**: Three-tier architecture for token efficiency
1. **Metadata** (always loaded): name, description, tool list
2. **Instructions** (on-demand): system prompt, workflow steps
3. **Resources** (as-needed): examples, templates, schemas

- Minimal token usage through strategic loading
- Enables large agent libraries without context bloat
- **Example**: [wshobson/agents](https://github.com/wshobson/agents)

### Hybrid Model Orchestration
**Pattern**: Strategic model selection based on task complexity
- **Haiku**: Fast deterministic tasks, execution, data processing
- **Sonnet**: Planning, review, complex reasoning, validation
- **Typical workflow**: Sonnet (plan) → Haiku (execute) → Sonnet (review)
- 47 Haiku : 97 Sonnet agent ratio in production systems

### Hub-and-Spoke Coordination
**Pattern**: Central orchestrator routes tasks to specialized workers
- Prevents peer-to-peer communication chaos
- Orchestrator manages task decomposition and result synthesis
- Workers maintain isolated contexts for separation of concerns
- **Example**: [vanzan01/claude-code-sub-agent-collective](https://github.com/vanzan01/claude-code-sub-agent-collective)

### Quality Gate Pattern
**Pattern**: Multi-phase workflow with validation thresholds
- Hooks with Exit Code 2 block progression until standards met
- LLM-as-judge pattern for output evaluation
- Structured artifacts for inter-phase communication
- **Example**: [zhsama/claude-sub-agent](https://github.com/zhsama/claude-sub-agent)

### Test-Driven Agent Development
**Pattern**: RED-GREEN-REFACTOR cycle
1. Write failing test defining desired behavior
2. Run test to confirm failure
3. Write minimal code to pass test
4. Run test to confirm success
5. Refactor while keeping tests green

- Agents write tests before implementation
- Break work into 2-5 minute tasks
- Mandatory protocol enforced via skills/hooks
- **Example**: [obra/superpowers](https://github.com/obra/superpowers)

### ReAct Loop (Reasoning + Acting)
**Pattern**: Thought → Action → Observation → Thought → Action...
- Agent alternates between reasoning and tool use
- Uses observations to decide next steps
- Enables dynamic response to complex queries
- **Reference**: [ReAct Pattern](https://arxiv.org/abs/2210.03629)

### Plan-and-Execute
**Pattern**: Separate planning from execution
1. **Planner Agent**: Creates task decomposition
2. **Executor Agents**: Carry out individual steps
3. **Coordinator**: Tracks progress, handles errors

- Modularity enables easier debugging
- Clear separation between strategy and tactics

---

## Performance Optimization

### Parallel Tool Execution
**Critical**: Batch independent operations in single message

**Recommended Batching Limits**:
- WebSearch/WebFetch: 3-5 calls per message
- Grep searches: 5-7 patterns
- Read operations: 5 files
- Glob patterns: 3-5 patterns per message

**Agent Prompt Instructions**:
```markdown
CRITICAL: Use parallel execution for independent operations.
Execute multiple WebSearch/Grep/Read calls in a SINGLE message when no dependencies exist.
DO NOT execute tools sequentially when they can run in parallel.
```

**Performance Impact**:
- 40-60% speedup through intelligent tool batching
- Reduced API call overhead
- Lower context switching costs

### Model Selection Strategy
- **Haiku**: Research agents, indexing, data gathering (faster execution)
- **Sonnet**: Complex reasoning, synthesis, validation
- **Opus**: Maximum capability for critical decisions

### Just-in-Time Loading
- Maintain lightweight identifiers, not full data
- Dynamically load data using tools only when needed
- Avoid context bloat with premature data loading
- **Reference**: [Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

### Context Caching
- Schema compilation cached for 24 hours
- First compilation has higher latency
- Repeated information benefits from caching
- Primary optimization for long context scenarios

### Concurrent Agent Deployment
- Maximum ~10 parallel subagents per workflow
- Git worktrees for parallel development across branches
- Container-based isolation for true parallel execution
- Wave-based deployment (1-5 agents per wave) prevents saturation

---

## Context Engineering

### Four Core Strategies

**1. Writing Context (External Memory)**
- CLAUDE.md files for persistent project knowledge
- Note-taking files (NOTES.md) to track progress
- Zettelkasten-inspired atomic notes (one concept per note)
- SQLite databases for multi-agent memory systems
- **Example**: [ruvnet/claude-flow](https://github.com/ruvnet/claude-flow) - 12-table memory system

**2. Selecting Context (Retrieval)**
- RAG patterns for dynamic information retrieval
- Vector databases for semantic search
- Tool description filtering (fetch only relevant tools)
- Embeddings for memory indexing
- Information positioning: critical info at beginning or end of context

**3. Compressing Context (Summarization)**
- Progressive summarization across iterations
- Hierarchical processing via sub-agents
- Dynamic trimming of redundant tokens
- Workflow compaction at checkpoints

**4. Isolating Context (Sub-agents)**
- Separate context windows prevent pollution
- Enable parallelization of tasks
- Fresh agent spawning when context limits reached
- Handoff contracts preserve necessary context

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
- Verbose, explicit descriptions of parameters

**Structured Instructions**:
```markdown
# Agent Role
[Clear, specific role definition]

## Core Responsibilities
1. [Specific responsibility]
2. [Specific responsibility]
3. [Specific responsibility]

## Workflow
1. [Concrete step with tool usage]
2. [Concrete step with tool usage]
3. [Concrete step with tool usage]

## Output Format
[Exact format with examples]

## Quality Criteria
- [Specific, measurable criterion]
- [Specific, measurable criterion]
```

### Token Efficiency Techniques

**Markdown vs JSON**:
- Markdown ~15% more token-efficient than JSON
- Model preferences vary (GPT-4 favors Markdown, GPT-3.5-turbo prefers JSON)
- Use JSON Schema for strict validation needs
- Use Markdown for human readability and efficiency

**Progressive Disclosure**:
- Load metadata first (always)
- Load instructions on-demand
- Load resources as-needed
- Minimal token usage enables large agent libraries

**AGENTS.md/CLAUDE.md Pattern**:
- Lightweight, project-specific instruction format
- Quick parsing without verbose documentation
- Dos/don'ts with version-specific instructions
- File-scoped commands (type check, format, lint per file)
- tool agnostic verions: AGENTS.md
- claude code version: CLAUDE.md

---

## Multi-Agent Coordination

### Coordination Architectures

**Hub-and-Spoke** (Most Common):
- Central orchestrator routes work to specialists
- Prevents peer-to-peer communication chaos
- Orchestrator handles task decomposition and synthesis
- **Example**: [vanzan01/claude-code-sub-agent-collective](https://github.com/vanzan01/claude-code-sub-agent-collective)

**Sequential Pipeline**:
- Agents handle distinct SDLC phases
- Clear handoffs between phases
- Quality gates validate completion
- **Example**: [zhsama/claude-sub-agent](https://github.com/zhsama/claude-sub-agent)

**Parallel Coordination**:
- Channel-based communication
- Git worktree isolation for concurrent work
- WebSocket-based protocols for real-time communication
- **Example**: [nwiizo/ccswarm](https://github.com/nwiizo/ccswarm)

**Swarm Intelligence**:
- Mesh topology with distributed coordination
- SQLite-based cross-session memory
- Natural language triggers for skill activation
- **Example**: [ruvnet/claude-flow](https://github.com/ruvnet/claude-flow)

### State Management Patterns

**File-Based State**:
- JSON artifacts for inter-agent communication
- Lock files prevent work conflicts
- Queue systems for task distribution
- Work registries track active/completed tasks
- **Example**: [Dicklesworthstone/claude_code_agent_farm](https://github.com/Dicklesworthstone/claude_code_agent_farm)

**Database-Backed Memory**:
- SQLite with WAL mode for concurrent access
- 12 specialized tables (memory_store, sessions, agents, tasks, etc.)
- Cross-agent coordination via shared state updates
- Event logging for debugging and analysis
- **Example**: [ruvnet/claude-flow](https://github.com/ruvnet/claude-flow)

**Hook-Based Coordination**:
- SubagentStop hooks enable handoffs
- Print next steps to STDOUT for parent visibility
- Exit Code 2 blocks completion for quality gates
- Prompt-based hooks for context-aware decisions

### Handoff Protocols

**Explicit Contracts**:
- Define input format for receiving agent
- Define output format for sending agent
- Specify success criteria
- Document handoff trigger conditions

**Context Bridging**:
- File-based state transfer (workaround for isolated contexts)
- Structured artifacts (JSON, Markdown) for data exchange
- Hooks write context files for parent access
- Memory systems maintain cross-agent state

**Quality Validation**:
- LLM-as-judge evaluation of agent outputs
- Quantitative trust scoring (0-1 scale)
- Validation thresholds (typically 80-95%)
- Checkpoint verification before handoff

---

## Quality Assurance Patterns

### Validation Gates

**Multi-Tier Validation**:
- Planning Phase: 95% threshold
- Development Phase: 80% threshold
- Validation Phase: 85% threshold
- **Example**: [zhsama/claude-sub-agent](https://github.com/zhsama/claude-sub-agent)

**Hook-Based Enforcement**:
- Exit Code 2 blocks progression
- Shows error message to agent
- Enables retry/refinement loop
- **Reference**: [Hooks Guide](https://code.claude.com/docs/en/hooks-guide)

**LLM-as-Judge Pattern**:
- Secondary LLM evaluates outputs
- End-state evaluation vs turn-by-turn
- Accuracy and completeness metrics
- Reduces compounding errors

### Testing Approaches

**Test-Driven Development**:
- Write tests before implementation
- Confirm test failure before coding
- Implement to pass tests
- Verify no overfitting to test cases
- **Example**: [obra/superpowers](https://github.com/obra/superpowers)

**Unit Testing (Agents)**:
- Step-level testing (isolate specific actions)
- Tool selection accuracy validation
- Component function independence checks
- Synthetic edge-case testing

**Integration Testing**:
- Multi-step reasoning success rate
- Session-level outcome verification
- Trajectory quality assessment
- Flow coverage testing

**Robustness Testing**:
- Ambiguous input handling
- Edge case coverage
- Adversarial example testing
- Error recovery validation

### Continuous Monitoring

**Observability Systems**:
- Hook-based event tracking (PreToolUse, PostToolUse)
- SQLite event logging
- WebSocket real-time visualization
- Session-based filtering and color coding
- **Example**: [disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability)

**Performance Metrics**:
- Task success rate/accuracy
- Response time/latency
- Throughput measurements
- Containment and completion rates
- Tool selection accuracy

**Regression Detection**:
- Track agent behavior over time
- Identify performance drift
- Automated regression tests
- Continuous evaluation loops

---

## Anti-Patterns to Avoid

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
- DO: Use CLAUDE.md, note-taking files, databases
- **Impact**: Loss of continuity across sessions

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

**❌ Peer-to-Peer Agent Communication**:
- DON'T: Allow arbitrary agent-to-agent messaging
- DO: Hub-and-spoke with central orchestrator
- **Impact**: Communication chaos, lost messages

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

### Quality Assurance

**❌ No Validation Gates**:
- DON'T: Allow unchecked progression between workflow phases
- DO: Implement quality thresholds with hook-based enforcement
- **Impact**: Compounding errors, poor output quality

**❌ Marking Tasks Complete When Blocked**:
- DON'T: Mark task "completed" when errors/blockers exist
- DO: Keep "in_progress", create new task for blocker
- **Impact**: False progress reporting, hidden issues

**❌ Skipping Tests**:
- DON'T: Write implementation before tests
- DO: RED-GREEN-REFACTOR cycle
- **Impact**: Brittle code, unclear requirements

### Workflow Design

**❌ Premature Complexity**:
- DON'T: Start with sophisticated multi-agent orchestration
- DO: Begin simple, add complexity with demonstrated benefit
- **Impact**: Over-engineering, maintenance burden

**❌ No Error Handling**:
- DON'T: Assume all operations succeed
- DO: Implement retry mechanisms, graceful degradation
- **Impact**: Fragile workflows, poor user experience

**❌ Ignoring Handoff Contracts**:
- DON'T: Implicit assumptions about data formats between agents
- DO: Explicit input/output specifications, validation
- **Impact**: Integration failures, data loss

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

### Example Repositories
- [obra/superpowers](https://github.com/obra/superpowers) - TDD workflows, skill-based composition
- [wshobson/agents](https://github.com/wshobson/agents) - 85 agents, progressive disclosure, hybrid models
- [zhsama/claude-sub-agent](https://github.com/zhsama/claude-sub-agent) - Quality gates, multi-phase workflows
- [ruvnet/claude-flow](https://github.com/ruvnet/claude-flow) - Swarm intelligence, SQLite memory
- [nwiizo/ccswarm](https://github.com/nwiizo/ccswarm) - Rust implementation, channel-based coordination
- [vanzan01/claude-code-sub-agent-collective](https://github.com/vanzan01/claude-code-sub-agent-collective) - Hub-and-spoke, context engineering
- [disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability) - Real-time monitoring
- [Dicklesworthstone/claude_code_agent_farm](https://github.com/Dicklesworthstone/claude_code_agent_farm) - 50 parallel agents, file-based coordination

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

---

**Document Metadata**
- Created: 2025-12-06
- Sources: 15 research documents, 20+ GitHub repositories, 30+ official documentation pages
- Coverage: Features, limitations, patterns, optimization, context engineering, coordination, QA, anti-patterns
- Format: AI-optimized (structured, scannable, with examples and references)
