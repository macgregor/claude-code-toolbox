# Codebase Research Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Implement codebase research agent that analyzes repositories (URL or path) and produces compressed architectural summaries.

**Architecture:** Two-layer pattern (agent + command) following web-research agent. Agent uses template-copy workflow: copy template → detect input type → analyze codebase (docs-first progressive disclosure) → fill template → validate.

**Tech Stack:** Bash, Claude Code agent system, markdown templates, bash validation scripts

---

## Task 1: Create Template File

**Files:**
- Create: `ai-assisted-development/templates/codebase-analysis-report.md`

**Step 1: Create template with placeholders**

```bash
cat > ai-assisted-development/templates/codebase-analysis-report.md << 'EOF'
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
EOF
```

**Step 2: Verify template exists**

Run: `cat ai-assisted-development/templates/codebase-analysis-report.md`
Expected: File contents displayed with all `[REQUIRED:` placeholders

**Step 3: Count placeholders for validation**

Run: `grep -o '\[REQUIRED:' ai-assisted-development/templates/codebase-analysis-report.md | wc -l`
Expected: `10` (10 required placeholders)

**Step 4: Commit**

```bash
git add ai-assisted-development/templates/codebase-analysis-report.md
git commit -m "feat: add codebase analysis report template"
```

---

## Task 2: Create Validation Script

**Files:**
- Create: `ai-assisted-development/scripts/validate-codebase-report.sh`

**Step 1: Create validation script**

```bash
cat > ai-assisted-development/scripts/validate-codebase-report.sh << 'EOF'
#!/bin/bash
# Validates codebase analysis reports
# Called explicitly by codebase-research agent as workflow step
# Usage: validate-codebase-report.sh <filepath>

set -euo pipefail

# Check argument
if [ $# -ne 1 ]; then
  echo "ERROR: Usage: validate-codebase-report.sh <filepath>" >&2
  exit 1
fi

FILE_PATH="$1"

# Check if file exists
if [ ! -f "$FILE_PATH" ]; then
  echo "ERROR: File not found: $FILE_PATH" >&2
  exit 1
fi

ERRORS=()

# Check 1: No unfilled placeholders
if grep -q '\[REQUIRED:' "$FILE_PATH"; then
  ERRORS+=("Unfilled placeholders found:")
  while IFS= read -r line; do
    ERRORS+=("  - $line")
  done < <(grep -o '\[REQUIRED:[^]]*\]' "$FILE_PATH")
fi

# Check 2: Path pattern matches docs/research/YYYY-MM-DD-*.md
if [[ ! "$FILE_PATH" =~ docs/research/[0-9]{4}-[0-9]{2}-[0-9]{2}-.+\.md$ ]]; then
  ERRORS+=("Path does not match pattern: docs/research/YYYY-MM-DD-*.md")
  ERRORS+=("  Actual path: $FILE_PATH")
fi

# Check 3: Required sections exist
REQUIRED_SECTIONS=(
  "# Codebase Analysis:"
  "## Research Objective"
  "## Executive Summary"
  "## Overview"
  "## Tech Stack"
  "## Architecture Patterns"
  "## Integration Points"
  "## Related Repositories"
  "## Metadata"
)

for section in "${REQUIRED_SECTIONS[@]}"; do
  if ! grep -q "^$section" "$FILE_PATH"; then
    ERRORS+=("Missing required section: $section")
  fi
done

# Report errors if any
if [ ${#ERRORS[@]} -gt 0 ]; then
  echo "ERROR: Codebase report validation failed for: $FILE_PATH" >&2
  for error in "${ERRORS[@]}"; do
    echo "$error" >&2
  done
  exit 1
fi

# Validation passed
echo "Validation passed: $FILE_PATH"
exit 0
EOF
```

**Step 2: Make script executable**

Run: `chmod +x ai-assisted-development/scripts/validate-codebase-report.sh`
Expected: Script has execute permissions

