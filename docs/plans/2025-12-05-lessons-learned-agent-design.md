# Design: Lessons Learned Agent

## Purpose

The lessons-learned agent analyzes project history to extract actionable patterns and maintain CLAUDE.md quality. It discovers project-specific learnings from git commits and conversation history, then updates CLAUDE.md automatically.

## Core Principles

**Evidence-based**: Every learning cites specific commits or conversation excerpts.

**Project-specific**: Focus on patterns unique to this codebase, not generic advice.

**Concrete over abstract**: Prefer specific examples over high-level principles.

**Conservative updates**: Only add high-confidence learnings.

## Scope Determination

The agent analyzes history since the last CLAUDE.md modification:

1. Check CLAUDE.md modification time: `git log -1 --format=%ct CLAUDE.md`
2. Calculate lookback period: now - last_modified
3. Apply bounds: minimum 30 days, maximum 90 days
4. If CLAUDE.md never modified, default to 30 days

## Data Sources

**Git History**:
- Commits: `git log --since=<timestamp> --format='%H|%an|%at|%s' --no-merges`
- Diffs: `git show <hash>` (batched, 5 per message)
- Categories: features, fixes, refactors, docs, config changes

**Conversation History**:
- Location: `~/.claude/projects/<project-hash>/<session-id>.jsonl`
- Project hash: Derived from `~/.claude/history.jsonl`
- Parse for: error → correction patterns, explicit guidance, repeated issues
- Batch reads: 5 JSONL files per message

## Pattern Extraction

The agent identifies meaningful patterns through these filters:

**Repetition**: Same issue/solution appeared 2+ times

**Explicit correction**: User corrected the agent's approach

**Anti-pattern discovery**: Code written then reverted/refactored

**Architecture decisions**: Changes to design docs or significant refactors

**Tool/workflow learnings**: Better ways to use git, testing, etc.

## Quality Criteria

All criteria must pass:

1. **Evidence threshold**: Must cite specific commit hash or conversation excerpt
2. **Actionability test**: Guidance must be specific enough to follow
3. **Project-specificity**: Must reference actual files, paths, or project tech/patterns
4. **Non-contradiction**: Must not conflict with existing CLAUDE.md
5. **Signal strength**: Pattern appeared 2+ times OR was significant single event

## Project vs Global Classification

**Project-specific signals** (add to project CLAUDE.md):
- References actual repo files (e.g., "devcontainer/entrypoint.sh")
- Mentions project-specific paths ("/workspace/", "~/.claude/plugins/claude-code-toolbox/")
- Refers to project architecture decisions (cites docs/plans/)
- Uses project-specific terminology (e.g., "Podman", "marketplace.json validation")
- Technology choices unique to this project

**Global-leaning signals** (skip, belongs in global CLAUDE.md):
- Generic development practices (TDD principles, git workflows)
- Universal tool usage without project context
- General coding principles (DRY, SOLID, etc.)
- Language-agnostic patterns

**Decision logic**: If 2+ project-specific signals present, classify as project-specific. Otherwise skip.

## CLAUDE.md Inconsistency Resolution

The agent detects and fixes three types of inconsistencies:

### 1. Contradictory Guidance

**Detection**: Cross-reference directive statements for logical conflicts.

**Resolution**:
- Keep more specific guidance over general
- Merge with context if both valid in different scenarios
- Prefer recent evidence over old
- Remove both if unresolvable, add TODO comment for human review

### 2. Outdated References

**Detection**: Verify file/path/tool references exist via filesystem checks.

**Resolution**:
- Remove if obsolete (no replacement found)
- Update path if similar file exists (fuzzy match)
- Mark as deprecated if uncertain

### 3. Vague Guidance

**Detection**: Flag guidance lacking evidence/examples based on context engineering principles.

**Resolution**:
- Add evidence from history (concrete examples from commits/conversations)
- Make specific (transform "be careful with X" into "when doing X, always Y")
- Remove if unsupported by evidence

## Learning Format

Each learning follows this structure:

```markdown
### Pattern: [Brief descriptive title]
**Evidence**: commit [hash] / conversation [date-time]
**Context**: [When/where this applies]
**Guidance**: [Specific actionable instruction]
**Example**: [Optional - concrete code/file reference]
```

Example:

```markdown
### Pattern: Plugin path references must be relative
**Evidence**: commit f02da8a, commit 8355d5b
**Context**: When writing agent definitions in ai-assisted-development/agents/
**Guidance**: Always use relative paths from plugin root (e.g., "templates/report.md"), never absolute paths like "/workspace/templates/report.md" which break when installed
**Example**: See ai-assisted-development/agents/web-research.md:32 for correct pattern
```

## Update Strategy

