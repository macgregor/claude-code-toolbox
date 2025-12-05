# AI-Assisted Development Plugin

This Claude Code plugin provides research agents that gather information and produce structured, validated reports for development planning.

## Agents

### Web Research Agent

**Purpose:** Conducts web-based research on technical topics and produces structured reports with validation. Gathers best practices, documentation, and code examples from online sources.

**Usage:**
```
/web-research <research-objective>
```

**Examples:**
```
/web-research How to implement multi-agent orchestration patterns in CLI tools
/web-research Best practices for plugin systems in TypeScript
/web-research Error handling patterns in Rust applications
```

**Output Location:** `docs/research/YYYY-MM-DD-<topic-slug>.md`

The agent:
- Conducts comprehensive web searches
- Fetches and analyzes relevant documentation
- Synthesizes findings into a structured report
- Validates the report against template requirements
- Saves to `docs/research/` with dated filename

### Codebase Research Agent

**Purpose:** Analyzes codebases (from URL or local filesystem path) and produces compressed architectural summaries. Uses token-efficient progressive disclosure strategy (documentation-first, then targeted code exploration).

**Usage:**
```
/codebase-research <repository-url-or-path>
```

**Examples:**
```
/codebase-research https://github.com/anthropics/anthropic-quickstarts
/codebase-research https://github.com/organization/project
/codebase-research /workspace
/codebase-research /path/to/local/repository
```

**Output Location:** `docs/research/YYYY-MM-DD-<repo-name>.md`

The agent:
- Detects whether input is a URL or filesystem path
- Clones remote repositories to `/tmp/` for analysis
- Analyzes documentation first (highest signal-to-token ratio)
- Strategically explores code using Grep/Glob
- Extracts architecture patterns, tech stack, integration points
- Identifies related repositories
- Validates the report against template requirements
- Saves to `docs/research/` with dated filename

**Analysis Strategy:**
1. Documentation discovery (README, ARCHITECTURE, docs/)
2. Manifest file analysis (package.json, Cargo.toml, etc.)
3. Strategic code exploration via keyword search
4. Selective deep reads of 2-3 key files
5. Related repository extraction

## Report Format

Both agents produce markdown reports in `docs/research/` following standardized templates:
- Web research reports: Objective, findings by source, synthesis, key takeaways
- Codebase analysis reports: Executive summary, tech stack, architecture patterns, integration points

All reports include:
- Metadata (timestamp, model identifier)
- Source attribution
- Structured sections
- Validation checkpoints

## Validation

Each agent includes validation scripts that verify:
- No unfilled template placeholders
- Required sections present
- Correct file naming pattern
- Structural integrity

Validation runs automatically as part of the agent workflow.