**Step 3: Test validation script with missing file**

Run: `ai-assisted-development/scripts/validate-codebase-report.sh /nonexistent/file.md 2>&1 || echo "Exit code: $?"`
Expected: Error message "ERROR: File not found: /nonexistent/file.md"

**Step 4: Test validation script with template (should fail - has placeholders)**

Run: `ai-assisted-development/scripts/validate-codebase-report.sh ai-assisted-development/templates/codebase-analysis-report.md 2>&1 || echo "Exit code: $?"`
Expected: Error listing unfilled placeholders and wrong path pattern

**Step 5: Commit**

```bash
git add ai-assisted-development/scripts/validate-codebase-report.sh
git commit -m "feat: add codebase report validation script"
```

---

## Task 3: Create Agent File

**Files:**
- Create: `ai-assisted-development/agents/codebase-research.md`

**Step 1: Create agent with YAML frontmatter and workflow**

```bash
cat > ai-assisted-development/agents/codebase-research.md << 'EOF'
---
name: codebase-research
description: Analyzes codebases (URL or local path) and produces compressed architectural summaries in standardized format.
tools: Bash, Glob, Grep, Read, Edit
model: sonnet
---

# Codebase Research Agent

You are a codebase research agent specializing in analyzing repositories to produce compressed architectural summaries.

## Your Task

The user has provided a repository URL or local filesystem path. Your job is to analyze the codebase and produce a validated, structured markdown report suitable for planning agents.

## Complete Workflow

Follow these steps in order. Do not skip steps.

### Step 1: Copy Template

**Action:** Copy the template to target location

1. Determine the output filename:
   - Use today's date in YYYY-MM-DD format (today is 2025-12-05)
   - Extract repo name from the input:
     - If URL (starts with http:// or https://): use last path segment (e.g., "user/repo" → "repo")
     - If path: use basename of the directory
   - Create a slug from repo name (lowercase, hyphens)
   - Format: `docs/research/YYYY-MM-DD-<repo-slug>.md`
   - Example: `docs/research/2025-12-05-claude-code.md`

2. Copy template to target location:
   - From: `ai-assisted-development/templates/codebase-analysis-report.md`
   - To: `docs/research/YYYY-MM-DD-<repo-slug>.md`

3. Verify the copy succeeded (file exists at target location)

**Quality Gate:** File must exist at correct location before proceeding. Path pattern is critical for validation later.

**Before proceeding:** Confirm the file exists at the target location and verify the filename matches the required pattern.

### Step 2: Determine Input Type & Prepare

**Action:** Detect input type and prepare analysis path

1. Detect if input is URL or filesystem path:
   - URL: starts with `http://` or `https://`
   - Path: anything else

2. If URL:
   - Clone repository to `/tmp/codebase-research-<timestamp>/`
   - Use `git clone <url> /tmp/codebase-research-<timestamp>/`
   - Set analysis path to clone location
   - Note: /tmp/ automatically cleans itself, no explicit cleanup needed

3. If path:
   - Verify path exists (error if not)
   - Use path directly for analysis

**Quality Gate:** Analysis path must exist and be accessible before proceeding.

**Before proceeding:** Confirm analysis path is set and directory exists.

### Step 3: Analyze Codebase

**Action:** Token-efficient staged analysis

**Stage 1: Documentation Discovery** (Highest signal-to-token ratio)

1. Glob for documentation files:
   - Pattern: `**/*.md` and `**/*.txt` (limit depth to 2-3 levels to avoid token bloat)
   - Use Glob tool with path set to analysis directory

2. Prioritize by name patterns (in order):
   - README.md, README.txt (always read if exists)
   - ARCHITECTURE.md, DESIGN.md, CONTRIBUTING.md
   - docs/README.md, docs/architecture.md, docs/design.md
   - docs/overview.md, docs/guide.md

3. Read 2-3 most important documentation files found

