# Document Reviewer - Agent Lifecycle Integration

**Date**: 2025-12-10
**Status**: Completed
**Goal**: Refactor document-reviewer agent to use agent lifecycle framework

---

## Current State Analysis

### What the Agent Does Now

**Phase 3 current behavior (lines 364-493):**
1. Calculates quality scores from issues found
2. Builds JSON report structure
3. **Agent outputs**: Pure JSON as final message (lines 397-432)
4. **Hook handles**: JSON validation, file persistence to `/tmp/document-reviews/`

**Current output contract:**
- Agent's final message is pure JSON
- No context tags, no work tags
- Hook is mentioned in agent prompt (lines 368-372, 486-493)
- SubagentStop hook handles persistence (but NOT implemented yet)

### Current Gaps

**Missing lifecycle integration:**
1. ❌ No `<context>` tag with summary of analysis
2. ❌ No `<work>` tag around JSON output
3. ❌ Agent is tightly coupled to `/tmp/` storage location
4. ❌ Hook-based validation mentioned but not implemented

**Current SubagentStop handler (agent-lifecycle.py:339-400):**
- Extracts `<context>` tags → appends to `context.md`
- Extracts `<work relpath="...">` tags → writes directly to request directory (BUG: should use `work/` subdirectory)
- No filename validation (SECURITY ISSUE: allows path traversal)

---

## Design Decisions

### Integration Strategy

**Option A: Minimal - Add Tags Only**
- Keep JSON generation in agent
- Wrap final output in `<context>` and `<work>` tags
- Store in request `work/` directory instead of `/tmp/`
- Leverage existing universal `agent-lifecycle.py` handler

**Decision: Option A (Minimal - tags only)**

**Rationale:**
- **Add tags**: Minimum viable integration with lifecycle framework
- **Skip preprocessing**: Agent already handles discovery efficiently with parallel tool calls
- **Skip validation for now**: Focus on minimal integration, add validation later if needed
- **Use existing infrastructure**: `agent-lifecycle.py` already handles context/work tag extraction universally

---

## Implementation Steps

### Step 1: Write Comprehensive Tests

**File**: `ai-assisted-development/tests/test_agent_lifecycle.py`

Create thorough unit tests for `agent-lifecycle.py` using Python's built-in `unittest` module (no third-party dependencies).

**Test Coverage:**

1. **`test_get_toolbox_root()`**
   - Returns env var when set
   - Falls back to CLAUDE_ENV_FILE parsing
   - Falls back to cwd from hook_input
   - Returns empty string when all fail

2. **`test_generate_request_id()`**
   - Deterministic: same input produces same ID
   - Format: `{timestamp}_{hash}` (8-char hash)
   - Handles missing timestamp (generates current)
   - Colons replaced with dashes in timestamp

3. **`test_create_request_directory()`**
   - Creates `.toolbox/events/{request-id}/`
   - Creates `work/` subdirectory
   - Creates `session-logs/` subdirectory
   - Creates empty `hook-events.jsonl`
   - Creates empty `errors.log`
   - Idempotent (no error on re-run)

4. **`test_parse_context_tags()`**
   - Extracts single context tag
   - Extracts multiple context tags
   - Handles empty text
   - Handles no context tags
   - Strips whitespace from content

5. **`test_parse_work_tags()`** (NEW behavior with `filename` attribute)
   - Extracts single work tag with filename
   - Extracts multiple work tags
   - Returns `{"filename": ..., "content": ...}` dict structure
   - Handles empty text
   - Strips whitespace from content
   - Does NOT match old `relpath` attribute

6. **`test_handle_subagent_stop_work_tags()`**
   - Writes file to `work/` subdirectory
   - Validates filename (no `/`, `\\`, `..`)
   - Exits with code 1 on invalid filename
   - Exits with code 1 on duplicate filename
   - Handles multiple work tags

7. **`test_handle_subagent_stop_context_tags()`**
   - Appends context to `context.md`
   - Wraps in `<agent-{id} type="{type}">` tags
   - Handles multiple context tags

8. **`test_handle_user_prompt_submit()`**
   - Generates request ID
   - Writes to `.current-request-id`
   - Creates request directory
   - Initializes `context.md` with user prompt
   - Extracts start UUID from transcript

9. **`test_handle_stop_event()`**
   - Reads start UUID from `.start-uuid`
   - Prunes session log between start and end UUIDs
   - Writes pruned log to `session-logs/`

10. **`test_append_to_request_events()`**
    - Appends to `hook-events.jsonl` when request active
    - Does nothing when no request active

**Test Fixtures** (in `ai-assisted-development/tests/fixtures/`):
- Sample hook input JSON files
- Sample agent transcripts with context/work tags
- Sample session logs

**Makefile Target**:

Add to `/workspace/Makefile`:
```makefile
.PHONY: test
test:
	python -m unittest discover -s ai-assisted-development/tests -p "test_*.py" -v

.PHONY: test-lifecycle
test-lifecycle:
	python -m unittest ai-assisted-development.tests.test_agent_lifecycle -v
```

**Success Criteria for Step 1:**
- All tests pass
- `make test` runs successfully
- Code coverage for all modified functions

### Step 2: Update agent-lifecycle.py

**File**: `ai-assisted-development/scripts/agent-lifecycle.py`

