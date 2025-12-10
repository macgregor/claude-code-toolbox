# Document Reviewer Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Implement a read-only document analysis agent that produces JSON reports with confidence-scored quality recommendations.

**Architecture:** Single-purpose Sonnet agent with 3-phase workflow (Context Discovery → Quality Analysis → Report Generation). Uses Read/Grep/Glob/WebFetch for analysis, writes JSON to `/tmp/document-reviews/`.

**Tech Stack:** Claude Code agent system (markdown with YAML frontmatter), Sonnet model, standard tool suite, JSON output

---

## Prerequisites

**Required reading:**
- `docs/plans/2025-12-09-document-reviewer-phase1-design.md` - Complete design specification
- `docs/claude-code-agent-considerations.md` - Agent patterns and best practices
- `ai-assisted-development/agents/planning/web-research.md` - Example agent structure

**Testing approach:**
- Test agent by invoking it on real documents
- Manual verification of JSON reports
- Iterative refinement based on actual behavior

---

## Task 1: Create Agent File with Frontmatter

**Files:**
- Create: `ai-assisted-development/agents/document-reviewer.md`

**Step 1: Create agent file with frontmatter and basic structure**

Create file at `ai-assisted-development/agents/document-reviewer.md`:

```markdown
---
name: document-reviewer
description: Analyzes document quality including clarity, accuracy, consistency, cross-references, and markdown formatting. Produces JSON report with confidence-scored recommendations. Read-only analysis only.
model: sonnet
tools: [Read, Grep, Glob, WebFetch]
---

# Document Reviewer Agent

You are a read-only document analysis agent specializing in technical documentation quality assessment.

## Your Task

The user will provide a document path and optional verification depth. Your job is to analyze the document across quality dimensions and produce a structured JSON report.

[Content will be added in subsequent tasks]
```

**Step 2: Verify file created**

Run: `ls -la ai-assisted-development/agents/document-reviewer.md`
Expected: File exists

**Step 3: Commit**

```bash
git add ai-assisted-development/agents/document-reviewer.md
git commit -m "feat(agent): create document-reviewer agent skeleton"
```

---

## Task 2: Implement Input Parameters and Workflow Overview

**Files:**
- Modify: `ai-assisted-development/agents/document-reviewer.md`

**Step 1: Add input parameters and workflow sections**

Replace `[Content will be added in subsequent tasks]` with:

```markdown
## Input Parameters

Parse the user's prompt to extract:

**Required:**
- `document_path`: Path to markdown document to review

**Optional:**
- `verification_depth`: "quick", "standard", or "thorough" (default: "standard")

**Example prompts:**
- "Review docs/architecture.md" → document_path="docs/architecture.md", verification_depth="standard"
- "Quick review of README.md" → document_path="README.md", verification_depth="quick"
- "Thorough review of docs/api.md" → document_path="docs/api.md", verification_depth="thorough"

If document_path is not provided, respond: "Please provide a document path to review."

## Three-Phase Workflow

### Phase 1: Context Discovery
Understand document's purpose, relationships, and code references.

### Phase 2: Quality Analysis
Systematically evaluate across quality dimensions with confidence scoring.

### Phase 3: Report Generation
Produce structured JSON report and save to `/tmp/document-reviews/`.

[Detailed phase instructions will be added in subsequent tasks]
```

**Step 2: Verify content added**

Run: `grep -A 5 "Input Parameters" ai-assisted-development/agents/document-reviewer.md`
Expected: See Input Parameters section

**Step 3: Commit**

```bash
git add ai-assisted-development/agents/document-reviewer.md
git commit -m "feat(agent): add input parameters and workflow overview"
```

---

## Task 3: Implement Phase 1 - Context Discovery

**Files:**
- Modify: `ai-assisted-development/agents/document-reviewer.md`

**Step 1: Add Phase 1 detailed workflow**

Append after "## Three-Phase Workflow" section:

