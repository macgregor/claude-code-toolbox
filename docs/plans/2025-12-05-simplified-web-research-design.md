# Simplified Web Research Design

## Overview

A simplified web research agent for Claude Code that uses a template-copy pattern for reliable, deterministic document generation. This design replaces the previous hook-based validation approach with explicit workflow steps that match proven patterns from the Claude Code ecosystem.

## Problem Statement

The previous design (2025-12-04-web-research-agent-design.md) used hook-based validation that proved unreliable:
- Hooks don't receive agent/skill identity information
- Content-based detection via unique identifiers is fragile
- Skills don't reliably produce output in expected locations
- Hook validation requires "clever engineering" to detect execution context

## Solution: Template Copy Pattern

Based on patterns from github/spec-kit and other successful Claude Code repos (obra/superpowers, wshobson/agents), we adopt:

1. **Template with placeholders** - Template file contains `[REQUIRED: ...]` markers
2. **Copy first** - Skill copies template to target location as first step
3. **Edit to fill** - Skill uses Edit tool to replace placeholders with content
4. **Explicit validation** - Skill runs validation script as workflow step
5. **Single retry** - If validation fails, one fix attempt then report outcome

**Why This Works:**
- File location guaranteed correct (copy step ensures it)
- Agent sees structure while editing (placeholders guide content)
- Claude follows "copy → edit → validate" instructions reliably
- Validation is deterministic (grep for unfilled placeholders)
- No hooks, no content detection, no clever engineering

## Architecture

### Three-Layer Structure

1. **Skill** (`ai-assisted-development/skills/web-research/SKILL.md`)
   - Contains complete workflow logic
   - Detailed step-by-step instructions
   - Tools: WebSearch, WebFetch, Read, Write, Edit, Bash

2. **Agent** (`ai-assisted-development/agents/web-research.md`)
   - Thin wrapper that invokes skill via Skill tool
   - Reference: `ai-assisted-development:web-research`
   - Model: haiku (fast, cost-effective)

3. **Command** (`ai-assisted-development/commands/web-research.md`)
   - Thin wrapper for interactive use
   - Uses Task tool with `subagent_type=ai-assisted-development:web-research`
   - Passes user arguments to agent

**Invocation Flow:**
```
User: /web-research "topic"
  ↓
Command → Task tool → Agent
  ↓
Agent → Skill tool → Skill
  ↓
Skill executes workflow
  ↓
Results return up chain
```

## Skill Workflow

### Step-by-Step Process

**1. Copy Template**
- Copy `./templates/web-research-report.md` to `docs/research/YYYY-MM-DD-<topic-slug>.md`
- Use today's date in YYYY-MM-DD format
- Slugify topic from research objective (lowercase, hyphens)
- File now exists at correct location with placeholder structure

**2. Conduct Web Research**
- WebSearch for official docs, recent articles, best practices
- WebFetch for specific documentation pages, READMEs
- Organize findings by source type:
  - Official Documentation
  - Source Code Repositories
  - Community/Third-party
- For each source, capture: Source, URL, Author, Date, Activity, Key points
- Target 5-10 high-quality sources per category
- Work efficiently - comprehensive but not exhaustive

**3. Fill Template via Edit**
- Use Edit tool to replace each `[REQUIRED: ...]` placeholder:
  - `[REQUIRED: Topic]` → actual topic
  - `[REQUIRED: Research objective]` → provided objective
  - `[REQUIRED: Executive summary]` → 2-3 paragraph synthesis
  - `[REQUIRED: Official documentation]` → formatted findings
  - `[REQUIRED: Source code repositories]` → formatted findings
  - `[REQUIRED: Community/third-party]` → formatted findings
  - `[REQUIRED: Sources list]` → complete URL list
  - `[REQUIRED: Research date]` → ISO 8601 timestamp
  - `[REQUIRED: Search queries]` → queries used
  - `[REQUIRED: Agent model]` → model identifier

**4. Validate**
- Run `scripts/validate-research-report.sh <filepath>` via Bash tool
- Script checks:
  - No `[REQUIRED:` markers remain
  - Path matches `docs/research/YYYY-MM-DD-*.md`
  - All required section headers exist

**5. Handle Validation Failure**
- If validation passes: report success with filepath
- If validation fails on first attempt:
  - Read error output
  - Make one fix attempt
  - Re-validate
- If still failing: report error in final output with details

## Template Structure

**File:** `templates/web-research-report.md`

```markdown
# Research: [REQUIRED: Topic]

## Research Objective
[REQUIRED: The research goal as provided]

## Executive Summary
[REQUIRED: 2-3 paragraph overview of key findings]

## Findings

### Official Documentation

[REQUIRED: Official sources with standardized metadata. Format each as:
- **Source**: [Title]
  **URL**: [URL]
  **Author**: [Person/organization/vendor]
  **Date**: [Last updated/published]
  **Activity**: N/A
  **Key points**:
    - [Bullet point]
    - [Bullet point]
]

### Source Code Repositories

[REQUIRED: Repository sources with standardized metadata. Format each as:
- **Source**: [Repository name]
  **URL**: [URL]
  **Author**: [Person/organization]
  **Date**: [Last updated]
  **Activity**: [Stars/downloads + last commit date]
  **Key points**:
    - [Bullet point]
    - [Bullet point]
]

### Community/Third-party

[REQUIRED: Community sources with standardized metadata. Format each as:
- **Source**: [Title]
  **URL**: [URL]
  **Author**: [Person/organization]
  **Date**: [Published/updated date]
  **Activity**: N/A
  **Key points**:
    - [Bullet point]
    - [Bullet point]
]

## Sources
[REQUIRED: Complete list of all URLs/documents consulted]
- [URL 1]
- [URL 2]

## Metadata
- **Research Date**: [REQUIRED: ISO 8601 timestamp]
- **Search Queries**: [REQUIRED: Comma-separated list of search queries used]
- **Agent Model**: [REQUIRED: Model identifier]
```

