# Codebase Research Agent Design

## Overview

A codebase research agent for Claude Code that analyzes repositories (from URL or local path) and produces compressed architectural summaries in a standardized format. These reports are designed for consumption by planning agents during software development, providing high-level architectural understanding without implementation details.

## Problem Statement

Planning agents need compressed architectural views of codebases to inform design decisions, but:
- Full codebase exploration exhausts tokens quickly
- Manual documentation may be outdated or incomplete
- Implementation details add noise for planning purposes
- Need consistent format for agent consumption

## Solution: Token-Efficient Codebase Analysis

Following the template-copy pattern established by web-research agent, we create a codebase researcher that:
1. Accepts URL (clones) or local path (analyzes in place)
2. Uses progressive disclosure to minimize token usage
3. Prioritizes documentation files (pre-compressed human summaries)
4. Produces standardized reports for planning agent consumption

**Design Philosophy:**
- Present compressed view, don't judge utility
- Capture architecture and patterns, not implementation details
- Token-efficient staged analysis (docs first, then strategic code reads)
- Self-contained reports suitable for planning context

## Architecture

### Two-Layer Structure

Following agent-architecture.md pattern:

**Agent** (`ai-assisted-development/agents/codebase-research.md`)
- Complete workflow implementation
- Tools: Bash, Glob, Grep, Read, Edit
- Model: sonnet (requires reasoning for codebase analysis)
- Self-contained with full workflow instructions

**Command** (`ai-assisted-development/commands/codebase-research.md`)
- Launches agent via Task tool
- Passes single argument (URL or path)
- User invokes: `/codebase-research <url-or-path>`

**Invocation Flow:**
```
User: /codebase-research "https://github.com/user/repo"
  ↓
Command → Task tool → Agent
  ↓
Agent executes complete workflow
  ↓
Results return to user
```

**Supporting Files:**
- Template: `ai-assisted-development/templates/codebase-analysis-report.md`
- Validation: `ai-assisted-development/scripts/validate-codebase-report.sh`

## Agent Workflow

### Step 1: Copy Template

**Action:** Copy template to target location

1. Determine output filename:
   - Use today's date in YYYY-MM-DD format
   - Extract repo name from input:
     - URL: use repository name (e.g., `user/repo` → `repo`)
     - Path: use directory name
   - Format: `docs/research/YYYY-MM-DD-<repo-name>.md`
   - Example: `docs/research/2025-12-05-claude-code.md`

2. Copy template to target location:
   - From: `ai-assisted-development/templates/codebase-analysis-report.md`
   - To: `docs/research/YYYY-MM-DD-<repo-name>.md`

3. Verify the copy succeeded (file exists at target location)

**Quality Gate:** File must exist at correct location before proceeding.

### Step 2: Determine Input Type & Prepare

**Action:** Detect input type and prepare analysis path

1. Detect if input is URL or filesystem path:
   - URL: starts with `http://` or `https://`
   - Path: anything else

2. If URL:
   - Clone to `/tmp/codebase-research-<timestamp>/`
   - Set analysis path to clone location

3. If path:
   - Verify path exists (error if not)
   - Use path directly for analysis

**Note:** /tmp/ automatically cleans itself, no explicit cleanup needed.

### Step 3: Analyze Codebase

**Action:** Token-efficient staged analysis

**Stage 1: Documentation Discovery** (Highest signal-to-token ratio)
- Glob for documentation files (`**/*.md`, `**/*.txt`, limit depth to 2-3 levels)
- Prioritize by name patterns (in order):
  - README.md, README.txt (always read if exists)
  - ARCHITECTURE.md, DESIGN.md, CONTRIBUTING.md
  - docs/README.md, docs/architecture.md, docs/design.md
  - docs/overview.md, docs/guide.md
- Read 2-3 most important documentation files found
- Read one manifest file (package.json, Cargo.toml, pyproject.toml, go.mod, etc.)
  - Captures dependencies, scripts, metadata

**Stage 2: Code Discovery** (Strategic exploration)
- Glob top-level directory structure to understand organization
- Grep for architecture keywords in code (`output_mode: "files_with_matches"` only):
  - "plugin", "api", "interface", "config", "architecture"
  - "router", "handler", "controller", "service"
- Grep for integration patterns:
  - Main entry points (main, index, app)
  - Import/export patterns
  - Configuration loaders