**Content Organization**:
1. Match learning category to existing CLAUDE.md structure
2. Append to existing section or create new section
3. Maintain alphabetical or logical ordering within sections
4. Preserve existing style and formatting

**Deduplication**:
- Check if similar guidance exists before adding
- If exists: enhance existing entry with new evidence
- If new angle: add as separate pattern

**Execution Steps**:
1. Read current CLAUDE.md
2. Apply inconsistency fixes (one Edit per fix)
3. Determine insertion points for new learnings
4. Insert learnings maintaining existing style
5. Write updated CLAUDE.md
6. Show changes: `git diff CLAUDE.md`

## Workflow

### Step 1: Initialize and Determine Scope
1. Get CLAUDE.md last modified time
2. Calculate lookback period
3. Get current project path
4. Derive project hash from ~/.claude/history.jsonl
5. Set time window variables

### Step 2: Gather Git Evidence
1. Collect commits within time window
2. Batch git show calls (5 commits per message)
3. Parse diffs to identify file changes, fixes, refactors
4. Build commit evidence database

### Step 3: Gather Conversation Evidence
1. Find session JSONL files within time window
2. Read JSONL files in batches (5 per message)
3. Parse for error-correction patterns and repeated issues
4. Build conversation evidence database

### Step 4: Extract and Filter Patterns
1. Cross-reference git and conversation evidence
2. Apply quality criteria
3. Classify as project-specific or global
4. Deduplicate similar patterns
5. Build candidate learnings list

### Step 5: Analyze CLAUDE.md for Inconsistencies
1. Read current CLAUDE.md
2. Parse into sections and extract directives
3. Run three consistency checks
4. Determine fix strategy for each issue
5. Build fixes list

### Step 6: Apply Updates
1. Read CLAUDE.md fresh
2. Apply inconsistency fixes (one Edit per fix)
3. Determine insertion points for new learnings
4. Insert new learnings using Edit tool
5. Validate final formatting

### Step 7: Report Changes
1. Run `git diff CLAUDE.md`
2. Summarize:
   - Inconsistencies fixed (by type)
   - New learnings added (by category)
   - Evidence sources used

## Error Handling

**Missing/Corrupt Conversation History**:
- Fall back to git-only analysis
- Log warning about limited evidence

**CLAUDE.md Parse Failures**:
- Use conservative Edit operations
- Preserve unknown sections as-is
- Only modify what we understand

**Contradictions Can't Be Resolved**:
- Add comment flag for human review
- Include commit references for context

**No Learnings Found**:
- Exit gracefully
- Don't modify CLAUDE.md
- Report "No new learnings identified since [date]"

**Git Repository Issues**:
- Detect with `git rev-parse --is-inside-work-tree`
- Exit with clear error message

## Edge Cases

**Brand New Project (no CLAUDE.md)**:
- Skip inconsistency checking
- Create new CLAUDE.md with template structure

**Very Active Project (1000s of commits)**:
- Respect time window strictly
- Sample commits if > 500 (every Nth commit)

**Multiple CLAUDE.md Files**:
- Prefer ./CLAUDE.md (root level)
- Only process one file

**CLAUDE.md Modified During Agent Run**:
- Check modification time before final write
- Warn if changed externally

## Context Engineering Integration

The agent embeds these principles:

**High-Signal Token Selection**:
- Focus on concrete, actionable patterns
- Prefer specific file references and commit hashes
- Avoid vague guidance

**Just-In-Time Context Loading**:
- Load evidence incrementally
- Summarize commits first, fetch diffs only for significant changes
- Batch operations to minimize context switching

**Examples Over Explanations**:
- Every learning includes concrete examples from the codebase
- Reference real files, commits, patterns
- Cite specific line numbers and file paths

**Tool Design Principles**:
- Self-contained (no external configuration)
- Token-efficient (batch operations, parallel execution)
- Clear error messages
- Robust to errors (graceful degradation)

**Quality Gates**:
- Step 1: Confirm time window calculated
- Step 2: Verify commits/conversations found
- Step 3: Confirm patterns meet quality criteria
- Step 4: Validate fixes don't introduce new issues
- Step 5: Check CLAUDE.md structure maintained

## Agent Metadata

```yaml
name: lessons-learned
description: Analyzes project history to extract learnings and maintain CLAUDE.md quality
tools: Bash, Glob, Grep, Read, Write, Edit
model: sonnet
```

**Model choice**: Sonnet required for complex pattern recognition, nuanced judgment about contradictions, sophisticated conversation analysis, and critical documentation updates.

## Performance Optimizations

- Parallel tool execution (multiple git show, multiple file reads)
- Batch operations (5 items per message)
- Minimal context loading (summarize before detailed analysis)