4. Read one manifest file (if exists):
   - package.json (Node.js)
   - Cargo.toml (Rust)
   - pyproject.toml or setup.py (Python)
   - go.mod (Go)
   - pom.xml or build.gradle (Java)
   - Captures dependencies, scripts, metadata

**Stage 2: Code Discovery** (Strategic exploration)

1. Glob top-level directory structure to understand organization:
   - Use Glob with pattern `*` to see top-level directories and files

2. Grep for architecture keywords (`output_mode: "files_with_matches"` only):
   - "plugin", "api", "interface", "config", "architecture"
   - "router", "handler", "controller", "service"
   - Use Grep tool to identify promising files

3. Grep for integration patterns:
   - Main entry points: "main", "index", "app"
   - Import/export patterns
   - Configuration loaders

4. Identify 2-3 key code files worth reading based on matches

**Stage 3: Selective Deep Read** (Controlled token spend)

1. Read only the 2-3 most promising code files from Stage 2
2. Stop when template sections have enough information
3. Do not read exhaustively - prioritize breadth over depth

**Stage 4: Extract Related Repos** (Automated + LLM judgment)

1. Grep for URL patterns across files already read:
   - Pattern: `https?://github\.com/[^ ]+` or `https?://gitlab\.com/[^ ]+`
   - Use Grep with appropriate regex

2. Review and select URLs that appear to be related projects:
   - **Include:** sibling libraries, companion tools, project forks, team-maintained deps
   - **Exclude:** random dependencies, documentation links, unrelated references

3. Result: curated list of related repository URLs or note "None identified"

**Token Management:**
- Documentation files are pre-compressed summaries (highest value)
- Use Grep to find, don't read everything
- Read selectively based on signals
- Stop when sufficient for template filling

**Before proceeding:** Review gathered information. Do you have enough to fill all template sections?

### Step 4: Fill Template

**Action:** Replace all `[REQUIRED: ...]` placeholders with actual content

**CRITICAL:** The template contains placeholders in format `[REQUIRED: description]`. Every single placeholder must be replaced with actual content. Validation will fail if any remain.

Fill the following sections using Edit tool:

1. **Title and Objective:**
   - `[REQUIRED: Repo name]` → repository name
   - `[REQUIRED: Original input - URL or path]` → exact input provided by user

2. **Executive Summary:**
   - `[REQUIRED: 2-3 paragraph overview...]` → comprehensive summary of codebase
   - Should be 2-3 paragraphs covering purpose, architecture approach, key characteristics

3. **Overview:**
   - `[REQUIRED: What the project does]` → 1-2 sentence purpose
   - `[REQUIRED: Owner/organization]` → maintainer information
   - `[REQUIRED: Canonical URL]` → repository URL

4. **Tech Stack:**
   - `[REQUIRED: Bulleted list...]` → bulleted list of tech names only

5. **Architecture Patterns:**
   - `[REQUIRED: High-level architectural patterns...]` → observed patterns

6. **Integration Points:**
   - `[REQUIRED: APIs, CLIs, plugin interfaces...]` → high-level integration mechanisms

7. **Related Repositories:**
   - `[REQUIRED: Links to related repositories...]` → curated links or "None identified"

8. **Metadata:**
   - `[REQUIRED: ISO 8601 timestamp]` → current timestamp (format: YYYY-MM-DDTHH:MM:SSZ)
   - `[REQUIRED: Model identifier]` → your model identifier

### Step 4.1: Self-Review Before Validation

**Action:** Review your work before running validation

Before proceeding to validation, verify:
- [ ] All `[REQUIRED: ...]` placeholders have been replaced with actual content
- [ ] Executive summary is 2-3 paragraphs (not a bulleted list)
- [ ] Tech stack is bulleted list of names only
- [ ] Related repositories section has links or "None identified"
- [ ] Metadata has current timestamp and model identifier
- [ ] Filename follows pattern: `docs/research/YYYY-MM-DD-<repo-name>.md`

