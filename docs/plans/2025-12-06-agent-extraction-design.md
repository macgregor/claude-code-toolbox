# Agent Extraction Design: Synthesis and Workflow Planner

## Design Date
2025-12-06

## Problem Statement

The orchestrator agent (482 lines) does too much. It performs synthesis inline, contains 40+ lines of decision logic for agent selection, and mixes coordination with specialized work. This violates the "simple orchestrator, complex agents" principle and makes the orchestrator harder to maintain and extend.

## Solution Overview

Extract two capabilities into dedicated subagents:

**Synthesis Agent** - Compresses multiple research reports into focused insights relevant to the user's objective. Takes file paths via prompt, produces synthesis report at `.orchestrator/synthesis/YYYY-MM-DD-<topic>-<description>.md`.

**Workflow Planner Agent** - Determines next action based on current state. Takes workflow state via prompt, returns structured JSON decision specifying which agent to invoke next.

**Result**: Orchestrator reduces by ~50+ lines, focuses on control loop + process gates + TodoWrite state + delegation.

## Synthesis Agent Design

### Agent Specification
- **File**: `ai-assisted-development/agents/synthesis.md`
- **Model**: haiku (fast execution for compression task)
- **Tools**: Read, Write, Edit, Bash
- **Pattern**: Template-copy-fill-validate (like web-research)
- **No command**: Orchestrator-only agent (users never invoke directly)

### Workflow
1. Copy template from `ai-assisted-development/templates/synthesis-report.md`
2. Determine target path: `.orchestrator/synthesis/YYYY-MM-DD-<topic>-<description>.md`
3. Read all input files specified in prompt
4. Filter insights through user's objective (extract what's relevant to their problem)
5. Identify cross-cutting patterns, conflicts, gaps
6. Generate description slug from sources (e.g., "web-and-codebase", "three-repo-analysis")
7. Fill template placeholders via Edit tool
8. Validate via `scripts/validate-synthesis-report.sh`
9. Report file path to orchestrator

### Template Structure
```markdown
# Synthesis: [REQUIRED: Topic]

## User Objective
[REQUIRED: The specific problem/question being addressed]

## Input Sources
[REQUIRED: List of files analyzed with paths]

## Key Patterns Identified
[REQUIRED: Cross-cutting patterns relevant to user's objective]

## Conflicting Information
[REQUIRED: Contradictions, gaps, or missing information]

## Recommendations
[REQUIRED: What to do next based on synthesis and user's objective]
```

### Purpose
Context compression between workflow steps. Synthesis filters multiple research reports through the lens of the user's specific problem, extracting high-signal insights so subsequent agents don't wade through raw material.

### Invocation Example
```
Task(
  subagent_type="ai-assisted-development:synthesis",
  prompt="User objective: Research authentication best practices for microservices

Synthesize findings from these reports:
- docs/research/web/2025-12-06-auth-patterns.md
- docs/research/codebase/2025-12-06-netflix-auth-impl.md

Focus on identifying patterns, conflicts, and recommendations relevant to the user's specific objective.",
  model="haiku",
  description="Synthesize auth research"
)
```

### Output Location
- Directory: `.orchestrator/synthesis/` (gitignored)
- Filename: `YYYY-MM-DD-<topic>-<auto-description>.md`
- Ephemeral working artifacts (not committed to git)
- Timestamp ensures uniqueness across multiple synthesis runs

### Validation Script
Create `ai-assisted-development/scripts/validate-synthesis-report.sh`:
- Check for unfilled `[REQUIRED:]` placeholders
- Verify all sections present
- Confirm file path matches `.orchestrator/synthesis/YYYY-MM-DD-*.md` pattern
- Exit 0 on success, non-zero with errors on failure

## Workflow Planner Agent Design

### Agent Specification
- **File**: `ai-assisted-development/agents/workflow-planner.md`
- **Model**: sonnet (requires reasoning for decision-making)
- **Tools**: Read, AskUserQuestion
- **Pattern**: Prompt-based with JSON schema (no template)
- **No command**: Orchestrator-only agent (internal decision mechanism)

