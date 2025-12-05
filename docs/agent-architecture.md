# Agent Architecture Pattern

## Two-Layer Structure

Each agent uses two components:

**Agent** (complete workflow implementation)
- Contains all workflow logic and step-by-step instructions
- Specifies tools in YAML frontmatter
- Specifies model (sonnet for complex workflows, haiku for simple tasks)
- Lives in `agents/<name>.md`
- Example: `agents/web-research.md`

**Command** (user interface)
- Launches agent via Task tool
- Passes user arguments to agent
- Lives in `commands/<name>.md`
- Example: `commands/web-research.md`

## Invocation Flow

```
User: /command "args"
  ↓
Command → Task tool → Agent
  ↓
Agent executes complete workflow
  ↓
Results return to user
```

## Why Two Layers (Not Three)

**Skill layer removed** - Initial design included a skill layer that agents would invoke via Skill tool, but:
- Agents cannot reliably invoke skills (Skill tool may not be available to subagents)
- Skills are auto-invoked by Claude based on description matching, not programmatically
- Adding indirection adds complexity without benefit
- Simpler to put workflow logic directly in agent

## Template-Copy Workflow

For agents that generate documents:

**1. Copy template to target location**
- Use `cp` via Bash tool
- Template contains `[REQUIRED: ...]` placeholders
- Target path uses date-based naming: `YYYY-MM-DD-<topic>.md`

**2. Execute core work**
- Research, analysis, code generation, etc.
- Gather information from tools

**3. Fill template via Edit tool**
- Replace each `[REQUIRED: ...]` placeholder
- Use Edit tool (not Write) to preserve structure
- Work systematically through all placeholders

**4. Validate explicitly**
- Run validation script via Bash tool
- Script checks for unfilled placeholders and required sections
- Exit 0 on success, non-zero with errors on failure

**5. Fix and retry once**
- If validation fails, read error output
- Make one fix attempt
- Re-validate
- Report final outcome (success or failure with details)

## Why This Pattern Works

**Two layers provide**:
- Simple, direct invocation chain
- All workflow logic in one place (easier to maintain)
- Isolated context per agent execution
- Clear separation between UI (command) and logic (agent)

**Template-copy ensures**:
- Correct file location from start
- Agent sees structure while editing
- Validation can be simple (check for markers)
- Claude follows instructions reliably

**Explicit validation provides**:
- Deterministic quality gates
- Clear error messages for fixing
- Bounded token usage (single retry)
- No hook complexity

## File Organization

```
plugin/
├── agents/
│   └── <name>.md              # Complete agent implementation
├── commands/
│   └── <name>.md              # Command that launches agent
├── templates/
│   └── <name>-template.md     # Template with placeholders
└── scripts/
    └── validate-<name>.sh     # Validation script
```

## Implementation Checklist

For new agents:

- [ ] Create template with `[REQUIRED:]` placeholders
- [ ] Write validation script (check placeholders, path pattern, sections)
- [ ] Implement agent with complete workflow (all 5 steps)
- [ ] Create command that launches agent via Task tool
- [ ] Register in `plugin.json`
- [ ] Test with sample input
- [ ] Verify validation catches errors
- [ ] Verify retry logic works

## Examples

**Web Research Agent**: Gathers documentation and examples, produces structured reports
- Agent: Search web, fetch pages, organize by source type, fill template, validate
- Template: Standardized research report with metadata
- Validation: Check placeholders filled, sections exist
- Command: `/ai-assisted-development:web-research <topic>`

**Future Agents**: Apply same pattern
- Code analysis, test generation, documentation creation
- Each follows: copy → work → fill → validate → report
- All workflow logic contained in agent, not split across skill layer

## Reference

Full design rationale: `docs/plans/2025-12-05-simplified-web-research-design.md`