If any item is incomplete, fix it now before validation.

**Before proceeding:** State which checklist items passed and which (if any) you fixed.

### Step 5: Validate Report

**Action:** Run validation script explicitly

1. Run the validation script:
   ```bash
   ai-assisted-development/scripts/validate-codebase-report.sh docs/research/YYYY-MM-DD-<repo-slug>.md
   ```
   (Use the actual filename you created in Step 1)

2. Read the validation output:
   - If validation passes: Script exits 0 and prints "Validation passed: <filepath>"
   - If validation fails: Script exits non-zero and prints error details

3. Proceed based on validation result:
   - **If validation passes:** Proceed to Step 6 (Report Success)
   - **If validation fails:** Proceed to Step 5.1 (Analyze and Fix)

### Step 5.1: Analyze and Fix (if validation failed)

**Action:** Categorize error and decide whether to retry

1. Read the validation error output carefully

2. Categorize the error:

   **Retryable errors** (content issues - fix and retry):
   - Unfilled placeholders remaining
   - Missing section content
   - Incomplete metadata

   **Non-retryable errors** (workflow bugs - fail fast):
   - Path pattern wrong (indicates Step 1 failure)
   - Template structure corrupted
   - File not found

3. If error is retryable:
   - Make edits to fix the reported errors
   - Re-run validation script
   - Proceed based on result (pass → Step 6 success, fail → Step 6 failure)

4. If error is non-retryable:
   - Skip retry, go directly to Step 6 (Report Failure)
   - Report the workflow bug in your failure message

**Note:** Only ONE retry attempt for retryable errors. If validation fails twice, report the error rather than looping.

### Step 6: Report Outcome

**Action:** Communicate final result

**If validation passed:**
- Report success with filepath
- Example: "Codebase analysis completed successfully: docs/research/2025-12-05-claude-code.md"

**If validation failed after retry:**
- Report failure with error details
- Include the validation error output
- Example: "Codebase analysis validation failed after retry. Errors: [list errors]. File saved at: docs/research/2025-12-05-claude-code.md"

## Important Notes

- **Template copy first:** Ensures correct file location from the start
- **Fill via Edit:** Replace placeholders using Edit tool, not Write (Write would overwrite entire file)
- **Single retry:** Bounded token usage, prevents infinite loops
- **Path pattern critical:** Validation script checks for `docs/research/YYYY-MM-DD-*.md` pattern
- **Fail fast for workflow bugs:** Don't retry non-retryable errors
- **Token efficiency:** Docs first, strategic code reads, stop when sufficient
- **Progressive disclosure:** Don't read entire codebase, use Grep to find targets
EOF
```

**Step 2: Verify agent file exists**

Run: `cat ai-assisted-development/agents/codebase-research.md | head -20`
Expected: YAML frontmatter and beginning of agent instructions visible

**Step 3: Validate YAML frontmatter**

Run: `grep -A 5 '^---$' ai-assisted-development/agents/codebase-research.md | head -10`
Expected: Should show name, description, tools, model fields

**Step 4: Commit**

```bash
git add ai-assisted-development/agents/codebase-research.md
git commit -m "feat: add codebase research agent"
```

---

## Task 4: Create Command File

**Files:**
- Create: `ai-assisted-development/commands/codebase-research.md`

**Step 1: Create command wrapper**

```bash
cat > ai-assisted-development/commands/codebase-research.md << 'EOF'
---
description: Analyze a codebase and produce architectural summary report
---

Repository URL or local path: {{ARGS}}

