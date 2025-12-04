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
