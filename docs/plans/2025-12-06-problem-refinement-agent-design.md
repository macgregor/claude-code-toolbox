# Problem Refinement Agent Design

## Overview

Refines rough problem statements through iterative questioning and synthesis until autonomous AI agents can execute them.

## Architecture

### Components

- **Command** (`/refine-problem`): Orchestrates the refinement loop - globs research, spawns synthesis, spawns refinement agent, asks user questions, manages iteration
- **Synthesis Agent**: Compresses research reports filtered by problem relevance
- **Refinement Agent**: Reads synthesis + problem doc, returns questions/research suggestions
- **Artifact** (`docs/plans/<problem-name>-refinement.md`): Mutable problem definition with refinement log

### Why Command Orchestration (Not Skill)

Research (.orchestrator/synthesis/2025-12-06-orchestrator-control-loop-five-sources.md) supports command orchestration:
- Agents fail to reliably invoke skills
- Commands enforce workflow externally
- Commands spawn agents; agents cannot (max depth = 1)
- Successful systems use commands/scripts to orchestrate agent workers

## Flow

### Every Iteration

1. User: `/refine-problem "build a caching system"` (or `/refine-problem` to continue)
2. Command globs `docs/research/**/*.md` for all available research
3. Command spawns synthesis agent with: problem statement + all research file paths
4. Command spawns refinement agent with: problem statement + synthesis report path + existing refinement doc path (if continuing)
5. Agent returns: `{questions: [...], research_suggestions: [...], ready: false}`
6. Command uses AskUserQuestion to ask questions, appends answers to refinement doc
7. If research suggested: AskUserQuestion "Spawn researchers?" → spawn web-research/codebase-research agents
8. AskUserQuestion "Continue refinement?" → if yes, goto step 2

### Command Logic (Detailed)

```
1. Parse args:
   - If args provided: new refinement (initial problem = args)

   - If no args:
     a. Glob docs/plans/*-refinement.md
     b. If no refinements found:
        - AskUserQuestion: "What problem do you want to refine?" (open-ended)
        - Use answer as initial problem, proceed as new refinement

     c. If refinements found:
        - Extract problem names from filenames
        - AskUserQuestion: "What would you like to do?"
          Options:
          - "Continue refining: <problem-1>"
          - "Continue refining: <problem-2>"
          - ...
          - "Start new refinement"
        - If "Start new": AskUserQuestion for problem statement
        - If continue: use selected doc path

2. TodoWrite (create all todos upfront):
   - "Synthesize existing research" (pending)
   - "Analyze problem and identify gaps" (pending)
   - "Gather user clarifications" (pending)
   - "Update problem definition" (pending)

3. Mark "Synthesize existing research" → in_progress
   Glob docs/research/**/*.md
   Spawn synthesis agent with problem + all research paths
   Mark "Synthesize existing research" → completed

4. Mark "Analyze problem and identify gaps" → in_progress
   Spawn refinement agent
   Parse JSON response
   Mark "Analyze problem and identify gaps" → completed

5. If ready == true:
   - Mark all todos completed
   - Display final doc path and next steps
   - Exit

6. Mark "Gather user clarifications" → in_progress
   For each question:
     - If options provided: AskUserQuestion with multiple choice
     - If options empty: AskUserQuestion open-ended
   Mark "Gather user clarifications" → completed

7. Mark "Update problem definition" → in_progress
   Write answers to refinement doc
   Mark "Update problem definition" → completed

8. If research_suggestions exist:
   - AskUserQuestion: "Spawn research agents?" (show suggestions with rationale, multi-select)
   - For selected: spawn /web-research or /codebase-research

9. AskUserQuestion: "Continue refinement?"
   - If yes: Add new iteration todos, goto step 3
   - If no: Mark all completed, exit
```

## Problem Document Structure

Location: `docs/plans/<problem-name>-refinement.md`

