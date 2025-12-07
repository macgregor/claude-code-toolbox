---
description: Refine rough problem statements through iterative questioning and synthesis
---

# Refine Problem Command

You orchestrate the problem refinement loop using synthesis and refinement agents.

## User Input

User provides either:
- `{{ARGS}}` - New problem statement to refine
- No args - Continue existing refinement or start new

## Your Task

Manage the iterative refinement process:
1. Parse args to determine new vs continue
2. Spawn synthesis agent to gather context
3. Spawn refinement agent to analyze and ask questions
4. Use AskUserQuestion to gather clarifications
5. Update refinement document with answers
6. Optionally spawn research agents
7. Loop until problem is ready or user stops

## Performance Requirements

CRITICAL: Use parallel execution for independent operations.

**Recommended Batching:**
- Glob patterns: 3-5 calls per message
- Read operations: 5 files per message
- Task tool calls: Execute in parallel when no dependencies exist
- WebSearch calls: 3-5 searches per message

**Examples:**
- ✅ GOOD: Single message with Glob + multiple Task calls
- ❌ BAD: Sequential messages for independent Glob operations
- ✅ GOOD: Read synthesis report AND refinement doc in single message
- ❌ BAD: Read synthesis, wait, then read refinement

DO NOT execute tools sequentially when they can run in parallel.

## Complete Workflow

Follow these steps in order.

### Step 1: Parse Arguments and Determine Mode

**If args provided ({{ARGS}} not empty):**
- Mode: NEW
- Problem statement: {{ARGS}}

**If no args:**

1. Glob for existing refinements:
   ```
   Use Glob tool with pattern: "docs/plans/????-??-??-*-refinement.md"
   ```

2. If no refinements found:
   - Use AskUserQuestion: "What problem do you want to refine?"
   - Question type: Open-ended (no options)
   - Use answer as problem statement
   - Mode: NEW

3. If refinements found:
   - Extract problem names from filenames (remove YYYY-MM-DD- prefix and -refinement.md suffix)
   - Use AskUserQuestion: "What would you like to do?"
   - Options:
     - "Continue refining: <problem-name>" (for each existing refinement)
     - "Start new refinement"
   - If "Start new": AskUserQuestion for problem statement, Mode: NEW
   - If continue: Extract doc path from selection, Mode: CONTINUE

### Step 2: Initialize TodoWrite State

**Create iteration todos:**

Use TodoWrite to create these 4 todos, all with status "pending":
1. "Synthesize existing research" / "Synthesizing existing research"
2. "Analyze problem and identify gaps" / "Analyzing problem and identifying gaps"
3. "Gather user clarifications" / "Gathering user clarifications"
4. "Update problem definition" / "Updating problem definition"

**Todo Management Pattern:**
- Mark a todo "in_progress" BEFORE starting work
- Mark it "completed" IMMEDIATELY after finishing
- Only ONE todo should be "in_progress" at any time

### Step 3: Synthesize Research Context

**Only run on first iteration:**

Check your conversation history - have you already run synthesis in this command execution?
- If YES: Skip this step entirely, go to step 4 (synthesis will be updated in step 8 if research is spawned)
- If NO: Continue with synthesis below

Mark todo #1 "Synthesize existing research" as **in_progress**

**Glob for research reports:**
```
Use Glob tool with pattern: "docs/research/**/*.md"
```

**Spawn synthesis agent:**

Use Task tool:
- subagent_type: `ai-assisted-development:synthesis`
- model: `haiku`
- description: "Synthesize research for problem"
- prompt:
  ```
  User's objective: <problem statement>

  Input sources to synthesize:
  <list of file paths from glob, one per line>
  ```

**Capture synthesis report path from agent response**

Mark todo #1 "Synthesize existing research" as **completed**

### Step 4: Spawn Refinement Agent

Mark todo #2 "Analyze problem and identify gaps" as **in_progress**

**Build refinement agent prompt:**

If NEW mode:
```
Problem statement: <problem from args or user>
Synthesis report path: <path from synthesis agent>
Refinement doc path: none
```

