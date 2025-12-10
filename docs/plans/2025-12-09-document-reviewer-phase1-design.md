# Document Reviewer Agent - Phase 1 Design

**Date**: 2025-12-09
**Status**: Design Complete
**Phase**: 1 of 3 (Read-Only Analysis)

## Overview

A read-only document analysis agent that reviews a single markdown document across quality dimensions and produces a structured JSON report identifying issues with confidence-scored recommendations.

**Phase Scope:**
- **Phase 1 (this)**: Analyze → Report (read-only)
- **Phase 2 (future)**: Report → Fix (write-only refiner agent)
- **Phase 3 (future)**: Orchestrate review-fix loop

## Problem Statement

Creating and maintaining high-quality documentation is time-consuming:
- Initial generation produces bloated, poorly structured docs
- Manual refinement takes 3+ passes to reach acceptable quality
- Cross-document consistency requires manual checking
- Docs become stale as code evolves

**Current pain points:**
- Long prompts with lots of context still produce poor initial drafts
- Conflicting objectives (comprehensive vs concise) in single prompt
- Context pollution mixing creation and review concerns
- Manual effort to check accuracy, consistency, cross-references

**Solution approach:**
- Separate analysis (this phase) from fixing (Phase 2)
- Automated quality assessment with confidence scoring
- Structured output for future automation
- Portable plugin working across repos

## Design Decisions

### Core Architecture

**Agent Type**: Read-only analysis agent
**Model**: Sonnet - Analysis/validation task requiring judgment and reasoning
**Tools**: Read, Grep, Glob, WebFetch

**Tool rationale:**
- **Read**: Load document and related files for analysis
- **Grep/Glob**: Discover related documents, verify code references
- **WebFetch**: Validate external links
- **NO Edit**: Read-only agent (Phase 2 will handle fixes)
- **NO AskUserQuestion**: Automated analysis (low confidence → flag in report)

**Why Sonnet:**
- Analysis/validation task requiring judgment
- Per docs/claude-code-agent-considerations.md:148-152: "Sonnet for planning, review, complex reasoning, validation"

### Agent Metadata

```yaml
---
name: document-reviewer
description: Analyzes document quality including clarity, accuracy, consistency, cross-references, and markdown formatting. Produces JSON report with confidence-scored recommendations. Read-only analysis only.
model: sonnet
tools: [Read, Grep, Glob, WebFetch]
---
```

