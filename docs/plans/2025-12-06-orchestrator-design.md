# AI-Assisted Development Orchestrator Design

## Design Date
2025-12-06

## Problem Statement

The ai-assisted-development plugin provides specialized research agents (web-research, codebase-research, context-indexing, lessons-learned) but lacks coordination. Users must manually determine which agents to invoke, in what order, and when the work is complete. This prevents the system from orchestrating multi-step workflows that follow software development best practices.

## Solution Overview

Build a minimal orchestration agent that executes a control loop: evaluate state → check completion → determine next action → execute → repeat. The orchestrator enforces process discipline (understand before acting, define completion criteria) while delegating specialized work to subagents.

## Design Principles

1. **Simple orchestrator, complex agents** - Keep orchestration logic minimal; push complexity into specialized agents and quality gates
2. **Incremental expansion** - Start with research orchestration; expand to full SDLC later
3. **Process enforcement over intelligence** - Orchestrator enforces methodology, not creative problem-solving
4. **Fail fast** - Stop on errors; let user decide next steps
5. **Explicit over implicit** - Hardcode agent registry and process rules; avoid generalization complexity

## Architecture

### Components

**Orchestrator Agent** (`ai-assisted-development:orchestrator`)
- Single persistent agent running evaluation loop
- Model: Sonnet (requires reasoning capability)
- Invoked via `/ai-assisted-development:start` command

**Slash Command** (`/ai-assisted-development:start`)
- Entry point for orchestrated workflows
- Passes user task description to orchestrator
- Explicit invocation (no auto-activation)

**TodoWrite State Management**
- Primary state tracking mechanism
- Todo list represents workflow steps
- Provides user visibility and checkpoint/resume capability

**Hardcoded Agent Registry**
- Explicit list in orchestrator prompt
- Four agents: web-research, codebase-research, context-indexing, lessons-learned
- Updated manually as agents are added

### Control Flow

```
User: /ai-assisted-development:start <task>
  ↓
Command spawns orchestrator agent with task description
  ↓
Orchestrator loop:
  1. Evaluate current state (TodoWrite, user request, subagent outputs)
  2. Check: Done? → Yes: Report results and exit
  3. Determine next action (apply process gates + reasoning)
  4. Execute action (spawn subagent, ask user, etc.)
  5. Update TodoWrite
  6. Repeat from step 1
```

### Process Gates (v1 - Minimal)

The orchestrator enforces two core rules:

1. **Understand before acting** - Cannot spawn work agents until information needs are clear
2. **Define completion criteria** - Must establish "done" state before starting work

These gates encode basic software development discipline. Additional gates (plan before implementing, review after coding, tests must pass) come later when we add planning and implementation agents.

### Decision-Making Model

**Hybrid: Rules + Reasoning**

Explicit rules define the process:
- Must understand requirements first
- Must define completion criteria
- Follow sequential flow: gather → synthesize → report

Within those constraints, orchestrator reasons about specific actions:
- What information is missing?
- Which agent handles this need?
- Is gathered information sufficient?

This keeps decision logic simple while allowing flexibility in action selection.

## State Management

### TodoWrite as Primary State

The todo list IS the orchestration state:
- Tasks represent both process steps and delegated work
- Status tracking: pending, in_progress, completed
- User sees orchestrator reasoning in real-time
- Natural checkpoint/resume capability

Example todo list:
```
- Understanding user requirements (in_progress)
- Researching best practices via web-research (pending)
- Synthesizing research findings (pending)
- Reporting results to user (pending)
```

### Agent Communication

Subagents write outputs to files (`docs/research/web/*.md`, etc.). The orchestrator:
1. Spawns subagent via Task tool
2. Receives completion message (includes file path)
3. Reads output file if needed for next decision
4. Updates TodoWrite
5. Continues loop

### What We're NOT Building (v1)

- No file-based orchestrator state (`.orchestrator/state.json`)
- No cross-session persistence
- No structured handoff contracts between agents
- No parallel agent execution