- Identify 2-3 key code files worth reading based on matches

**Stage 3: Selective Deep Read** (Controlled token spend)
- Read only the 2-3 most promising code files from Stage 2
- Stop when template sections have enough information
- Do not read exhaustively - prioritize breadth over depth

**Stage 4: Extract Related Repos** (Automated + LLM judgment)
- Grep for URL patterns across all files already read
- Filter to repository URLs (github.com, gitlab.com, etc.)
- Agent reviews and selects URLs that appear to be related projects:
  - **Include:** sibling libraries, companion tools, project forks, team-maintained deps
  - **Exclude:** random dependencies, documentation links, unrelated references
- Result: curated list of related repositories or "None identified"

**Token Management Philosophy:**
- Documentation files are pre-compressed summaries (highest value)
- Use Grep to find, not read everything
- Read selectively based on signals
- Stop when sufficient for template filling

### Step 4: Fill Template

**Action:** Replace all `[REQUIRED: ...]` placeholders with content

Use Edit tool to replace each placeholder:
- `[REQUIRED: Repo name]` → repository name extracted from input
- `[REQUIRED: Original input]` → exact URL or path provided by user
- `[REQUIRED: Executive summary]` → 2-3 paragraph overview of codebase
- `[REQUIRED: Purpose]` → what the project does (1-2 sentences)
- `[REQUIRED: Maintainer]` → owner/organization/individual
- `[REQUIRED: Repository URL]` → canonical repository URL
- `[REQUIRED: Tech stack]` → bulleted list of technology names only
- `[REQUIRED: Architecture patterns]` → high-level patterns observed
- `[REQUIRED: Integration points]` → APIs, CLIs, plugin systems (high-level)
- `[REQUIRED: Related repositories]` → curated links or "None identified"
- `[REQUIRED: ISO timestamp]` → current timestamp (YYYY-MM-DDTHH:MM:SSZ)
- `[REQUIRED: Model identifier]` → agent's model ID

**Critical:** Every placeholder must be replaced. Validation will fail if any remain.

### Step 5: Validate & Report

**Action:** Run validation script and handle outcome

1. Run validation script:
   ```bash
   ai-assisted-development/scripts/validate-codebase-report.sh docs/research/YYYY-MM-DD-<repo-name>.md
   ```

2. Read validation output:
   - Exit 0: Validation passed
   - Exit non-zero: Validation failed with error details

3. Handle validation result:
   - **If passes:** Report success with filepath
   - **If fails:** Make ONE fix attempt based on errors, then re-validate
   - **If still fails:** Report final outcome with error details

**Single Retry Philosophy:** Handles common mistakes, prevents infinite loops, bounded token usage.

## Template Structure

**File:** `ai-assisted-development/templates/codebase-analysis-report.md`

```markdown
# Codebase Analysis: [REQUIRED: Repo name]

## Research Objective
[REQUIRED: Original input - URL or path]

## Executive Summary
[REQUIRED: 2-3 paragraph overview of the codebase - purpose, architecture approach, and key characteristics]

## Overview
- **Purpose**: [REQUIRED: What the project does]
- **Maintainer**: [REQUIRED: Owner/organization]
- **Repository**: [REQUIRED: Canonical URL]

## Tech Stack
[REQUIRED: Bulleted list of technologies, frameworks, languages - names only]

## Architecture Patterns
[REQUIRED: High-level architectural patterns observed - MVC, plugin system, microservices, etc.]

## Integration Points
[REQUIRED: APIs, CLIs, plugin interfaces, configuration mechanisms - high-level only]

## Related Repositories
[REQUIRED: Links to related repositories, or "None identified"]

## Metadata
- **Analysis Date**: [REQUIRED: ISO 8601 timestamp]
- **Agent Model**: [REQUIRED: Model identifier]
```

**Key Characteristics:**
- Every required section has `[REQUIRED: ...]` placeholder
- Placeholders include guidance on expected content
- Consistent with web-research report structure
- Self-documenting template

## Validation Script

**File:** `ai-assisted-development/scripts/validate-codebase-report.sh`

**Purpose:** Deterministic structural validation

**Validation Checks:**

1. **No unfilled placeholders**
   - Check for any remaining `[REQUIRED:` markers
   - List all unfilled placeholders in error output