If CONTINUE mode:
```
Problem statement: <read from existing refinement doc>
Synthesis report path: <path from synthesis agent>
Refinement doc path: <path from step 1>
```

**Spawn refinement agent:**

Use Task tool:
- subagent_type: `ai-assisted-development:problem-refinement`
- model: `sonnet`
- description: "Refine problem statement"
- prompt: <built above>

**Parse JSON response:**
- Extract: `questions`, `research_suggestions`, `ready`, `doc_path`

Mark todo #2 "Analyze problem and identify gaps" as **completed**

### Step 5: Check Readiness

**If ready == true:**

1. Mark remaining todos #3 and #4 as **completed**

2. Display to user:
   ```
   Problem refined and ready for autonomous execution!

   Refinement document: <doc_path>

   Next steps:
   - Review the refined problem definition
   - Ready to proceed with implementation planning
   ```

3. EXIT (stop here, do not continue)

**If ready == false:** Continue to step 6

### Step 6: Gather User Clarifications

Mark todo #3 "Gather user clarifications" as **in_progress**

**For each question in questions array:**

1. Extract question and options
2. Use AskUserQuestion:
   - question: <question text>
   - If options array not empty: provide as multiSelect false choices
   - If options array empty: open-ended question
3. Capture answer
4. Store Q&A pair for later

Mark todo #3 "Gather user clarifications" as **completed**

### Step 7: Update Refinement Document

Mark todo #4 "Update problem definition" as **in_progress**

**Read current refinement doc:**
```
Use Read tool with file_path: <doc_path>
```

**Append new iteration to Refinement Log:**

Use Edit tool to add before "## Readiness Assessment" section:

```markdown
### Iteration N - <timestamp>
**Questions Asked:**
- Q: <question 1>
  A: <answer 1>
- Q: <question 2>
  A: <answer 2>

**Research Suggested:**
<if research_suggestions not empty>
- <type>: <query or URL>

**Status:** needs_more_refinement
```

Mark todo #4 "Update problem definition" as **completed**

### Step 8: Handle Research Suggestions (Optional)

**If research_suggestions array not empty:**

1. Build question for user:
   - Question: "Spawn research agents for these topics?"
   - For each suggestion:
     - Label: "<type>: <rationale>"
     - Description: "<query or URL>"
   - multiSelect: true

2. Use AskUserQuestion with above

3. For each selected suggestion:
   - If type == "web": Spawn `/web-research <query>`
   - If type == "codebase": Spawn `/codebase-research <url>`

**If any research was spawned:**

Run synthesis to incorporate new research for next iteration:

1. Glob for research reports:
   ```
   Use Glob tool with pattern: "docs/research/**/*.md"
   ```

2. Spawn synthesis agent:
   - subagent_type: `ai-assisted-development:synthesis`
   - model: `haiku`
   - description: "Synthesize research for problem"
   - prompt:
     ```
     User's objective: <problem statement>

     Input sources to synthesize:
     <list of file paths from glob, one per line>
     ```

3. Capture updated synthesis report path from agent response

**Note:** Updated synthesis will be used in next iteration's refinement

### Step 9: Ask to Continue

**Use AskUserQuestion:**
- Question: "Continue refinement?"
- Options:
  - "Yes - ask more questions"
  - "No - stop here"

**If "Yes":**
- Reset to step 2 (initialize new iteration todos)
- Goto step 3 (synthesis will pick up new research)

**If "No":**
- Mark all todos completed
- EXIT

## Important Notes

- **TodoWrite pattern**: Create all todos upfront, mark in_progress one at a time, mark completed immediately after
- **Single-threaded**: Only one todo in_progress at any time
- **JSON parsing**: Refinement agent returns JSON, parse carefully
- **Path tracking**: Keep track of paths in your context:
  - `synthesis_report_path`: Path from synthesis agent (updated in step 8 if research spawned)
  - `doc_path`: Path to refinement document from refinement agent
- **Iteration loop**: Steps 2-9 repeat until ready or user stops
- **No commits**: Refinement docs not committed automatically
- **Synthesis optimization**: Synthesis only runs on first iteration, then again in step 8 if research is spawned