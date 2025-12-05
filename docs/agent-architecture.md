# Agent Architecture Pattern

## Three-Layer Structure

Each agent uses three components with single responsibilities:

**Skill** (reusable workflow logic)
- Contains complete step-by-step instructions
- Lists allowed tools in YAML frontmatter
- Lives in `skills/<name>/SKILL.md`
- Example: `skills/web-research/SKILL.md`

**Agent** (isolated execution context)
- Thin wrapper that invokes skill via Skill tool
- Specifies model (haiku for speed, sonnet for complexity)
- Lives in `agents/<name>.md`
- Example: `agents/web-research.md`

**Command** (user interface)
- Thin wrapper for interactive use
- Uses Task tool with custom subagent_type
- Passes user arguments to agent
- Lives in `commands/<name>.md`
- Example: `commands/web-research.md`

## Invocation Flow

```
User: /command "args"
  ↓
Command → Task tool → Agent
  ↓
Agent → Skill tool → Skill
  ↓
Skill executes workflow
  ↓
Results return up chain
```

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

**Three layers enable**:
- Skill reuse across multiple agents
- Isolated context per execution
- Clear separation of concerns

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
├── skills/
│   └── <name>/
│       └── SKILL.md           # Workflow instructions
├── agents/
│   └── <name>.md              # Agent wrapper
├── commands/
│   └── <name>.md              # Command wrapper
├── templates/
│   └── <name>-template.md     # Template with placeholders
└── scripts/
    └── validate-<name>.sh     # Validation script
```

## Implementation Checklist

For new agents:

- [ ] Create template with `[REQUIRED:]` placeholders
- [ ] Write validation script (check placeholders, path pattern, sections)
- [ ] Implement skill with workflow steps
- [ ] Create agent wrapper (invoke skill, specify model)
- [ ] Create command wrapper (invoke agent, pass args)
- [ ] Register in `plugin.json`
- [ ] Test with sample input
- [ ] Verify validation catches errors
- [ ] Verify retry logic works

## Examples

**Web Research Agent**: Gathers documentation and examples, produces structured reports
- Skill: Search web, fetch pages, organize by source type
- Template: Standardized research report with metadata
- Validation: Check placeholders filled, sections exist

**Future Agents**: Apply same pattern
- Code analysis, test generation, documentation creation
- Each follows: copy → work → fill → validate → report

## Reference

Full design rationale: `docs/plans/2025-12-05-simplified-web-research-design.md`