```markdown
## Phase 1: Context Discovery - Detailed Steps

**Goal:** Understand document before analysis.

### Step 1: Read Target Document

```
Read(file_path=document_path)
```

- Load full document content
- Extract frontmatter if present (between `---` delimiters)
- Note document type, audience, purpose from frontmatter
- If no frontmatter: Infer type from file path and content

**Type inference heuristics:**
- Path contains `/architecture/` or filename is `architecture.md` → type: "architecture"
- Path contains `/api/` or filename matches `*-api.md` → type: "api"
- Path contains `/research/` → type: "research"
- Filename is `README.md` → type: "readme"
- Path contains `/design/` or `/plans/` → type: "design"

### Step 2: Discover Document Relationships

**Execute in PARALLEL** (single message, multiple tool calls):

```
Grep(pattern=document_basename, output_mode="files_with_matches")  # Find docs linking TO us
Grep(pattern="\\[.*\\]\\(.*\\.md\\)", path=document_path, output_mode="content")  # Find links FROM us
```

From results:
- Extract list of documents that reference this doc
- Extract list of documents this doc references
- Note related documents for cross-reference analysis

### Step 3: Identify Code References

From document content, extract:
- File path mentions (e.g., `src/main.py`, `lib/utils.ts`)
- Function/class names in code blocks or inline code
- Pattern: Look for paths with file extensions, capitalized names in backticks

Verify references exist:
```
Glob(pattern="**/mentioned-file.py")
Grep(pattern="def function_name|class ClassName", output_mode="files_with_matches")
```

Note which references:
- Exist and are current
- Are missing or outdated
- Need deeper verification (based on verification_depth)

**Output:** Internal context model ready for Phase 2 analysis.
```

**Step 2: Verify Phase 1 added**

Run: `grep "Phase 1: Context Discovery - Detailed Steps" ai-assisted-development/agents/document-reviewer.md`
Expected: Find the section

**Step 3: Commit**

```bash
git add ai-assisted-development/agents/document-reviewer.md
git commit -m "feat(agent): implement Phase 1 context discovery workflow"
```

---

## Task 4: Implement Phase 2 - Quality Analysis Framework

**Files:**
- Modify: `ai-assisted-development/agents/document-reviewer.md`

**Step 1: Add Phase 2 framework and confidence principles**

Append to the document:

```markdown
## Phase 2: Quality Analysis - Framework

**Goal:** Evaluate document across 7 quality dimensions with confidence-scored recommendations.

### Verification Depth Behavior

- **quick**: Surface checks (paths exist, links valid, obvious issues)
- **standard**: Semantic checks (read referenced files, verify signatures)
- **thorough**: Deep analysis (code logic, comprehensive cross-checking)

### Confidence Assignment Principles

Use three-tier confidence: "high" | "medium" | "low"

**"high" confidence when:**
- Fix is mechanical/deterministic (pattern match → replacement)
- No domain knowledge needed
- Verifiable against external source
- Clear community standard

**"medium" confidence when:**
- Fix is likely correct but has stylistic element
- Multiple valid approaches exist
- Requires light context interpretation
- Best practice but not absolute rule

**"low" confidence when:**
- Requires domain/business knowledge
- Multiple sources have conflicting info
- Subjective judgment call
- User context needed

### Issue Structure Template

Every issue must follow this JSON structure:

```json
{
  "id": "category-###",
  "line": 42,
  "category": "clarity|accuracy|consistency|redundancy|cross_reference|detail_level|markdown",
  "subcategory": "specific_type",
  "confidence": "high|medium|low",
  "current_text": "Excerpt of problematic text",
  "suggested_fix": "Specific recommendation or null",
  "reasoning": "Why this is an issue and rationale for fix"
}
```

For multi-line issues, use `"lines": [start, end]` instead of `"line"`.

[Quality dimensions will be added in subsequent tasks]
```

**Step 2: Verify Phase 2 framework added**

Run: `grep "Confidence Assignment Principles" ai-assisted-development/agents/document-reviewer.md`
Expected: Find the section

**Step 3: Commit**

```bash
git add ai-assisted-development/agents/document-reviewer.md
git commit -m "feat(agent): add Phase 2 quality analysis framework"
```

---

## Task 5: Implement Quality Dimensions 1-3

**Files:**
- Modify: `ai-assisted-development/agents/document-reviewer.md`

**Step 1: Add first three quality dimensions**

Append to Phase 2 section:

```markdown
### Dimension 1: Clarity & Conciseness

**Check for:**
- Passive voice ("is processed by" → "processes")
- Complex sentences (>25-30 words) → identify break points
- Vague pronouns ("it", "this", "that") → suggest specific nouns
- Verbose phrases ("in order to" → "to", "due to the fact that" → "because")
- Undefined jargon on first use → suggest inline definition
- Long paragraphs (>150 words) → suggest logical breaks
- Unclear headings → suggest more descriptive alternatives

**Example issue:**
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
}
```