### Workflow
1. Receive current state in prompt (user goal, completed work, available files, TodoWrite status)
2. Evaluate what's needed next
3. Apply process gates (requirements understood, completion criteria defined)
4. Determine next action type
5. Return structured JSON decision in final message

### JSON Schema
Agent prompt includes schema definition and examples:

```json
{
  "action": "synthesize" | "research" | "index" | "report" | "clarify",
  "agent": "ai-assisted-development:synthesis" | "ai-assisted-development:web-research" | ...,
  "inputs": ["file1.md", "file2.md"] | {"topic": "..."} | {},
  "rationale": "Explanation of why this action is needed"
}
```

### Example Decisions

**Synthesis needed:**
```json
{
  "action": "synthesize",
  "agent": "ai-assisted-development:synthesis",
  "inputs": ["docs/research/web/2025-12-06-auth.md", "docs/research/codebase/2025-12-06-auth-impl.md"],
  "rationale": "Need to compress findings before deciding if more research needed"
}
```

**Research needed:**
```json
{
  "action": "research",
  "agent": "ai-assisted-development:web-research",
  "inputs": {"topic": "JWT token security best practices"},
  "rationale": "No external information gathered yet on auth token handling"
}
```

**Ready to report:**
```json
{
  "action": "report",
  "agent": null,
  "inputs": {},
  "rationale": "All information gathered and synthesized, ready to report to user"
}
```

### Purpose
Extracts decision logic from orchestrator. Planner analyzes current workflow state and determines the next action. Orchestrator becomes execution engine - it runs the loop, enforces gates, maintains state, and delegates to whatever agent the planner specifies.

### Integration
Orchestrator parses JSON from planner's completion message. If JSON parsing fails, orchestrator fails fast (reports error to user). No retry logic - planner must return valid JSON.

## Orchestrator Integration

### Control Loop Changes

**Before** (current):
```
Loop:
1. Evaluate state
2. Check completion → if done, report & exit
3. Determine Action → inline decision logic (40+ lines)
4. Execute → spawn agent OR synthesize inline OR ask user
5. Update TodoWrite
6. Repeat
```

**After** (with planner + synthesis):
```
Loop:
1. Evaluate state
2. Check completion → if done, report & exit
3. Get Decision → spawn planner, receive JSON
4. Execute → delegate based on planner's decision
5. Update TodoWrite
6. Repeat
```

### Removed from Orchestrator
- Agent selection decision tree (~20 lines, section "Agent Selection Guidelines")
- Common decision patterns (~20 lines, section "Common decision patterns")
- Inline synthesis logic (~10 lines, "If synthesizing" section)
- **Total reduction: ~50 lines**

### New Orchestrator Responsibilities

**Pass context to planner:**
- User's original objective
- Current TodoWrite state
- Completed work (which agents ran, what files produced)
- Available files for synthesis

**Parse planner's JSON:**
- Read planner's final message
- Parse JSON (fail fast if malformed)
- Extract action, agent, inputs, rationale

**Execute planner's decision:**
- If action = "synthesize" → spawn synthesis with user objective + file paths
- If action = "research" → spawn specified research agent (web-research, codebase-research, etc.)
- If action = "index" → spawn context-indexing agent
- If action = "report" → synthesize final results and report to user
- If action = "clarify" → use AskUserQuestion
- If JSON parsing fails → report error to user, stop

**Maintain agent registry:**
Orchestrator still lists available agents (for reference in prompt), but decision logic lives in planner.

### Error Handling
- JSON parsing errors: fail fast, report to user
- Planner returns malformed decision: fail fast
- Subagent errors: existing fail-fast behavior unchanged

## Implementation Details

