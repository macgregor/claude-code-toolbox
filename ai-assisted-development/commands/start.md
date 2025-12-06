---
description: Launch orchestrated AI-assisted development workflow
---

# Start AI-Assisted Development Workflow

You are launching an orchestrated development workflow.

## Your Task

The user has provided a task or objective. Launch the orchestrator agent to handle it.

## Instructions

Use the Task tool to invoke the orchestrator:

**CRITICAL:** Use a single Task tool call with these parameters:
- `subagent_type`: `ai-assisted-development:orchestrator`
- `prompt`: Pass the user's complete request (from {{ARGS}}) to the orchestrator
- `model`: `sonnet` (orchestrator needs reasoning capability)
- `description`: Brief description (3-5 words) of what the orchestrator will do

Example:
```
Task(
  subagent_type="ai-assisted-development:orchestrator",
  prompt="User request: Research best practices for async Python testing",
  model="sonnet",
  description="Orchestrate async testing research"
)
```

After invoking the orchestrator, your work is complete. The orchestrator will report results when finished.

## Arguments

User's task: {{ARGS}}