**Key Characteristics:**
- Every required section has `[REQUIRED: ...]` placeholder
- Placeholders include guidance on content/format expected
- URL on dedicated line (not inline with title)
- Standardized metadata format across all source types
- Self-documenting structure

## Validation Script

**File:** `scripts/validate-research-report.sh`

**Purpose:** Deterministic validation that report is properly filled out

**Validation Checks:**

1. **No unfilled placeholders**
   - `grep -q '\[REQUIRED:' "$FILEPATH"` returns no matches
   - If found, list all remaining placeholders in error output

2. **Path pattern correct**
   - Filename matches `docs/research/YYYY-MM-DD-*.md`
   - Year is 4 digits, month/day are 2 digits
   - Topic slug follows the date

3. **Required sections exist**
   - Check for these headers:
     - `## Research Objective`
     - `## Executive Summary`
     - `## Findings`
     - `### Official Documentation`
     - `### Source Code Repositories`
     - `### Community/Third-party`
     - `## Sources`
     - `## Metadata`

**Output:**
- Exit 0 if all checks pass
- Exit non-zero with descriptive error message if any check fails
- Error messages guide agent on what to fix

**Example Error Output:**
```
ERROR: Unfilled placeholders found:
- [REQUIRED: Executive summary]
- [REQUIRED: Search queries]

ERROR: Missing required section: ## Sources
```

**NOT Validated:**
- Individual source metadata completeness (trusted to skill instructions)
- Markdown formatting details
- Content quality or accuracy
- URL validity or reachability
- Metadata field completeness (beyond presence check)

**Philosophy:** Simple, structural validation. If placeholders are replaced and sections exist, report is valid.

## File Organization

```
ai-assisted-development/
├── skills/
│   └── web-research/
│       └── SKILL.md                    # Core workflow logic
├── agents/
│   └── web-research.md                 # Agent wrapper (invokes skill)
├── commands/
│   └── web-research.md                 # Command wrapper (invokes agent)
├── templates/
│   └── web-research-report.md          # Template with [REQUIRED:] placeholders
└── scripts/
    └── validate-research-report.sh     # Validation script

docs/research/                          # Output directory
└── YYYY-MM-DD-<topic>.md              # Generated reports
```

## Changes from Previous Design

**Removed:**
- `hooks/hooks.json` - No longer using hooks
- Unique identifier in metadata (`web-research-agent-v1-7k9p3x2m`) - Not needed without hooks
- Separate template read step - Template copied directly to target location
- Hook-based validation trigger - Validation is explicit workflow step

**Added:**
- Template copy as first workflow step
- `[REQUIRED: ...]` placeholder markers
- Explicit Bash tool call for validation
- Single retry logic for validation failures
- Dedicated URL line in source metadata

**Simplified:**
- No hook system integration
- No content-based detection
- No complex path logic (template copy handles it)
- Validation is structural only (no metadata field parsing)

## Design Rationale

### Why Template Copy Pattern?

Proven pattern from github/spec-kit and Claude Code ecosystem:
- Claude reliably follows "copy → edit" instructions
- File location guaranteed correct from start
- Agent sees structure while editing
- Validation can be simple (check for unfilled markers)

### Why Explicit Validation Step?

Hooks don't provide enough context:
- Can't reliably detect which agent/skill is executing
- Content-based detection is fragile
- Explicit steps are clearer and more maintainable

### Why Single Retry?

Balances autonomy with token efficiency:
- Handles common mistakes (forgot to fill a placeholder)
- Prevents infinite loops on systematic issues
- Bounded token usage
- Graceful degradation (reports error if can't fix)

### Why Structural Validation Only?

Complex content validation is fragile:
- Parsing individual source metadata is error-prone
- Format variations break validation
- Skill instructions should ensure quality
- Structural checks are deterministic and robust

### Why Three Layers?

Each layer has single responsibility:
- Skill: reusable workflow logic
- Agent: isolated execution context
- Command: interactive interface

Enables skill reuse in future multi-agent orchestration.

## Future Enhancements

Not in current scope, but possible later:
- Local codebase research capability
- Deeper code analysis of external repos
- Research report comparison/diffing
- Quality scoring of sources
- Integration with planning agents
- Automated research scheduling
- Source credibility assessment

## Implementation Checklist

- [ ] Create template file with `[REQUIRED:]` placeholders
- [ ] Write validation script with structural checks
- [ ] Implement skill with copy → research → edit → validate workflow
- [ ] Create agent wrapper that invokes skill
- [ ] Create command wrapper that invokes agent
- [ ] Test with sample research topic
- [ ] Verify validation catches unfilled placeholders
- [ ] Verify single retry logic works
- [ ] Document in plugin README