We defer these until we hit limitations of TodoWrite + subagent file outputs.

## Implementation

### File Structure

```
ai-assisted-development/
├── agents/
│   ├── orchestrator.md          # New: orchestrator agent
│   ├── web-research.md           # Existing
│   ├── codebase-research.md      # Existing
│   ├── context-indexing.md       # Existing
│   └── lessons-learned.md        # Existing
├── commands/
│   └── start.md                  # New: /start command
└── .claude-plugin/
    └── plugin.json               # Update: register new agent
```

### Orchestrator Agent Prompt (Outline)

```markdown
# AI-Assisted Development Orchestrator

You manage research and development workflows through a control loop.

## Your Role
Evaluate state → check completion → determine action → execute → repeat.

## Process Rules (MUST Follow)
1. Understand requirements before spawning work agents
2. Define clear completion criteria upfront
3. Fail fast on errors - report to user, don't retry

## Available Agents
- ai-assisted-development:web-research - Research web sources, documentation, best practices
- ai-assisted-development:codebase-research - Analyze external repositories
- ai-assisted-development:context-indexing - Index local project context
- ai-assisted-development:lessons-learned - Extract project learnings

## State Management
- Use TodoWrite to track workflow steps
- Mark tasks in_progress before starting
- Mark completed immediately after finishing
- Read subagent output files when needed

## Control Loop
[Detailed instructions for evaluation and decision-making]

## Failure Handling
Stop immediately on errors. Report to user. Do not retry.
```

### Start Command (Outline)

```markdown
# Start AI-Assisted Development Workflow

Launch the orchestrator with the user's task description.

Use the Task tool to invoke:
- subagent_type: ai-assisted-development:orchestrator
- prompt: User's task description
- model: sonnet
```

## Error Handling

**Fail Fast Strategy**
- Subagent reports error → orchestrator stops
- Unexpected results → orchestrator stops
- Cannot determine next action → orchestrator stops

All failures report to user. No retry logic. No graceful degradation.

This keeps the orchestrator simple and gives users control when things go wrong.

## Evolution Path

### Near-Term Extensions
1. **Planning agents** - Requirement analysis, task breakdown, implementation planning
2. **Interactive quality gates** - User approval at checkpoints
3. **File-based state** - Cross-session persistence, handoff contracts
4. **Parallel coordination** - Multiple agents working simultaneously

### Process Gate Evolution
As implementation agents are added:
- "Plan before implementing" gate
- "Code review after implementation" gate
- "Tests must pass" validation gate
- TDD enforcement (red-green-refactor)

### From Adaptive Loop to Hub-and-Spoke
When patterns emerge:
- Add explicit routing rules for common scenarios
- Build agent capability taxonomy
- Implement task decomposition
- Keep core loop simple

## Success Criteria

This design succeeds if:
1. Orchestrator handles simple research workflows: question → gather → synthesize → report
2. Process gates enforce basic development discipline
3. Architecture supports expansion to full SDLC orchestration
4. Orchestrator remains simple as system grows complex

## Non-Goals (v1)

- Automatic activation (hooks, always-on)
- Retry and resilience logic
- Parallel agent execution
- Cross-session persistence
- Complex routing optimizations
- Plugin/system interoperability
- Interactive approval workflows

## References

Research that informed this design:
- `docs/research/web/2025-12-05-multi-agent-orchestration-claude-code.md` - Hub-and-spoke patterns, quality gates, state management
- `docs/research/web/2025-12-06-todowrite-checkpointing.md` - TodoWrite usage patterns, checkpointing strategies
- `docs/research/codebase/2025-12-05-superpowers.md` - Process enforcement, subagent coordination
- `docs/research/codebase/2025-12-05-agents.md` - Plugin architecture, agent composition

Key patterns adopted:
- Hub-and-spoke coordination (simplified to adaptive loop)
- TodoWrite for state tracking
- Process gate enforcement from obra/superpowers
- Fail-fast error handling
- Hardcoded agent registry (avoiding generalization complexity)