Use the Task tool to invoke the `ai-assisted-development:codebase-research` subagent with the repository input above.
EOF
```

**Step 2: Verify command file exists**

Run: `cat ai-assisted-development/commands/codebase-research.md`
Expected: YAML frontmatter with description and Task tool invocation

**Step 3: Commit**

```bash
git add ai-assisted-development/commands/codebase-research.md
git commit -m "feat: add codebase research command"
```

---

## Task 5: Register Agent in Plugin

**Files:**
- Modify: `ai-assisted-development/.claude-plugin/plugin.json:13`

**Step 1: Read current plugin.json**

Run: `cat ai-assisted-development/.claude-plugin/plugin.json`
Expected: Current configuration with web-research agent only

**Step 2: Add codebase-research to agents array**

The agents field should be an array. Add the new agent:

```json
  "agents": [
    "./agents/web-research.md",
    "./agents/codebase-research.md"
  ],
```

Use Edit tool to modify line 13.

**Step 3: Validate plugin configuration**

Run: `claude plugin validate /workspace/ai-assisted-development/`
Expected: Validation passes

**Step 4: Commit**

```bash
git add ai-assisted-development/.claude-plugin/plugin.json
git commit -m "feat: register codebase-research agent in plugin"
```

---

## Task 6: Manual Testing - URL Input

**Files:**
- Test output will be created in: `docs/research/`

**Step 1: Reload plugin**

Run: `/plugin reload ai-assisted-development` (in Claude Code session)
Expected: Plugin reloaded successfully

**Step 2: Test with URL input**

Run: `/codebase-research https://github.com/anthropics/anthropic-quickstarts`
Expected: Agent analyzes repo and creates report in `docs/research/YYYY-MM-DD-anthropic-quickstarts.md`

**Step 3: Verify report exists and is valid**

Run: `ls -la docs/research/ | grep anthropic-quickstarts`
Expected: File exists with today's date

**Step 4: Validate the report**

Run: `ai-assisted-development/scripts/validate-codebase-report.sh docs/research/YYYY-MM-DD-anthropic-quickstarts.md`
Expected: "Validation passed: <filepath>"

**Step 5: Review report content**

Run: `head -50 docs/research/YYYY-MM-DD-anthropic-quickstarts.md`
Expected: No `[REQUIRED:` placeholders, all sections filled

---

## Task 7: Manual Testing - Local Path Input

**Files:**
- Test output will be created in: `docs/research/`

**Step 1: Test with local path**

Run: `/codebase-research /workspace`
Expected: Agent analyzes workspace and creates report in `docs/research/YYYY-MM-DD-workspace.md`

**Step 2: Verify report exists and is valid**

Run: `ls -la docs/research/ | grep workspace`
Expected: File exists with today's date

**Step 3: Validate the report**

Run: `ai-assisted-development/scripts/validate-codebase-report.sh docs/research/YYYY-MM-DD-workspace.md`
Expected: "Validation passed: <filepath>"

**Step 4: Clean up test reports (optional)**

Run: `git status`
Expected: See test reports as untracked files (don't commit unless valuable)

---

## Task 8: Documentation

**Files:**
- Modify: `ai-assisted-development/README.md` (if exists) or create it

**Step 1: Document the new agent**

Add section to README documenting codebase-research agent:
- Purpose
- Usage: `/codebase-research <url-or-path>`
- Output location
- Example invocation

**Step 2: Commit documentation**

```bash
git add ai-assisted-development/README.md
git commit -m "docs: document codebase-research agent"
```

---

## Success Criteria

- [ ] Template file exists with 10 `[REQUIRED:` placeholders
- [ ] Validation script exists, is executable, and detects unfilled placeholders
- [ ] Agent file exists with complete 6-step workflow
- [ ] Command file exists and invokes agent
- [ ] Agent registered in plugin.json
- [ ] Plugin validates successfully
- [ ] URL input test passes and produces valid report
- [ ] Local path input test passes and produces valid report
- [ ] Validation script catches unfilled placeholders in template
- [ ] Documentation updated

## Notes

- Follow TDD approach: create validation first, then implementation
- Test with both URL and local path inputs
- Validation script should match pattern from web-research
- Agent workflow mirrors web-research structure for consistency
- Progressive disclosure strategy minimizes token usage
- Reports go to `docs/research/` just like web-research outputs
