# Web Research Agent Design

## Overview

A specialized research agent for Claude Code that performs web-based research on codebases, documentation, and general internet sources to produce structured research documents for decision-making and future reference.

## Scope

### In Scope
- Web-based research (WebSearch, WebFetch)
- Official documentation gathering
- Source code repository analysis (README, key docs only)
- Community/third-party resources
- Structured markdown report generation
- Standardized metadata format

### Out of Scope (for MVP)
- Local codebase analysis (Glob/Grep)
- Deep code analysis of external repositories
- Comparative code pattern analysis

## Architecture

### Three-Layer Structure

1. **Skill** (`skills/web-research/SKILL.md`): Core research logic and instructions
2. **Agent** (`agents/web-research.md`): Thin wrapper for Task tool delegation
3. **Slash Command** (`commands/web-research.md`): Thin wrapper for interactive use

The skill contains the research logic. The agent and command delegate to it through different invocation mechanisms.

### Template & Validation

- **Template**: `templates/web-research-report.md` - Markdown template with required sections
- **Validation Script**: `scripts/validate-research-report.sh` - Validates completed reports
- **Hook**: PostToolUse Write hook runs validation script
- **Unique Identifier**: `web-research-agent-v1-7k9p3x2m` embedded in metadata for reliable detection

### Validation Flow

1. Any Write operation triggers hook
2. Script checks for unique identifier in file content
3. If present, validates:
   - Path matches `docs/research/YYYY-MM-DD-*.md`
   - Filename follows date-topic convention
   - All required sections present
   - All sources have required metadata fields
4. If validation fails, return error to agent
5. Agent fixes and retries

## Research Process

When invoked, the web-research skill follows this structured process:

1. **Initialize**: Load template, understand research objective
2. **Codebase exploration**: SKIPPED in MVP (web-only focus)
3. **Web research**:
   - WebSearch for official docs, recent articles
   - WebFetch for specific URLs
   - Repository analysis limited to README and key docs
4. **Synthesize**: Organize findings by source type with standardized metadata
5. **Document**: Fill template sections, write to `docs/research/YYYY-MM-DD-<topic>.md`
6. **Validate**: Hook checks format, agent fixes if needed

### Time-boxing

Agent works efficiently, gathering comprehensive but not exhaustive sources. Target: 5-10 high-quality sources per category.

## Document Format

### Source Type Categories

Findings organized into:
- **Official Documentation**: Vendor docs, official guides
- **Source Code Repositories**: GitHub/GitLab projects (README + key docs only)
- **Community/Third-party**: Blog posts, tutorials, Stack Overflow

### Standard Metadata (All Sources)

- **Source**: [Title] - [URL]
- **Author**: [Person/organization/vendor]
- **Date**: [Last updated/published]
- **Activity**: [For repos: stars + recent commit; for others: N/A]
- **Key points**: [Bullets]

Same fields, same order, every source for easy comparison.

### Complete Template Structure

```markdown
# Research: [Topic]

## Research Objective
[The research goal as provided]

## Executive Summary
[2-3 paragraph overview of key findings]

## Findings

### Official Documentation

- **Source**: [Title] - [URL]
  **Author**: [Person/organization/vendor]
  **Date**: [Last updated/published]
  **Activity**: N/A
  **Key points**:
    - [Bullet point]

### Source Code Repositories

- **Source**: [Repository name] - [URL]
  **Author**: [Person/organization]
  **Date**: [Last updated]
  **Activity**: [Stars/downloads + last commit date]
  **Key points**:
    - [Bullet point]

### Community/Third-party

- **Source**: [Title] - [URL]
  **Author**: [Person/organization]
  **Date**: [Published/updated date]
  **Activity**: N/A
  **Key points**:
    - [Bullet point]

## Sources
[Complete list of all URLs/documents consulted]
- [URL 1]
- [URL 2]

## Metadata
- **agent-type**: web-research-agent-v1-7k9p3x2m
- **Research Date**: [ISO timestamp]
- **Search Queries**: [Comma-separated list]
- **Agent Model**: [Model name]
```

### Validation Checks

- All section headers present
- At least one finding per category (or explicit "None found")
- All sources have: Source, Author, Date, Activity, Key points
- Sources section populated
- Metadata complete

## File Organization

```
skills/web-research/
  SKILL.md                       # Core research instructions
agents/
  web-research.md                # Agent wrapper
commands/
  web-research.md                # Slash command wrapper
templates/
  web-research-report.md         # Empty template
scripts/
  validate-research-report.sh    # Validation script
hooks/
  hooks.json                     # Hook configuration (updated)
docs/research/                   # Output directory
  YYYY-MM-DD-<topic>.md         # Research reports
```

