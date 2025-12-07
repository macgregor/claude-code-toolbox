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

## Complete Workflow

Follow these steps in order.

### Step 1: Parse Arguments and Determine Mode

**If args provided ({{ARGS}} not empty):**
- Mode: NEW
- Problem statement: {{ARGS}}

**If no args:**

1. Glob for existing refinements:
   ```bash
   ls docs/plans/*-refinement.md 2>/dev/null
   ```

2. If no refinements found:
   - Use AskUserQuestion: "What problem do you want to refine?"
   - Question type: Open-ended (no options)
   - Use answer as problem statement
   - Mode: NEW

3. If refinements found:
   - Extract problem names from filenames
   - Use AskUserQuestion: "What would you like to do?"
   - Options:
     - "Continue refining: <problem-1>" (for each existing refinement)
     - "Start new refinement"
   - If "Start new": AskUserQuestion for problem statement, Mode: NEW
   - If continue: Extract doc path from selection, Mode: CONTINUE

### Step 2: Initialize TodoWrite State

**Create all iteration todos upfront:**

```
TodoWrite([
  {content: "Synthesize existing research", status: "pending", activeForm: "Synthesizing existing research"},
  {content: "Analyze problem and identify gaps", status: "pending", activeForm: "Analyzing problem and identifying gaps"},
  {content: "Gather user clarifications", status: "pending", activeForm: "Gathering user clarifications"},
  {content: "Update problem definition", status: "pending", activeForm: "Updating problem definition"}
])
```

### Step 3: Synthesize Research Context

**Only run on first iteration:**

Check your conversation history - have you already run synthesis in this command execution?
- If YES: Skip this step entirely, go to step 4 (synthesis will be updated in step 8 if research is spawned)
- If NO: Continue with synthesis below

**Mark todo in_progress:**
```
TodoWrite([
  {content: "Synthesize existing research", status: "in_progress", activeForm: "Synthesizing existing research"},
  {content: "Analyze problem and identify gaps", status: "pending", activeForm: "Analyzing problem and identifying gaps"},
  {content: "Gather user clarifications", status: "pending", activeForm: "Gathering user clarifications"},
  {content: "Update problem definition", status: "pending", activeForm: "Updating problem definition"}
])
```

**Glob for research reports:**
```bash
find docs/research -name "*.md" -type f
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

**Mark todo completed:**
```
TodoWrite([
  {content: "Synthesize existing research", status: "completed", activeForm: "Synthesizing existing research"},
  {content: "Analyze problem and identify gaps", status: "pending", activeForm: "Analyzing problem and identifying gaps"},
  {content: "Gather user clarifications", status: "pending", activeForm: "Gathering user clarifications"},
  {content: "Update problem definition", status: "pending", activeForm: "Updating problem definition"}
])
```

### Step 4: Spawn Refinement Agent

**Mark todo in_progress:**
```
TodoWrite([
  {content: "Synthesize existing research", status: "completed", activeForm: "Synthesizing existing research"},
  {content: "Analyze problem and identify gaps", status: "in_progress", activeForm: "Analyzing problem and identifying gaps"},
  {content: "Gather user clarifications", status: "pending", activeForm: "Gathering user clarifications"},
  {content: "Update problem definition", status: "pending", activeForm: "Updating problem definition"}
])
```

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

**Mark todo completed:**
```
TodoWrite([
  {content: "Synthesize existing research", status: "completed", activeForm: "Synthesizing existing research"},
  {content: "Analyze problem and identify gaps", status: "completed", activeForm: "Analyzing problem and identifying gaps"},
  {content: "Gather user clarifications", status: "pending", activeForm: "Gathering user clarifications"},
  {content: "Update problem definition", status: "pending", activeForm: "Updating problem definition"}
])
```

### Step 5: Check Readiness

**If ready == true:**

1. Mark all todos completed:
   ```
   TodoWrite([
     {content: "Synthesize existing research", status: "completed", activeForm: "Synthesizing existing research"},
     {content: "Analyze problem and identify gaps", status: "completed", activeForm: "Analyzing problem and identifying gaps"},
     {content: "Gather user clarifications", status: "completed", activeForm: "Gathering user clarifications"},
     {content: "Update problem definition", status: "completed", activeForm: "Updating problem definition"}
   ])
   ```

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

**Mark todo in_progress:**
```
TodoWrite([
  {content: "Synthesize existing research", status: "completed", activeForm: "Synthesizing existing research"},
  {content: "Analyze problem and identify gaps", status: "completed", activeForm: "Analyzing problem and identifying gaps"},
  {content: "Gather user clarifications", status: "in_progress", activeForm: "Gathering user clarifications"},
  {content: "Update problem definition", status: "pending", activeForm: "Updating problem definition"}
])
```

**For each question in questions array:**

1. Extract question and options
2. Use AskUserQuestion:
   - question: <question text>
   - If options array not empty: provide as multiSelect false choices
   - If options array empty: open-ended question
3. Capture answer
4. Store Q&A pair for later

**Mark todo completed:**
```
TodoWrite([
  {content: "Synthesize existing research", status: "completed", activeForm: "Synthesizing existing research"},
  {content: "Analyze problem and identify gaps", status: "completed", activeForm: "Analyzing problem and identifying gaps"},
  {content: "Gather user clarifications", status: "completed", activeForm: "Gathering user clarifications"},
  {content: "Update problem definition", status: "pending", activeForm: "Updating problem definition"}
])
```

### Step 7: Update Refinement Document

**Mark todo in_progress:**
```
TodoWrite([
  {content: "Synthesize existing research", status: "completed", activeForm: "Synthesizing existing research"},
  {content: "Analyze problem and identify gaps", status: "completed", activeForm: "Analyzing problem and identifying gaps"},
  {content: "Gather user clarifications", status: "completed", activeForm: "Gathering user clarifications"},
  {content: "Update problem definition", status: "in_progress", activeForm: "Updating problem definition"}
])
```

**Read current refinement doc:**
```bash
cat <doc_path>
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

**Mark todo completed:**
```
TodoWrite([
  {content: "Synthesize existing research", status: "completed", activeForm: "Synthesizing existing research"},
  {content: "Analyze problem and identify gaps", status: "completed", activeForm: "Analyzing problem and identifying gaps"},
  {content: "Gather user clarifications", status: "completed", activeForm: "Gathering user clarifications"},
  {content: "Update problem definition", status: "completed", activeForm: "Updating problem definition"}
])
```

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
   ```bash
   find docs/research -name "*.md" -type f
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