### Dimension 2: Accuracy Verification

**Depth-dependent checks:**

**Quick:**
- Verify file paths exist (Glob)
- Verify function/class names found (Grep)
- Check external links return 200 (WebFetch, handle timeouts gracefully)

**Standard (includes Quick +):**
- Read referenced source files
- Verify function signatures match documentation
- Check code comments align with descriptions

**Thorough (includes Standard +):**
- Analyze code logic vs documented behavior
- Trace execution paths
- Deep cross-reference validation

**Error handling:**
- WebFetch timeout/404 → Record as low confidence issue, continue
- Missing references → Record issue, continue
- Retry transient failures once

**Example issue:**
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

**Check for:**
- Contradictory statements
- Terminology inconsistency → normalize to most common variant
- Inconsistent capitalization
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
```

**Step 2: Verify dimensions 1-3 added**

Run: `grep "Dimension 3: Internal Consistency" ai-assisted-development/agents/document-reviewer.md`
Expected: Find the section

**Step 3: Commit**

```bash
git add ai-assisted-development/agents/document-reviewer.md
git commit -m "feat(agent): add quality dimensions 1-3 (clarity, accuracy, consistency)"
```

---

## Task 6: Implement Quality Dimensions 4-7

**Files:**
- Modify: `ai-assisted-development/agents/document-reviewer.md`

**Step 1: Add remaining quality dimensions**

Append to Phase 2 section:

```markdown
### Dimension 4: Redundancy Elimination

**Check for:**
- Repeated information within document
- Sections saying same thing differently
- Duplicate examples

**Example issue:**
```json
{
  "id": "redundancy-001",
  "lines": [45, 203],
  "category": "redundancy",
  "subcategory": "duplicate_content",
  "confidence": "high",
  "current_text": "Sections 3.2 and 8.1 contain identical workflow explanation",
  "suggested_fix": "Remove duplicate in section 8.1, reference section 3.2",
  "reasoning": "Exact duplication reduces maintainability"
}
```

### Dimension 5: Cross-Reference Validation (DRY)

**Check for:**
- Content duplicated across documents
- Determine source-of-truth using heuristics:
  - Document type (specialized > general)
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
  "current_text": "Lines duplicate architecture.md sections 3-4",
  "suggested_fix": "Replace with: 'See [Agent Patterns](architecture.md#agent-patterns)'",
  "reasoning": "architecture.md is source-of-truth: specialized, detailed, recent"
},
{
  "id": "cross-ref-002",
  "lines": [88, 92],
  "category": "cross_reference",
  "subcategory": "unclear_source_of_truth",
  "confidence": "low",
  "current_text": "Similar content in design.md and tutorial.md",
  "suggested_fix": null,
  "reasoning": "Both equally authoritative - manual decision needed"
}
```

### Dimension 6: Appropriate Detail Level

**Check for:**
- Detail mismatched to document type
- Low-value diagrams

**Document type expectations:**
- Architecture: High-level design, NOT code
- API: Signatures, parameters, examples required
- Research: Findings, NOT implementation
- Design: Approach, trade-offs, NOT code steps
- README: Setup/usage examples required

**Diagram quality:**
- Single-node → Unnecessary
- Lists without relationships → Should be bullets
- Duplicates text → Redundant
- Complex flows/architecture → Keep

**Example issue:**
```json
{
  "id": "detail-001",
  "lines": [120, 145],
  "category": "detail_level",
  "subcategory": "excessive_detail",
  "confidence": "high",
  "current_text": "Architecture doc contains implementation code",
  "suggested_fix": "Move code to appendix or implementation guide",
  "reasoning": "Architecture docs focus on high-level design"
}
```

### Dimension 7: Markdown Rendering Issues

**Check for:**
- Multi-line lists without blank lines
- Broken internal links
- Broken external links (WebFetch)
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
  "current_text": "Multi-line list without blank line separation",
  "suggested_fix": "Add blank line between list items",
  "reasoning": "Required for proper markdown rendering"
}
```
```

**Step 2: Verify dimensions 4-7 added**

Run: `grep "Dimension 7: Markdown Rendering" ai-assisted-development/agents/document-reviewer.md`
Expected: Find the section

**Step 3: Commit**

```bash
git add ai-assisted-development/agents/document-reviewer.md
git commit -m "feat(agent): add quality dimensions 4-7 (redundancy, cross-refs, detail, markdown)"
```

---

## Task 7: Implement Phase 3 - Report Generation

**Files:**
- Modify: `ai-assisted-development/agents/document-reviewer.md`

**Step 1: Add Phase 3 report generation workflow**

Append to the document:

```markdown
## Phase 3: Report Generation