**Changes to `parse_work_tags()` (line 120):**

```python
def parse_work_tags(text: str) -> List[Dict[str, str]]:
    """Extract {filename, content} from <work> tags"""
    pattern = r'<work\s+filename="([^"]+)"\s*>(.*?)</work>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [{"filename": filename, "content": content.strip()} for filename, content in matches]
```

**Changes to `handle_subagent_stop()` (lines 387-392):**

Replace the work tag writing section with:

```python
# Parse and write work files
work_items = parse_work_tags(final_output)
work_dir = request_dir / "work"

for item in work_items:
    filename = item["filename"]

    # Validate: no path separators or traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        print(f"[SubagentStop] ERROR: Invalid filename '{filename}' - must be simple filename only", file=sys.stderr)
        sys.exit(1)

    work_path = work_dir / filename

    # Validate: no duplicates
    if work_path.exists():
        print(f"[SubagentStop] ERROR: File '{filename}' already exists in work directory", file=sys.stderr)
        sys.exit(1)

    work_path.write_text(item["content"])
```

**Rationale:**
- Changes attribute from `relpath` to `filename` (simpler, clearer intent)
- Writes to `work/` subdirectory (already created at line 74)
- Validates filename is simple (no path traversal)
- Prevents duplicate filenames (avoids silent overwrites)

**Success Criteria for Step 2:**
- All tests still pass
- No regressions in existing functionality

### Step 3: Update document-reviewer agent

**File**: `ai-assisted-development/agents/quality/document-reviewer.md`

**Changes needed:**

1. **Line 57** - Update Phase 1 description:
   - Current: `Produce structured JSON report and save to /tmp/document-reviews/.`
   - New: `Produce structured JSON report in final message.`

2. **Lines 364-494** - Replace entire Phase 3 section:

```markdown
## Phase 3: Report Generation

**Goal:** Produce context summary and structured JSON report as final message.

### Step 1: Calculate Scores

**Overall quality score:**
- Weighted average of category scores (0-10 scale)
- Weight categories equally
- Formula: (sum of category scores) / 7

**Per-category scores:**
- Start at 10.0 (perfect)
- Deduct points based on issues found:
  - High-confidence issue: -1.0 point
  - Medium-confidence issue: -0.5 point
  - Low-confidence issue: -0.2 point
- Minimum score: 0.0
- Round to 1 decimal place

**Count issues:**
- Total issues found
- High-confidence fixes (confidence == "high")
- Needs manual review (confidence == "low" or "medium")

### Step 2: Build and Output Final Message

Your final message must contain TWO parts:

**1. Context summary** - What you analyzed and found:
```
<context>
Reviewed {document_path} ({line_count} lines, {doc_type} document)
Found {total_issues} issues: {high} high-confidence, {medium} medium-confidence, {low} low-confidence
Overall quality score: {score}/10
Top issues: {category1} ({count1}), {category2} ({count2})
</context>
```

**2. JSON report** - Structured findings wrapped in work tag:
```
<work filename="document-review-report.json">
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
</work>
```

**Critical requirements:**
- Context must be concise (3-5 lines max)
- JSON must be valid and complete
- Filename is just the filename (framework handles storage location)
- Framework will write JSON to `.toolbox/events/{request-id}/work/document-review-report.json`

**No issues found:**
- Return report with empty issues array
- All category scores = 10.0
- total_issues = 0
```

**Rationale:**
- Removes all `/tmp/` references (lines 57, 490)
- Removes "pure JSON only" requirement (lines 369-372, 478-485)
- Adds `<context>` tag output
- Wraps JSON in `<work filename="...">` tag
- Agent provides only filename, framework handles full path

### Step 4: Integration Test

**Manual testing:**
1. Run document-reviewer agent on a test document
2. Verify context tag → appends to `.toolbox/events/{request-id}/context.md`
3. Verify work tag → writes to `.toolbox/events/{request-id}/work/document-review-report.json`
4. Verify JSON is valid and complete
5. Test edge cases:
   - Invalid filename with `/` → exits with error
   - Duplicate filename → exits with error

---

## Success Criteria

**Refactor complete when:**
- ✅ Agent outputs `<context>` summary of analysis
- ✅ Agent outputs `<work filename="...">` tag wrapping JSON report
- ✅ Lifecycle handler extracts context and work tags
- ✅ Valid reports write to `.toolbox/events/{request-id}/work/document-review-report.json`
- ✅ Context summary appends to `.toolbox/events/{request-id}/context.md`
- ✅ No references to `/tmp/` storage in agent prompt
- ✅ Agent is decoupled from storage location (framework handles persistence)
- ✅ Filename validation prevents path traversal attacks

---

## Migration Path

**Backward compatibility:** None needed (agent not yet in production use)

**Future phases:**
- Phase 2 (document-refiner) will read from `.toolbox/events/{request-id}/work/document-review-report.json`
- Phase 3 (orchestrator) will coordinate review → refine loop using request directory as shared workspace

---

## References

- ARCHITECTURE.md - Agent lifecycle foundation
- docs/claude-code-reference.md - Hook system behavior
- ai-assisted-development/scripts/agent-lifecycle.py - Standard lifecycle handler
- docs/plans/2025-12-09-document-reviewer-phase1-design.md - Original design