```markdown
# Problem Refinement: <Problem Name>

## Problem Statement
Initial user-provided problem (immutable)

## Current Understanding
Evolving description based on Q&A (updated each iteration)

## Constraints
Known limitations, requirements, dependencies

## Success Criteria
What "done" looks like

## Refinement Log
### Iteration 1 - 2025-12-06 14:30
**Questions Asked:**
- Q: What cache eviction policy?
  A: LRU preferred
- Q: Expected dataset size?
  A: ~10GB

**Research Suggested:**
- Web research: "LRU cache implementations Python"

**Status:** needs_more_refinement

### Iteration 2 - 2025-12-06 14:45
...

## Readiness Assessment
**Status:** ready | needs_more_refinement
**Missing Information:** [if not ready]
**Confidence:** [high/medium/low]
```

**Document Characteristics:**
- Problem Statement is immutable (original user input)
- Current Understanding evolves as questions are answered
- Refinement Log shows the journey (what was asked, what was learned)
- Agent reads entire doc each iteration to inform next questions
- Status gets updated by refinement agent

## Refinement Agent Behavior

### Inputs (from command via prompt)
1. Problem statement (user's original request)
2. Synthesis report path (compressed research context)
3. Refinement doc path (if continuing - contains previous Q&A)

### Process
1. Read synthesis report to understand available context
2. Read refinement doc (if exists) to see previous questions/answers
3. Identify gaps between "what we know" vs "what autonomous agents need"
4. Generate clarifying questions (prioritize most critical unknowns)
5. Suggest research directions if context is missing
6. Assess readiness: can autonomous agents execute this, or needs more refinement?
7. Update refinement doc (append new iteration to log, update sections)

### Output Format
```json
{
  "questions": [
    {"question": "What cache eviction policy?", "options": ["LRU", "LFU", "FIFO", "TTL-based"]},
    {"question": "Expected dataset size?", "options": []}
  ],
  "research_suggestions": [
    {
      "type": "web",
      "rationale": "Need to understand common cache eviction strategies",
      "query": "cache eviction policies LRU LFU comparison"
    },
    {
      "type": "codebase",
      "rationale": "Learn from existing cache implementation patterns",
      "url": "https://github.com/python/cpython"
    }
  ],
  "ready": false,
  "doc_path": "docs/plans/caching-system-refinement.md"
}
```

### Agent Constraints
- Ask 2-4 questions maximum per iteration
- Prefer multiple-choice when common options exist; otherwise open-ended (options: [])
- Focus on questions blocking autonomous execution
- Skip questions answerable from synthesis report
- Skip questions answered in previous iterations

### Readiness Criteria
Set `ready: true` with high confidence only when:
- Scope is clearly defined
- Constraints are explicit
- Success criteria are measurable
- No critical unknowns remain

### Confidence Levels
- **High**: All questions answered, clear scope, ready for autonomous work
- **Medium**: Most questions answered, minor ambiguities workable
- **Low**: Significant gaps remain, needs more refinement

Agent sets `ready: true` only with high confidence.

## Research Suggestions Format

### Structure
```json
{
  "research_suggestions": [
    {
      "type": "web",
      "rationale": "Need to understand common cache eviction strategies",
      "query": "cache eviction policies LRU LFU comparison"
    },
    {
      "type": "codebase",
      "rationale": "Learn from existing cache implementation patterns",
      "url": "https://github.com/python/cpython"
    }
  ]
}
```

### Command Handling
1. Display suggestions to user with rationale
2. AskUserQuestion: "Spawn research agents for these topics?"
   - Shows each suggestion with rationale
   - Multi-select: user can choose which ones to run
3. For selected suggestions:
   - Spawn `/web-research <query>` for web type
   - Spawn `/codebase-research <url>` for codebase type
4. New research files appear in `docs/research/` directories
5. Next iteration's synthesis picks them up automatically

### Agent Guidelines
- Suggest 1-3 research directions maximum
- Focus on gaps user questions cannot answer
- Provide clear rationale

## Templates and Validation

### Template
Create `ai-assisted-development/templates/problem-refinement.md`:

```markdown
# Problem Refinement: [REQUIRED: Problem Name]

## Problem Statement
[REQUIRED: Original user-provided problem statement]

## Current Understanding
[REQUIRED: Evolving description based on refinement - initially same as problem statement]

## Constraints
[OPTIONAL: Known limitations, requirements, dependencies]

## Success Criteria
[OPTIONAL: What "done" looks like]

## Refinement Log
<!-- Iterations appended here by agent -->

## Readiness Assessment
**Status:** [REQUIRED: ready | needs_more_refinement]
**Missing Information:** [REQUIRED if needs_more_refinement: List of gaps]
**Confidence:** [REQUIRED: high | medium | low]
```

### Validation Script
Create `ai-assisted-development/scripts/validate-problem-refinement.sh`:
- Checks all `[REQUIRED: ...]` placeholders are replaced
- Verifies status is valid value (ready | needs_more_refinement)
- Ensures at least one iteration in refinement log
- Exit code 0 = valid, exit code 1 = invalid

### Agent Workflow
1. Copy template to `docs/plans/<slug>-refinement.md`
2. Fill in sections using Edit tool
3. Run validation script
4. If fails: fix and retry once
5. Return doc path to command

## Readiness and Next Steps

### When Agent Declares ready: true

**Command Response:**
1. Mark all todos completed
2. Display to user:
   ```
   Problem refined and ready for autonomous execution!

   Refinement document: docs/plans/<name>-refinement.md

   Next steps:
   - Review the refined problem definition
   - Ready to proceed with implementation planning
   ```
3. Exit (no loop continuation)

### What User Does Next
- Review refinement doc
- Use `/write-plan` or other planning tools with refined problem
- Refinement doc feeds implementation agents

## Agent Prompting Strategy

### Key Instructions

**Your Job:**
- Read synthesis report for available context
- Read refinement doc for previous Q&A (if exists)
- Identify critical gaps blocking autonomous execution
- Ask 2-4 targeted questions (prefer multiple-choice)
- Suggest 1-3 research directions for gaps user cannot answer
- Assess whether problem allows autonomous work

**Critical Constraints:**
- Skip questions answered previously or in synthesis report
- Focus on questions blocking autonomous agents
- Prefer multiple-choice when common answers exist; otherwise open-ended (options: [])
- Return JSON only

**Readiness Criteria:**
Set `ready: true` with high confidence only when:
- Scope is clearly defined
- Constraints are explicit
- Success criteria are measurable
- No critical unknowns remain

**Output Format:**
```json
{
  "questions": [...],
  "research_suggestions": [...],
  "ready": false,
  "doc_path": "docs/plans/..."
}
```

## TodoWrite Pattern

Based on research (docs/research/web/2025-12-06-todowrite-checkpointing.md):

**Best Practices:**
1. **Proactive Planning** - Create all todos before starting
2. **Single-threaded execution** - One task in_progress at a time
3. **Update immediately** - Mark completed after finishing
4. **Communicate progress** - Use todos to show user progress
5. **2-5 minute task sizes** - Keep tasks granular

**Implementation:**
- Create all iteration todos at command start
- Mark one in_progress before starting
- Mark completed immediately after finishing
- Add new iteration todos when looping
- All completed when exiting

## Implementation Files

1. `ai-assisted-development/commands/refine-problem.md` - Command definition
2. `ai-assisted-development/agents/problem-refinement.md` - Agent definition
3. `ai-assisted-development/templates/problem-refinement.md` - Problem doc template
4. `ai-assisted-development/scripts/validate-problem-refinement.sh` - Validation script
5. Update `ai-assisted-development/.claude-plugin/plugin.json` - Register agent

## Design Rationale

### Why This Approach Works

**Evidence from Research:**
- **Pattern 2: External Enforcement** - Commands manage workflow; agents lack self-discipline
- **Pattern 3: First-Action Protocol** - Command controls flow deterministically
- **Pattern 4: State-First** - Agent receives state (refinement doc) before task
- **Pattern 5: Workflow Modes** - Agent responsibility: refinement only

**From synthesis (.orchestrator/synthesis/2025-12-06-problem-refinement-agent.md):**
- Progressive problem decomposition
- Standardized output structures with validation
- Token-efficient context gathering via synthesis
- External validation mechanisms
- Problem refinement clarifies; it does not solve
- Structured uncertainty handling
- Narrow, modular responsibility

## Metadata

**Design Date:** 2025-12-06
**Agent Version:** problem-refinement-v1
**Confidence Level:** High