## Naming and Namespacing

- **Plugin name**: `claude-code-toolbox`
- **Skill name**: `web-research`
- **Full reference**: `claude-code-toolbox:web-research`
- **Agent name**: `web-research`
- **Command**: `/web-research`

Always reference the skill with namespace to avoid conflicts with other plugins.

## Implementation Details

### Skill File (`skills/web-research/SKILL.md`)

```yaml
---
name: web-research
description: Use for web-based research on best practices, documentation, and code examples - produces structured reports for decision-making. Don't use for local codebase analysis
allowed-tools: WebSearch, WebFetch, Read, Write
---

# Web Research Skill

## Overview
Conducts web-based research to gather best practices, documentation, and examples. Produces structured markdown reports with standardized metadata for decision-making and future reference.

## Process

### 1. Initialize
- Read the template from `./templates/web-research-report.md`
- Understand the research objective clearly

### 2. Web Research
- Use WebSearch to find official docs, recent articles, best practices
- Use WebFetch to read specific URLs (documentation pages, READMEs)
- For repositories: Focus on README, main documentation, example code only
- DO NOT attempt deep codebase analysis or local file exploration

### 3. Organize Findings
Group findings by source type using standardized metadata:
- Official Documentation
- Source Code Repositories
- Community/Third-party

For each source, capture:
- **Source**: [Title] - [URL]
- **Author**: [Person/organization]
- **Date**: [Last updated/published]
- **Activity**: [Stars/commits for repos, N/A for docs]
- **Key points**: [Bullets]

### 4. Write Report
- Fill all template sections
- Save to `docs/research/YYYY-MM-DD-<topic-slug>.md`
- CRITICAL: The template includes `**agent-type**: web-research-agent-v1-7k9p3x2m` - keep this exact identifier

### 5. Efficiency Guidelines
- Work efficiently - comprehensive but not exhaustive
- Target 5-10 high-quality sources per category
- Stop when sufficient information gathered for decision-making
```

### Agent File (`agents/web-research.md`)

```yaml
---
name: web-research
description: Web-based research agent for gathering best practices, documentation, and code examples. Returns structured research reports.
tools: WebSearch, WebFetch, Read, Write
model: haiku
skills: claude-code-toolbox:web-research
---

You are a web research agent specializing in gathering information from online sources.

Your task is to execute the claude-code-toolbox:web-research skill with the provided research objective. Follow the skill's instructions precisely to produce a structured research report.

Focus on finding high-quality, relevant sources and organizing them clearly.
```

### Command File (`commands/web-research.md`)

```markdown
Use the claude-code-toolbox:web-research skill to investigate: {{ARGS}}
```

### Hook Configuration

Add to `hooks/hooks.json`:
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write",
      "hooks": [{
        "type": "command",
        "command": "scripts/validate-research-report.sh"
      }]
    }]
  }
}
```

### Validation Script Logic

```bash
#!/bin/bash
# scripts/validate-research-report.sh

FILEPATH="$1"

# Check for unique identifier
if ! grep -q "agent-type.*web-research-agent-v1-7k9p3x2m" "$FILEPATH"; then
  # Not a research report, exit silently
  exit 0
fi

# It's a research report - validate:
# 1. Path matches docs/research/YYYY-MM-DD-*.md
# 2. All required sections present
# 3. All sources have required metadata fields
# On failure: output JSON error and exit non-zero
```

## Design Rationale

### Why Web-Only for MVP?

Bootstrapping requires learning from the Claude Code ecosystem and foundation model patterns. No local code exists yet to learn from. Build codebase-focused researchers after establishing reliable agent workflows.

### Why Three-Layer Architecture?

The skill contains core logic. The agent wrapper enables autonomous research via Task tool delegation. The command wrapper enables interactive use. The skill serves as a reusable building block for future agent coordination.

### Why Template + Hook Validation?

Minimizes context engineering. Template makes format constraints explicit. Hook validation ensures compliance without relying on prompting. Agent receives concrete errors and fixes them.

### Why Content-Based Detection?

Hooks don't receive agent identity information. Content-based detection with a unique identifier reliably identifies research reports regardless of location or author.

### Why Standardized Metadata?

Makes sources easier to compare. Supports future analysis and tooling. Consistent structure enables programmatic processing later.

## Future Iterations

Potential enhancements (not in MVP):

- Local codebase research capability
- Deeper code analysis of external repos
- Quality scoring/ranking of sources
- Research report comparison/diffing
- Integration with planning agents
- Automated research scheduling
- Source credibility assessment
