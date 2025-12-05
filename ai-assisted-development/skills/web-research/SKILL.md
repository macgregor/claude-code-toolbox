---
name: web-research
description: Use for web-based research on best practices, documentation, and code examples - produces structured reports for decision-making. Don't use for local codebase analysis
allowed-tools: WebSearch, WebFetch, Read, Write
---

# Web Research Skill

## Overview
Conducts web-based research to gather best practices, documentation, and examples. Produces structured markdown reports with standardized metadata for decision-making and future reference.

## Process

This is a multi-stage workflow with quality gates. You MUST complete each stage before proceeding to the next.

### STAGE 1: INITIALIZE (MANDATORY - DO NOT SKIP)

**YOU MUST COMPLETE THIS STAGE FIRST**

1. Use the Read tool to read the template file at `ai-assisted-development/skills/web-research/templates/web-research-report.md`
2. Extract and preserve these CRITICAL values from the template:
   - **agent-type identifier**: Look for the line `- **agent-type**: web-research-agent-v1-7k9p3x2m`
   - **File path pattern**: `docs/research/YYYY-MM-DD-<topic>.md`
   - **Required sections**: Note all section headers (## and ###)
3. Understand the research objective clearly

**Quality Gate**: You cannot proceed to Stage 2 without reading the template and capturing the agent-type identifier. If you skip this step, the validation hook will not recognize your report and will not provide feedback.

### STAGE 2: WEB RESEARCH

Execute web research efficiently:
- Use WebSearch to find official docs, recent articles, best practices
- Use WebFetch to read specific URLs (documentation pages, READMEs)
- For repositories: Focus on README, main documentation, example code only
- DO NOT attempt deep codebase analysis or local file exploration

Efficiency guidelines:
- Work efficiently - comprehensive but not exhaustive
- Target 5-10 high-quality sources per category
- Stop when sufficient information gathered for decision-making

### STAGE 3: ORGANIZE FINDINGS

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

### STAGE 4: WRITE REPORT

1. Fill all template sections
2. Save to `docs/research/YYYY-MM-DD-<topic-slug>.md` where:
   - YYYY-MM-DD is today's date
   - <topic-slug> is a brief hyphenated description of the research topic
3. CRITICAL: Include the EXACT agent-type identifier you extracted in Stage 1: `**agent-type**: web-research-agent-v1-7k9p3x2m`
4. Ensure all required sections from the template are present

**Quality Gate**: After writing, a validation hook will check:
- File path matches `docs/research/YYYY-MM-DD-*.md`
- All required sections are present
- The agent-type identifier is correct
- All metadata fields are complete

If validation fails, you will receive an error message. Fix the issues and retry.