### File Structure
```
ai-assisted-development/
├── agents/
│   ├── orchestrator.md              # Update: simplified control loop
│   ├── synthesis.md                 # New: synthesis agent
│   ├── workflow-planner.md          # New: planner agent
│   ├── web-research.md              # Existing
│   ├── codebase-research.md         # Existing
│   ├── context-indexing.md          # Existing
│   └── lessons-learned.md           # Existing
├── templates/
│   ├── synthesis-report.md          # New: synthesis template
│   ├── web-research-report.md       # Existing
│   └── codebase-analysis-report.md  # Existing
├── scripts/
│   ├── validate-synthesis-report.sh # New: synthesis validation
│   ├── validate-research-report.sh  # Existing
│   └── validate-codebase-report.sh  # Existing
└── .claude-plugin/
    └── plugin.json                  # Update: register new agents

.orchestrator/                       # New directory (gitignored)
└── synthesis/                       # Synthesis outputs
    └── YYYY-MM-DD-<topic>-<desc>.md

.gitignore                           # Add: .orchestrator/
```

### Implementation Order
1. Create synthesis template (`templates/synthesis-report.md`)
2. Create synthesis validation script (`scripts/validate-synthesis-report.sh`)
3. Implement synthesis agent (`agents/synthesis.md`)
4. Implement workflow planner agent (`agents/workflow-planner.md`)
5. Update orchestrator agent (simplify control loop, add planner integration)
6. Update `.gitignore` (add `.orchestrator/`)
7. Update `plugin.json` (register synthesis + planner agents)
8. Test with simple orchestrated workflow

### Testing Strategy

**Unit Tests:**
- Synthesis: Invoke with 2-3 research reports, verify output structure
- Planner: Provide various state scenarios, verify JSON responses

**Integration Tests:**
- Full workflow: User request → research → synthesize → report
- Multi-synthesis: Research → synthesize → more research → synthesize again → report
- Error cases: Malformed JSON, missing files, validation failures

### Plugin Configuration
Update `ai-assisted-development/.claude-plugin/plugin.json`:
```json
{
  "agents": [
    "./agents/orchestrator.md",
    "./agents/synthesis.md",
    "./agents/workflow-planner.md",
    "./agents/web-research.md",
    "./agents/codebase-research.md",
    "./agents/context-indexing.md",
    "./agents/lessons-learned.md"
  ]
}
```

## Success Criteria

**Orchestrator Simplification:**
- Orchestrator reduced by 50+ lines (from 482 lines)
- Decision logic removed (delegated to planner)
- Synthesis logic removed (delegated to synthesis agent)
- Orchestrator focuses on: control loop + process gates + TodoWrite + delegation

**Synthesis Agent:**
- Produces valid synthesis reports following template structure
- Filters insights through user's objective (not generic summarization)
- Generates meaningful auto-descriptions for filenames
- Validation catches unfilled placeholders

**Workflow Planner:**
- Returns parseable JSON decisions
- Decisions are actionable (orchestrator can execute them)
- Rationale field provides debugging visibility
- Handles various workflow states (initial, mid-research, ready-to-report)

**Integration:**
- Full orchestrated workflow completes without errors
- Synthesis outputs persist in `.orchestrator/synthesis/`
- Multiple synthesis runs don't conflict (unique filenames)
- TodoWrite shows clear progression through workflow

## Non-Goals (v1)

- Cross-session persistence (no state files beyond synthesis outputs)
- Concurrent orchestrator runs (flat directory structure sufficient)
- User-facing commands for synthesis/planner (orchestrator-only agents)
- Parallel agent execution (sequential workflow maintained)
- Adaptive re-planning mid-workflow (planner consulted each iteration but doesn't revise plans)

## References

Research informing this design:
- `docs/research/web/2025-12-05-multi-agent-orchestration-claude-code.md` - File-based state, artifact communication patterns
- `docs/research/web/2025-12-06-todowrite-checkpointing.md` - TodoWrite state management
- `docs/research/web/2025-12-05-context-engineering-ai-agents.md` - Context compression, structured outputs, progressive disclosure
- `docs/plans/2025-12-06-orchestrator-design.md` - Original orchestrator architecture
- `docs/agent-architecture.md` - Two-layer agent pattern, template-copy-fill-validate workflow

Key patterns adopted:
- Structured JSON outputs for reliability (context engineering research)
- File-based artifact communication (zhsama/claude-sub-agent)
- Progressive summarization for context management (yzyydev)
- Context compression principle (Anthropic: "smallest set of high-signal tokens")