2. **Path pattern correct**
   - Filename matches `docs/research/YYYY-MM-DD-*.md`
   - Year is 4 digits, month/day are 2 digits
   - Topic slug follows the date

3. **Required sections exist**
   - `# Codebase Analysis:`
   - `## Research Objective`
   - `## Executive Summary`
   - `## Overview`
   - `## Tech Stack`
   - `## Architecture Patterns`
   - `## Integration Points`
   - `## Related Repositories`
   - `## Metadata`

**Output:**
- Exit 0 with message "Validation passed: <filepath>" if all checks pass
- Exit non-zero with descriptive errors if any check fails

**Philosophy:** Simple structural validation. If placeholders filled and sections exist, report is valid.

## Design Rationale

### Why Docs-First Analysis?

Documentation files are:
- Pre-compressed summaries written by humans
- Highest signal-to-token ratio
- Often more current than comments in code
- Designed for understanding, not execution

### Why Progressive Disclosure?

Token efficiency based on research findings:
- Context is finite and precious
- Models experience "context rot" with high token counts
- Just-in-time loading prevents context bloat
- Strategic exploration beats exhaustive reading

### Why URL + Path Support?

Flexibility for different workflows:
- URL: analyze external repos during research
- Path: analyze local repos or workspace projects
- Single parameter simplifies invocation
- Auto-detection removes user burden

### Why Related Repos Section?

Planning agents benefit from:
- Understanding ecosystem context
- Discovering companion libraries
- Identifying team-maintained dependencies
- Following architectural lineage

### Why No Implementation Details?

Planning phase needs:
- What patterns exist (not how they're coded)
- What integration points exist (not their internals)
- Compressed view for decision-making
- Focus on architecture, not algorithms

### Why Template-Copy Pattern?

Proven reliable from web-research agent:
- Guarantees correct file location
- Agent sees structure while editing
- Validation is simple and deterministic
- Claude follows copy → edit → validate reliably

## File Organization

```
ai-assisted-development/
├── agents/
│   └── codebase-research.md         # Complete agent implementation
├── commands/
│   └── codebase-research.md         # Command wrapper (launches agent)
├── templates/
│   └── codebase-analysis-report.md  # Template with [REQUIRED:] placeholders
└── scripts/
    └── validate-codebase-report.sh  # Validation script

docs/research/                        # Output directory
└── YYYY-MM-DD-<repo-name>.md        # Generated reports
```

## Comparison with Web Research Agent

**Similarities:**
- Template-copy workflow pattern
- `[REQUIRED: ...]` placeholder system
- Explicit validation step with single retry
- Two-layer architecture (agent + command)
- Output to `docs/research/` with date-based naming

**Differences:**
- **Input:** URL/path vs research topic string
- **Sources:** Codebase files vs web search results
- **Tools:** Bash/Glob/Grep/Read vs WebSearch/WebFetch
- **Analysis:** Progressive disclosure stages vs web research strategy
- **Scope:** Architecture & patterns vs documentation & examples

**Design Consistency:** Both agents follow established patterns, enabling future orchestration.

## Future Enhancements

Not in current scope, but possible later:
- Dependency graph visualization
- Code quality metrics (test coverage, documentation coverage)
- Comparison between multiple repos
- Integration with planning agents for automated context gathering
- Support for monorepo analysis (analyze specific packages)
- Historical analysis (compare versions over time)
- Security/vulnerability scanning integration

## Implementation Checklist

- [ ] Create template file with `[REQUIRED:]` placeholders
- [ ] Write validation script matching web-research pattern
- [ ] Implement agent with 5-step workflow
- [ ] Create command wrapper that launches agent
- [ ] Register in `plugin.json`
- [ ] Test with URL input (public repo)
- [ ] Test with path input (local repo)
- [ ] Verify validation catches unfilled placeholders
- [ ] Verify single retry logic works
- [ ] Document in plugin README

## References

- `docs/agent-architecture.md` - Two-layer agent pattern
- `docs/plans/2025-12-05-simplified-web-research-design.md` - Template-copy pattern
- `docs/research/2025-12-05-multi-agent-orchestration-claude-code.md` - Orchestration patterns
- `docs/research/2025-12-05-context-engineering-ai-agents.md` - Token efficiency strategies
- `ai-assisted-development/agents/web-research.md` - Reference implementation
