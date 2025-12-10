# Agent Orchestration Patterns

**Purpose**: Custom multi-agent patterns and implementations built on Claude Code platform
**Audience**: AI agents and developers building sophisticated agent workflows
**Updated**: 2025-12-10

**Note**: These are community-developed patterns, not Claude Code platform features. See `claude-code-reference.md` for platform features.

---

## Table of Contents

1. [Architecture Patterns](#architecture-patterns)
2. [Coordination Architectures](#coordination-architectures)
3. [State Management](#state-management)
4. [Quality Assurance](#quality-assurance)
5. [Example Repositories](#example-repositories)

---

## Architecture Patterns

### Single Responsibility Principle

**Pattern**: One goal, one input, one output, one handoff rule per agent

**Benefits**:
- Clear role boundaries prevent context pollution
- Easier debugging and testing
- Composable agent workflows

**Implementation**:
```yaml
---
name: spec-tester
description: Writes and executes comprehensive test suites for validated specifications
model: haiku
tools: [Read, Write, Edit, Bash, Grep, Glob]
---
```

**Observations**: Based on analysis of wshobson/agents repository: average 3.4 components per plugin across 85 agents in 63 plugins.

**Example**: [wshobson/agents](https://github.com/wshobson/agents)

---

### Progressive Disclosure

**Pattern**: Three-tier architecture for token efficiency

**Tiers**:
1. **Metadata** (always loaded): name, description, tool list
2. **Instructions** (on-demand): system prompt, workflow steps
3. **Resources** (as-needed): examples, templates, schemas

**Benefits**:
- Minimal token usage through strategic loading
- Enables large agent libraries without context bloat

**Implementation**: Organize agent markdown files with clear sections that can be selectively loaded.

**Example**: [wshobson/agents](https://github.com/wshobson/agents)

---

### Hybrid Model Orchestration

**Pattern**: Strategic model selection based on task complexity

**Model Roles**:
- **Haiku**: Fast deterministic tasks, execution, data processing
- **Sonnet**: Planning, review, complex reasoning, validation
- **Opus**: Maximum capability for critical decisions

**Typical Workflow**: Sonnet (plan) → Haiku (execute) → Sonnet (review)

**Observations**: Analysis of production systems shows 47 Haiku : 97 Sonnet agent ratio (source: community implementations).

---

### Test-Driven Agent Development

**Pattern**: RED-GREEN-REFACTOR cycle for agents writing code

**Steps**:
1. Write failing test defining desired behavior
2. Run test to confirm failure
3. Write minimal code to pass test
4. Run test to confirm success
5. Refactor while keeping tests green

**Benefits**:
- Agents write tests before implementation
- Break work into 2-5 minute tasks
- Clear success criteria

**Enforcement**: Mandatory protocol enforced via skills/hooks

**Example**: [obra/superpowers](https://github.com/obra/superpowers)

---

### ReAct Loop (Reasoning + Acting)

**Pattern**: Thought → Action → Observation → Thought → Action...

**Process**:
- Agent alternates between reasoning and tool use
- Uses observations to decide next steps
- Enables dynamic response to complex queries

**Reference**: [ReAct Pattern](https://arxiv.org/abs/2210.03629)

---

### Plan-and-Execute

**Pattern**: Separate planning from execution

**Components**:
1. **Planner Agent**: Creates task decomposition
2. **Executor Agents**: Carry out individual steps
3. **Coordinator**: Tracks progress, handles errors

**Benefits**:
- Modularity enables easier debugging
- Clear separation between strategy and tactics

---

## Coordination Architectures

### Hub-and-Spoke (Most Common)

**Architecture**: Central orchestrator routes work to specialized workers

**Components**:
- Orchestrator: Task decomposition, routing, result synthesis
- Workers: Specialized agents with isolated contexts

**Benefits**:
- Prevents peer-to-peer communication chaos
- Single point of control for workflow state
- Clear responsibility boundaries

**Implementation**: Use slash command to spawn orchestrator agent, which uses Task tool to spawn worker agents.

**Example**: [vanzan01/claude-code-sub-agent-collective](https://github.com/vanzan01/claude-code-sub-agent-collective)

---

### Sequential Pipeline

**Architecture**: Agents handle distinct SDLC phases with handoffs

**Components**:
- Phase-specific agents (planning, development, validation, deployment)
- Quality gates between phases
- File-based state transfer

**Benefits**:
- Clear handoffs between phases
- Quality validation at checkpoints
- Structured workflow progression

**Implementation**: Use SubagentStop hooks to validate outputs before triggering next phase agent.

**Example**: [zhsama/claude-sub-agent](https://github.com/zhsama/claude-sub-agent)

---

### Parallel Coordination

**Architecture**: Independent agents work concurrently on separate tasks

**Techniques**:
- Git worktree isolation for concurrent work on different branches
- Container-based isolation for true parallel execution
- Wave-based deployment (1-5 agents per wave) prevents saturation

**Benefits**:
- Faster completion for independent tasks
- Resource isolation prevents conflicts

**Limitations**: Maximum ~10 parallel subagents recommended per workflow (Claude Code platform limitation)

**Example**: [nwiizo/ccswarm](https://github.com/nwiizo/ccswarm) - channel-based communication, WebSocket protocols

---

### Swarm Intelligence

**Architecture**: Mesh topology with distributed coordination

**Components**:
- Multiple peer agents with shared state
- Cross-session memory (typically SQLite database)
- Natural language triggers for skill activation

**Benefits**:
- Distributed decision-making
- Emergent collaborative behavior
- Persistent state across sessions

**Example**: [ruvnet/claude-flow](https://github.com/ruvnet/claude-flow) - 12-table SQLite schema for memory

---

## State Management

### File-Based State

**Pattern**: JSON/Markdown artifacts for inter-agent communication

**Techniques**:
- Lock files prevent work conflicts
- Queue systems for task distribution
- Work registries track active/completed tasks

**Use Case**: Simple coordination without external dependencies

**Implementation**: Agents write state to agreed-upon files, hooks trigger subsequent agents when files appear/change.

**Example**: [Dicklesworthstone/claude_code_agent_farm](https://github.com/Dicklesworthstone/claude_code_agent_farm) - 50 parallel agents

---

### Database-Backed Memory

**Pattern**: Shared database for cross-agent, cross-session coordination

**Common Choice**: SQLite with WAL mode for concurrent access

**Schema Example** (from ruvnet/claude-flow):
- 12 specialized tables: memory_store, sessions, agents, tasks, etc.
- Cross-agent coordination via shared state updates
- Event logging for debugging and analysis

**Benefits**:
- Queryable history
- Transaction support
- Complex coordination patterns

**Tradeoffs**: Additional dependency, more complex setup

**Example**: [ruvnet/claude-flow](https://github.com/ruvnet/claude-flow)

---

### Hook-Based Coordination

**Pattern**: Use Claude Code hooks for agent lifecycle management

**Techniques**:
- SubagentStart hooks: Pre-execution validation, logging, context injection
- SubagentStop hooks: Handoffs, post-execution processing, triggering next agent
- Exit Code 2: Block completion until quality gates pass
- File-based output: Write state to files for parent visibility (STDOUT not bridged to parent context)

**Benefits**:
- Leverage platform features
- Deterministic workflow automation
- Quality gates without custom infrastructure

**Best Practice**: Use `"*"` matcher for universal lifecycle tracking, specific matchers for targeted behavior.

---

## Quality Assurance

### Validation Gates

**Multi-Tier Validation Example** (from zhsama/claude-sub-agent):
- Planning Phase: 95% threshold
- Development Phase: 80% threshold
- Validation Phase: 85% threshold

**Note**: Specific thresholds are implementation choices, not universal standards. Customize based on use case.

**Implementation**: Hook-based enforcement with Exit Code 2 blocks progression until standards met.

---

### LLM-as-Judge Pattern

**Pattern**: Secondary LLM evaluates agent outputs

**Process**:
- End-state evaluation vs turn-by-turn
- Quantitative trust scoring (0-1 scale)
- Validation thresholds (typically 80-95%)

**Benefits**:
- Accuracy and completeness metrics
- Reduces compounding errors
- Checkpoint verification before handoff

**Implementation**: SubagentStop hook invokes evaluation prompt, blocks with Exit Code 2 if below threshold.

---

### Testing Approaches

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

---

### Observability Systems

**Custom Implementations** (not Claude Code platform features):
- SQLite event logging for queryable history
- WebSocket real-time visualization
- Session-based filtering and color coding

**Platform Features Used**:
- Hook-based event tracking (PreToolUse, PostToolUse, SubagentStart, SubagentStop)
- Hook input includes session_id for per-session event correlation
- Agent lifecycle tracking via SubagentStart/SubagentStop hooks

**Example**: [disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability)

---

### Performance Metrics

**Tracking**:
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

## Example Repositories

### Production Implementations

**[obra/superpowers](https://github.com/obra/superpowers)**
- TDD workflows
- Skill-based composition
- Mandatory testing protocol

**[wshobson/agents](https://github.com/wshobson/agents)**
- 85 agents across 63 plugins
- Progressive disclosure architecture
- Hybrid model orchestration

**[zhsama/claude-sub-agent](https://github.com/zhsama/claude-sub-agent)**
- Quality gates with validation thresholds
- Multi-phase workflows
- Sequential pipeline pattern

**[ruvnet/claude-flow](https://github.com/ruvnet/claude-flow)**
- Swarm intelligence architecture
- 12-table SQLite memory system
- Cross-session coordination

**[nwiizo/ccswarm](https://github.com/nwiizo/ccswarm)**
- Rust implementation
- Channel-based coordination
- WebSocket protocols

**[vanzan01/claude-code-sub-agent-collective](https://github.com/vanzan01/claude-code-sub-agent-collective)**
- Hub-and-spoke architecture
- Context engineering techniques
- Central orchestrator pattern

**[disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability)**
- Real-time monitoring
- Hook-based event tracking
- WebSocket visualization

**[Dicklesworthstone/claude_code_agent_farm](https://github.com/Dicklesworthstone/claude_code_agent_farm)**
- 50 parallel agents
- File-based coordination
- Work queue management

---

## Anti-Patterns

### Coordination

**❌ Peer-to-Peer Agent Communication**:
- DON'T: Allow arbitrary agent-to-agent messaging
- DO: Hub-and-spoke with central orchestrator
- **Impact**: Communication chaos, lost messages

**❌ Ignoring Handoff Contracts**:
- DON'T: Implicit assumptions about data formats between agents
- DO: Explicit input/output specifications, validation
- **Impact**: Integration failures, data loss

---

### Quality

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

---

### Workflow Design

**❌ Premature Complexity**:
- DON'T: Start with sophisticated multi-agent orchestration
- DO: Begin simple, add complexity with demonstrated benefit
- **Impact**: Over-engineering, maintenance burden

**❌ No Error Handling**:
- DON'T: Assume all operations succeed
- DO: Implement retry mechanisms, graceful degradation
- **Impact**: Fragile workflows, poor user experience

---

## Related Resources

See `claude-code-reference.md` for Claude Code platform features and limitations.

See research documents in `docs/research/web/` for deeper analysis of specific topics.