**Description design:**
- Lists general categories without exact counts (won't go stale)
- Emphasizes read-only nature
- Clear about output format (JSON report)

### Input Parameters

**Required:**
- `document_path`: Absolute or relative path to markdown document to review

**Optional:**
- `verification_depth`: `"quick"` | `"standard"` | `"thorough"` (default: `"standard"`)

**Parameter parsing examples:**
- "Review docs/architecture.md" → `document_path="docs/architecture.md"`, `verification_depth="standard"`
- "Quick review of README.md" → `document_path="README.md"`, `verification_depth="quick"`
- "Thorough review of docs/api.md" → `document_path="docs/api.md"`, `verification_depth="thorough"`

### Output Contract

#### JSON Report Structure

**File location:** `/tmp/document-reviews/{basename}-{date}-{time}.json`

**Example:** `/tmp/document-reviews/architecture-2025-12-09-143022.json`

**Rationale for `/tmp/`:**
- Plugin portability (works across any repo)
- No `.gitignore` setup needed per-repo
- Auto-cleanup (system handles temp files)
- Reports are ephemeral working artifacts, not documentation to preserve

**Schema:**
```json
{
  "document": "docs/architecture.md",
  "reviewed_at": "2025-12-09T14:30:22Z",
  "verification_depth": "standard",
  "summary": {
    "total_issues": 12,
    "high_confidence_fixes": 8,
    "needs_manual_review": 4,
    "overall_quality_score": 7.5
  },
  "issues": [
    {
      "id": "clarity-001",
      "line": 42,
      "category": "clarity",
      "subcategory": "passive_voice",
      "severity": "minor",
      "confidence": "high",
      "current_text": "Requests are processed by the system",
      "suggested_fix": "The system processes requests",
      "reasoning": "Active voice is clearer and more direct"
    },
    {
      "id": "cross-ref-002",
      "lines": [88, 92],
      "category": "cross_reference",
      "subcategory": "unclear_source_of_truth",
      "confidence": "low",
      "current_text": "Similar content in design.md and tutorial.md",
      "suggested_fix": null,
      "reasoning": "Both documents equally authoritative - manual decision needed"
    }
  ],
  "scores_by_category": {
    "clarity": 7.5,
    "accuracy": 9.0,
    "consistency": 8.0,
    "redundancy": 6.5,
    "cross_references": 7.0,
    "detail_level": 8.5,
    "markdown": 9.5
  }
}
```

#### Final Message to User

**Format:**
```
Review complete: {document_path}
Report: {json_file_path}
```

**Rationale:**
- Minimal, actionable output
- No redundant summary (everything in JSON)
- Clear next step (check the report)

### Confidence Scoring

**Three-tier system**: `"high"` | `"medium"` | `"low"`

**Why three-tier:**
- More nuanced than binary without false precision of numeric scores
- Natural categorization for future automation
- Clear decision boundaries

**Confidence principles** (not exhaustive mappings):

**"high" confidence when:**
- Fix is mechanical/deterministic (regex pattern → replacement)
- No domain knowledge needed
- Verifiable against external source (file exists, link returns 200)
- Clear community standard (active voice, consistent terminology)

**"medium" confidence when:**
- Fix is likely correct but has stylistic element
- Multiple valid approaches exist
- Requires light interpretation of context
- Best practice but not absolute rule

**"low" confidence when:**
- Requires domain/business knowledge
- Multiple sources have conflicting information
- Subjective judgment call
- User context needed to determine correct fix

**Future refiner agent can:**
- Auto-apply "high" confidence fixes
- Prompt user for "medium" confidence fixes
- Skip "low" confidence fixes (manual review)

## Three-Phase Workflow

### Phase 1: Context Discovery

**Goal:** Understand document's purpose, relationships, and code references before analysis.

**Steps:**

1. **Read target document**
   - Load full content using Read tool
   - Extract frontmatter metadata if present (type, audience, purpose)
   - If no frontmatter: Infer type from file path/content structure

2. **Discover document relationships** (parallel execution)
   - Grep: Find documents that link TO this one
   - Parse document: Extract links FROM this document
   - Identify related documents via similar topics

3. **Identify code references** (if applicable)
   - Extract mentioned file paths, function/class names
   - Use Glob/Grep to verify references exist in codebase
   - Note which references are current vs outdated/missing

**Output:** Internal context model for analysis

### Phase 2: Quality Analysis

**Goal:** Systematically evaluate document across quality dimensions with confidence scoring.

**Verification depth behavior:**
- **quick**: Surface checks (paths exist, links valid, obvious issues)
- **standard**: Semantic checks (read referenced files, verify signatures)
- **thorough**: Deep analysis (code logic verification, comprehensive cross-checking)

**Analysis produces:**
- List of issues with confidence scores
- Specific recommendations for high-confidence issues
- Flags for low-confidence issues needing manual review
- Per-category quality scores (0-10 scale)

### Phase 3: Report Generation

**Goal:** Produce structured JSON report and save to temp location.

**Steps:**

1. **Calculate scores**
   - Overall quality score (weighted average of categories)
   - Per-category scores
   - Count high-confidence vs needs-review issues

2. **Write JSON report**
   - Create `/tmp/document-reviews/` directory if needed
   - Generate filename: `{basename}-{date}-{time}.json`
   - Write structured JSON with all findings

3. **Return summary message**
   - Document path
   - Report file path

## Quality Analysis Dimensions

### Dimension 1: Clarity & Conciseness

**Checks:**
- Passive voice constructions → Active voice alternatives
- Complex sentences (>25-30 words) → Break points identified
- Vague pronouns ("it", "this", "that") → Specific noun replacements
- Verbose phrasing ("in order to" → "to")
- Undefined jargon on first use → Suggest inline definition
- Long paragraphs (>150 words) → Logical break points
- Unclear headings → More descriptive alternatives

**Example issues:**
```json
{
  "id": "clarity-001",
  "line": 42,
  "category": "clarity",
  "subcategory": "passive_voice",
  "confidence": "high",
  "current_text": "Requests are processed by the system",
  "suggested_fix": "The system processes requests",
  "reasoning": "Active voice is clearer and more direct"
},
{
  "id": "clarity-002",
  "line": 58,
  "category": "clarity",
  "subcategory": "complex_sentence",
  "confidence": "medium",
  "current_text": "...(35 words)...",
  "suggested_fix": "Break at 'however' into 2 sentences",
  "reasoning": "Long sentences reduce readability"
}
```

### Dimension 2: Accuracy Verification

**Depth-dependent checks:**

**Quick:**
- File paths exist (Glob)
- Function/class names found (Grep)
- External links return 200 (WebFetch with timeout handling)

**Standard (includes Quick +):**
- Read referenced source files
- Verify function signatures match documentation
- Check code comments align with descriptions

**Thorough (includes Standard +):**
- Analyze code logic vs documented behavior
- Trace execution paths for workflow docs
- Deep cross-reference validation

**Example issues:**
```json
{
  "id": "accuracy-001",
  "line": 85,
  "category": "accuracy",
  "subcategory": "outdated_reference",
  "confidence": "high",
  "current_text": "See processRequest() in handlers.js",
  "suggested_fix": "See processRequest() in src/api/handlers.ts",
  "reasoning": "File moved from handlers.js to src/api/handlers.ts"
}
```

### Dimension 3: Internal Consistency

**Checks:**
- Contradictory statements within document
- Terminology inconsistency (normalize to most common variant)
- Inconsistent capitalization ("GitHub" vs "github")
- Mixed British/American spelling
- Examples contradicting stated principles

**Example issue:**
```json
{
  "id": "consistency-001",
  "lines": [12, 45, 78],
  "category": "consistency",
  "subcategory": "terminology",
  "confidence": "high",
  "current_text": "Uses 'subagent' (2x), 'sub-agent' (1x)",
  "suggested_fix": "Normalize to 'subagent' (most common)",
  "reasoning": "Inconsistent terminology reduces clarity"
}
```

### Dimension 4: Redundancy Elimination

**Checks:**
- Repeated information within same document
- Sections conveying same information differently
- Duplicate examples

**Example issue:**
```json
{
  "id": "redundancy-001",
  "lines": [45, 203],
  "category": "redundancy",
  "subcategory": "duplicate_content",
  "confidence": "high",
  "current_text": "Section 3.2 and 8.1 contain identical explanation of agent workflow",
  "suggested_fix": "Remove duplicate in section 8.1, reference section 3.2",
  "reasoning": "Exact duplication reduces maintainability"
}
```

### Dimension 5: Cross-Reference Validation (DRY)

**Checks:**
- Content duplicated across multiple documents
- Determine source-of-truth using heuristics:
  - Document type/purpose (specialized > general)
  - Depth of coverage (detailed > brief)
  - Recency (recently updated > stale)
  - Explicit frontmatter claim (`source-of-truth-for: [topic]`)

**Example issues:**
```json
{
  "id": "cross-ref-001",
  "lines": [200, 215],
  "category": "cross_reference",
  "subcategory": "duplicate_content",
  "confidence": "high",
  "current_text": "Lines 200-215 duplicate architecture.md sections 3-4",
  "suggested_fix": "Replace with: 'See [Agent Patterns](architecture.md#agent-patterns)'",
  "reasoning": "architecture.md is source-of-truth: specialized doc, more detailed, recently updated"
},
{
  "id": "cross-ref-002",
  "lines": [88, 92],
  "category": "cross_reference",
  "subcategory": "unclear_source_of_truth",
  "confidence": "low",
  "current_text": "Similar content in design.md and tutorial.md",
  "suggested_fix": null,
  "reasoning": "Both documents equally authoritative - manual decision needed"
}
```

### Dimension 6: Appropriate Detail Level

**Checks:**
- Validate detail matches document type (architecture/API/research/design/README)
- Diagram quality: Does it illustrate complex relationships or just decorate?

**Document type expectations:**
- **Architecture docs**: High-level design, NOT implementation details
- **API docs**: Signatures, parameters, usage examples required
- **Research docs**: Findings, sources, analysis - NOT implementation
- **Design docs**: Approach, trade-offs - NOT step-by-step code
- **README/Getting Started**: Setup/usage examples required

**Diagram quality heuristics:**
- Single-node diagrams → Likely unnecessary
- Lists without relationships → Should be bullet list
- Diagrams duplicating clear text → Redundant
- Complex flows/architecture → Keep these

**Example issues:**
```json
{
  "id": "detail-001",
  "lines": [120, 145],
  "category": "detail_level",
  "subcategory": "excessive_detail",
  "confidence": "high",
  "current_text": "Architecture doc contains 25 lines of implementation code",
  "suggested_fix": "Move code example to appendix or implementation guide",
  "reasoning": "Architecture docs should focus on high-level design, not code"
},
{
  "id": "detail-002",
  "lines": [88, 92],
  "category": "detail_level",
  "subcategory": "low_value_diagram",
  "confidence": "medium",
  "current_text": "Mermaid diagram shows simple linear flow already described in text",
  "suggested_fix": "Remove diagram - adds no value beyond text",
  "reasoning": "Diagram duplicates clear text explanation"
}
```

### Dimension 7: Markdown Rendering Issues

**Checks:**
- Multi-line lists without blank lines
- Broken internal links (file doesn't exist)
- Broken external links (WebFetch validation)
- Code blocks missing language identifiers
- Malformed tables/lists/headers
- Unescaped special characters

**Example issue:**
```json
{
  "id": "markdown-001",
  "lines": [55, 58],
  "category": "markdown",
  "subcategory": "list_formatting",
  "confidence": "high",
  "current_text": "Multi-line list items without blank line separation",
  "suggested_fix": "Add blank line between list items",
  "reasoning": "Required for proper markdown rendering"
}
```

## Performance Optimization

**Parallel tool execution** (per research: 40-60% speedup):

**Document discovery phase:**
- Batch Grep calls (5-7 patterns per message) for finding related docs
- Batch Read calls (up to 5 files per message) for cross-reference analysis
- Batch WebFetch calls (3-5 URLs per message) for link validation

**Just-in-time loading:**
- Don't read source code files until accuracy verification phase
- Only read related documents when checking cross-references
- Load based on verification_depth setting

**Rationale:**
- Minimize context usage through strategic loading
- Reduce API call overhead through batching
- Per docs/claude-code-agent-considerations.md:201-220: "40-60% speedup through intelligent tool batching"

## Error Handling

**WebFetch failures:**
- Timeout/404 → Record in issues with `confidence: "low"`, continue review
- Retry transient failures once
- Don't block review on link validation failures

**Missing code references:**
- File path doesn't exist → Record issue, continue
- Function/class not found → Record issue, suggest verification
- Never block review on missing references

**Invalid document path:**
- Return error immediately: "Document not found: {path}"
- Don't attempt review

## Edge Cases

**Empty or minimal documents:**
- Still analyze for basic issues (frontmatter, markdown formatting)
- Skip cross-reference analysis if no substantial content
- Note in summary: minimal content

**Non-markdown files:**
- Check file extension before review
- Return error: "Document reviewer only supports markdown files. {filename} is {detected_type}"

**Very large documents (>10,000 lines):**
- Process normally (Read tool handles large files)
- May take longer, but complete analysis

**Documents with no issues:**
- Return report with empty issues array
- All category scores = 10.0
- Summary: "No issues found"

## Implementation Artifacts

**Files to create:**
- `ai-assisted-development/agents/document-reviewer.md` - Agent implementation

**No slash command needed**: Agent invoked directly via Task tool for Phase 1

**Example invocation:**
```
Task(
  subagent_type="document-reviewer",
  prompt="Review docs/architecture.md with standard verification depth"
)
```

## Success Criteria

**Agent complete when:**
- ✅ Analyzes document across all 7 dimensions
- ✅ Produces valid JSON report with all required fields
- ✅ Handles errors gracefully (links, missing refs, etc.)
- ✅ Assigns confidence levels consistently using principles
- ✅ Works portably across different repos (uses `/tmp/`)
- ✅ Provides clear, minimal output message
- ✅ Implements parallel tool execution for performance
- ✅ Supports quick/standard/thorough verification depths

## Future Phases

**Phase 2 - Document Refiner** (separate design):
- Consumes JSON reports from Phase 1
- Applies high-confidence fixes using Edit tool
- Prompts user for medium-confidence fixes
- Skips low-confidence fixes (manual review)

**Phase 3 - Orchestration** (separate design):
- `/improve-document` slash command
- Runs review → refine loop
- Iterates until quality threshold met or max iterations reached
- Provides progress updates and final summary

## References

### Design Principles
- docs/claude-code-agent-considerations.md - Agent architecture, context engineering, performance optimization
- docs/research/web/2025-12-09-llm-documentation-prompting.md - Technical writing best practices
- docs/research/web/2025-12-06-ai-agent-communication-formats.md - Structured output for agent-to-agent communication

### Key Patterns Applied
- **Single Responsibility**: One goal - analyze document quality, produce report
- **Separation of Concerns**: Analysis (Phase 1) separate from fixing (Phase 2)
- **Structured Artifacts**: JSON for inter-agent communication (per research)
- **Parallel Tool Execution**: Batch independent operations (40-60% speedup)
- **Just-in-Time Loading**: Load data only when needed
- **Graceful Degradation**: Errors don't block completion

### Research-Backed Decisions
- **JSON for agent-to-agent communication** (docs/research/web/2025-12-06-ai-agent-communication-formats.md:64, 376)
- **Three-tier confidence** vs numeric (avoids false precision, enables clear automation boundaries)
- **Principle-based confidence assignment** vs exhaustive mappings (adapts to new issue types)
- **Portable temp storage** (`/tmp/`) for plugin usage across repos

## Document Metadata
- **Created**: 2025-12-09
- **Phase**: 1 of 3 (Read-Only Analysis)
- **Dependencies**: None (standalone agent)
- **Future Dependencies**: Phase 2 (refiner) will consume this agent's JSON reports