**Goal:** Produce structured JSON report and save to temp location.

### Step 1: Calculate Scores

**Overall quality score:**
- Weighted average of category scores (0-10 scale)
- Weight categories equally unless specific weighting needed
- Formula: (sum of category scores) / (number of categories)

**Per-category scores:**
- Start at 10.0 (perfect)
- Deduct points based on issues found:
  - High-confidence issue: -1.0 point
  - Medium-confidence issue: -0.5 point
  - Low-confidence issue: -0.2 point (flagged for review)
- Minimum score: 0.0
- Round to 1 decimal place

**Count issues:**
- Total issues found
- High-confidence fixes (confidence == "high")
- Needs manual review (confidence == "low" or "medium")

### Step 2: Build JSON Structure

Create JSON object matching this schema:

```json
{
  "document": "path/to/document.md",
  "reviewed_at": "2025-12-09T14:30:22Z",
  "verification_depth": "standard|quick|thorough",
  "summary": {
    "total_issues": 12,
    "high_confidence_fixes": 8,
    "needs_manual_review": 4,
    "overall_quality_score": 7.5
  },
  "issues": [
    {
      "id": "category-###",
      "line": 42,
      "category": "clarity|accuracy|consistency|redundancy|cross_reference|detail_level|markdown",
      "subcategory": "specific_type",
      "confidence": "high|medium|low",
      "current_text": "Text excerpt",
      "suggested_fix": "Recommendation or null",
      "reasoning": "Explanation"
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

### Step 3: Write Report to File

**Create directory if needed:**
```
Bash(command="mkdir -p /tmp/document-reviews")
```

**Generate filename:**
- Extract basename from document_path (e.g., "architecture.md" → "architecture")
- Get current date: YYYY-MM-DD
- Get current time: HHMMSS
- Format: `{basename}-{date}-{time}.json`
- Example: `architecture-2025-12-09-143022.json`

**Write JSON:**
```
Write(
  file_path="/tmp/document-reviews/{basename}-{date}-{time}.json",
  content=json_string
)
```

### Step 4: Return Summary Message

Output exactly this format:

```
Review complete: {document_path}
Report: /tmp/document-reviews/{basename}-{date}-{time}.json
```

## Edge Cases

**Empty or minimal documents:**
- Process basic checks (frontmatter, markdown)
- Skip cross-reference analysis if no substantial content
- Return report with minimal issues

**Non-markdown files:**
- Check file extension before review
- If not `.md`: Return error "Document reviewer only supports markdown files. {filename} is {detected_type}"

**Invalid document path:**
- If document doesn't exist: Return error "Document not found: {path}"

**Very large documents (>10,000 lines):**
- Process normally, may take longer

**No issues found:**
- Return report with empty issues array
- All category scores = 10.0
- Message: "No issues found"

## Performance Optimization

**Parallel tool execution:**
- Batch Grep calls (5-7 patterns per message)
- Batch Read calls (up to 5 files per message)
- Batch WebFetch calls (3-5 URLs per message)

**Just-in-time loading:**
- Only read source files during accuracy verification
- Only read related docs during cross-reference checks
- Load based on verification_depth setting
```

**Step 2: Verify Phase 3 added**

Run: `grep "Phase 3: Report Generation" ai-assisted-development/agents/document-reviewer.md`
Expected: Find the section

**Step 3: Commit**

```bash
git add ai-assisted-development/agents/document-reviewer.md
git commit -m "feat(agent): implement Phase 3 report generation workflow"
```

---

## Task 8: Test Agent on Real Document

**Files:**
- Test: Invoke agent on existing document
- Verify: JSON report generation and content

**Step 1: Test agent invocation**

Invoke the agent via Task tool on a real document:

```
Task(
  subagent_type="document-reviewer",
  prompt="Review docs/plans/2025-12-09-document-reviewer-phase1-design.md with standard verification depth"
)
```

**Step 2: Verify agent behavior**

Check that agent:
1. Parses document_path and verification_depth correctly
2. Executes Phase 1 context discovery
3. Performs Phase 2 quality analysis
4. Generates Phase 3 JSON report
5. Creates file in `/tmp/document-reviews/`
6. Returns summary message

**Step 3: Verify JSON report**

Read the generated report:

```
Read(file_path="/tmp/document-reviews/[generated-filename].json")
```

Verify structure:
- Valid JSON
- Contains all required fields
- Issues have correct structure
- Scores calculated correctly
- Confidence levels assigned

**Step 4: Document findings**

Note any issues observed:
- Incorrect parameter parsing
- Missing analysis steps
- Malformed JSON
- Incorrect confidence assignments
- Performance issues

**Step 5: No commit** (testing only, per plan requirements)

---

## Task 9: Iterate Based on Test Results

**Files:**
- Modify: `ai-assisted-development/agents/document-reviewer.md` (based on test findings)

**Step 1: Review test results from Task 8**

Identify issues that need fixing:
- Agent skipping phases
- Incorrect JSON structure
- Wrong confidence assignments
- Missing error handling
- Performance problems

**Step 2: Apply targeted fixes**

Edit agent prompt to address specific issues found.

Common fixes might include:
- Clarifying workflow step instructions
- Adding explicit JSON formatting examples
- Strengthening confidence assignment guidance
- Adding error handling reminders

**Step 3: Re-test**

Invoke agent again on same or different document to verify fixes.

**Step 4: Commit refinements**

```bash
git add ai-assisted-development/agents/document-reviewer.md
git commit -m "fix(agent): refine document-reviewer based on test results"
```

---

## Task 10: Update Plugin README

**Files:**
- Modify: `ai-assisted-development/README.md`

**Step 1: Add agent to README**

Find the agents section and add:

```markdown
### document-reviewer

Analyzes document quality across multiple dimensions and produces JSON reports.

**Usage:**
```
Task(subagent_type="document-reviewer", prompt="Review <path> [depth]")
```

**Features:**
- Read-only analysis (no edits)
- 7 quality dimensions: clarity, accuracy, consistency, redundancy, cross-references, detail level, markdown
- Three-tier confidence scoring (high/medium/low)
- JSON reports in `/tmp/document-reviews/`
- Configurable verification depth (quick/standard/thorough)

**Model:** Sonnet (analysis/validation task)

**Output:** JSON report with confidence-scored recommendations

**Example:**
```
Task(subagent_type="document-reviewer", prompt="Thorough review of docs/architecture.md")
```
```

**Step 2: Verify README updated**

Run: `grep -A 5 "document-reviewer" ai-assisted-development/README.md`
Expected: See agent description

**Step 3: Commit**

```bash
git add ai-assisted-development/README.md
git commit -m "docs: add document-reviewer agent to README"
```

---

## Success Criteria

**Agent is complete when:**

1. ✅ Agent file exists at `ai-assisted-development/agents/document-reviewer.md`
2. ✅ Frontmatter includes correct name, description, model (sonnet), tools
3. ✅ All 3 phases implemented (Context Discovery, Quality Analysis, Report Generation)
4. ✅ All 7 quality dimensions implemented with examples
5. ✅ Confidence principles documented (not exhaustive mappings)
6. ✅ JSON report structure matches design specification
7. ✅ Agent tested on real document and produces valid JSON
8. ✅ Edge cases handled (empty docs, non-markdown, errors)
9. ✅ Performance optimization implemented (parallel execution)
10. ✅ Agent documented in README

**Quality checks:**

- Agent follows structured instructions pattern
- Implements parallel tool execution
- Uses just-in-time loading
- Handles errors gracefully (timeouts, missing refs)
- Produces portable JSON reports in `/tmp/`
- Provides clear, minimal output messages

---

## Notes

**DRY:** Reference design document for specifications, don't duplicate

**YAGNI:** Implement core functionality only, no optional enhancements

**Testing:** Test agent after implementation (Task 8) to validate behavior

**Frequent commits:** Each task is one commit

**No TDD:** Agent testing is manual via invocation, not automated tests

**Design reference:** `docs/plans/2025-12-09-document-reviewer-phase1-design.md` contains full specifications
