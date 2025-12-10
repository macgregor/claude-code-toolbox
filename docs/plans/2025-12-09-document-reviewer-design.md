# Document Reviewer Agent Design

**Date**: 2025-12-09
**Status**: Design Complete
**Author**: AI-Assisted Design Session

## Overview

A specialized Claude Code agent that reviews a single document to ensure high quality, accuracy, consistency, and adherence to documentation best practices. The agent performs automated fixes where possible (respecting user's permission mode) and requests user input when facing ambiguous decisions.

## Problem Statement

Documentation quality degrades over time as codebases evolve, leading to:
- Inaccurate information about current code features
- Redundant content across multiple documents
- Inconsistent terminology and style
- Poor cross-referencing (violating DRY principle)
- Markdown rendering issues
- Inappropriate detail levels for document types
- Low-value diagrams that don't add insight

Manual review is time-consuming and inconsistent. An automated agent can systematically check quality dimensions and fix common issues.

## Design Decisions

### Core Architecture

**Agent Type**: Single-purpose review agent
**Model**: Sonnet - Review/validation task requiring complex reasoning and judgment
**Tools**: Read, Grep, Glob, Edit, AskUserQuestion, WebFetch

**Rationale**:
- Sonnet selected per docs/claude-code-agent-considerations.md:148-152 - "Planning, review, complex reasoning, validation"
- Edit tool automatically respects Claude Code permission modes (no custom permission handling needed)
- WebFetch essential for validating external documentation links
- AskUserQuestion enables user decisions when confidence < 80%

### Input Parameters

```yaml
document_path: <required> # Path to document to review
verification_depth: <optional> # "quick" | "standard" | "thorough" (default: "standard")
```

### Permission Handling

**Design**: Use Edit tool directly, inherit user's Claude Code permission mode

**Behavior**:
- User in "accept all edits" mode → Changes apply automatically
- User in "bypass permissions" mode → All operations execute without prompts
- User in default mode → Prompted for each Edit call
- User can reject individual edits without stopping review

**Rationale**: Claude Code handles permission inheritance for subagents automatically, eliminating need for custom permission logic.

## Four-Phase Workflow

### Phase 1: Context Discovery

**Goal**: Understand document's purpose, scope, audience, and relationships before reviewing content.

**Steps**:

1. **Read target document** - Load full content

2. **Extract or infer metadata**:
   - Check for YAML frontmatter (title, type, audience, purpose, source-of-truth-for)
   - If missing: Infer from file path, content structure, headings, tone
   - Prepare frontmatter addition via Edit (user can reject)
   - Frontmatter renders as table in GitHub/GitLab - acceptable trade-off for structured metadata

3. **Discover document relationships** (parallel execution):
   - Grep: Documents that link TO this document (who references us?)
   - Read document: Extract links FROM this document (who do we reference?)
   - Glob/Grep: Identify related documents via similar topics/keywords

4. **Identify code references** (if applicable):
   - Extract mentioned file paths, function names, class names
   - Grep/Glob: Verify references exist in codebase
   - Note references for accuracy verification phase

**Output**: Internal context model of document's role in ecosystem

### Phase 2: Quality Review (7 Dimensions)

**Verification Depth Levels**:

- **quick**: Surface checks (paths exist, links valid, obvious markdown issues)
- **standard** (default): Shallow semantic checks (read referenced files, verify signatures, check comments align)
- **thorough**: Deep semantic analysis (analyze code logic, trace execution, comprehensive cross-referencing)

#### Dimension 1: Clarity & Conciseness

**Checks** (research-backed from Google Cloud, Document360, Docsie):
- Verbose phrasing, redundant words, unnecessary qualifiers
- Complex sentences (>25-30 words)
- Vague language in technical content ("should", "might", "probably")
- Passive voice constructions ("is done by" → "does")
- Vague pronouns without clear antecedent ("it", "this", "that")
- Overly technical jargon without definition on first use
- Long paragraphs (>150 words) without logical breaks
- Unclear headings

**Actions**:
- **Auto-fix**: Convert passive to active voice, break complex sentences, add paragraph breaks, simplify phrasing, add inline definitions for jargon
- **Flag in summary**: Issues requiring human judgment

#### Dimension 2: Accuracy Verification

**Depth-dependent checks**:

- **Quick**:
  - Verify file paths exist (Glob)
  - Function/class names found (Grep)
  - External links valid (WebFetch with timeout handling)

- **Standard**:
  - Read referenced source files
  - Verify function signatures match documentation
  - Check code comments align with descriptions
  - Validate external documentation links are current

- **Thorough**:
  - Analyze code logic to verify documented behavior
  - Trace execution paths for workflow documentation
  - Deep cross-reference validation

**Actions**:
- **Auto-fix**: Update outdated function signatures, fix broken internal file links
- **Flag in summary**: Verification failures, suspected inaccuracies, dead external links

**Error handling**:
- WebFetch failures (404, timeout) → Flag in summary, don't block review
- Missing code references → Note in summary, suggest verification
- Retry once on transient failures

#### Dimension 3: Internal Consistency

**Checks**:
- Contradictory statements within document
- Terminology inconsistency (e.g., "subagent" vs "sub-agent" vs "sub agent")
- Inconsistent capitalization (e.g., "GitHub" vs "github")
- Mixed British/American spelling
- Examples that contradict stated principles
- Inconsistent formatting patterns

**Actions**:
- **Auto-fix**: Normalize terminology to most common variant, fix capitalization, standardize spelling
- **Ask user**: Conflicting information requiring domain knowledge (confidence < 80%)

#### Dimension 4: Redundancy Elimination

**Checks**:
- Repeated information within same document
- Sections that convey same information differently
- Duplicate examples

**Actions**:
- **Auto-fix**: Remove or consolidate duplicate content

#### Dimension 5: Cross-Reference Validation (DRY Principle)

**Goal**: Ensure documents reference others rather than duplicating content.

**Heuristic Analysis for Source of Truth**:

Analyze both documents using weighted criteria:
1. Document type/purpose (official docs > design docs > research notes)
2. Depth of coverage (detailed treatment > brief mention)
3. Recency and maintenance (recently updated > stale)
4. Explicit frontmatter claims (`source-of-truth-for: [topic]`)
5. Document scope (specialized doc > general doc for specific topic)

**Confidence scoring**:
- **High confidence** (>80%): Auto-fix by replacing duplicated content with links
- **Low confidence** (<80%): Use AskUserQuestion with 2-4 options, clear trade-off descriptions

**Bidirectional linking**:
- If we link to them as source of truth, verify they link back to us for related content

**Actions**:
- **Auto-fix**: Replace duplicate content with cross-references (when confident)
- **Ask user**: Source of truth determination when ambiguous

#### Dimension 6: Appropriate Detail Level

**Context-aware validation**:

Document type determines appropriate detail:
- **Architecture docs**: High-level design, component interactions, NOT implementation details
- **API docs**: Specific signatures, parameters, return values, usage examples
- **Research docs**: Findings, sources, analysis - NOT implementation steps
- **Design docs**: Approach, trade-offs, decisions - NOT step-by-step code
- **README/Getting Started**: Concrete setup/usage examples

**Diagram Quality Check** (architecture/design documents):
- Verify diagrams add value, not just decoration
- Criteria:
  - Illustrates relationships/flows hard to describe in text?
  - Reduces complexity rather than duplicating clear text?
  - Sufficiently complex to warrant visualization?

**Detection heuristics**:
- Single-node diagrams → Likely unnecessary
- Diagrams that just list items without relationships → Could be bullet list
- Diagrams identical to text description → Redundant
- Complex multi-step flows, branching logic, architectural layers → Keep

**Actions**:
- **Auto-fix**: Move overly detailed content to appendix, remove low-value diagrams
- **Ask user**: Uncertain if detail level appropriate for audience, medium-complexity diagram decisions

#### Dimension 7: Markdown Rendering Issues

**Checks**:
- Multi-line content rendering as single line (needs list formatting or extra newlines)
- Broken internal links (file paths)
- Broken external links (URLs via WebFetch)
- Code blocks missing language identifiers
- Malformed tables, lists, headers
- Improper escaping of special characters

**Actions**:
- **Auto-fix**: All markdown formatting issues

### Phase 3: Apply Fixes

**Execution Strategy**:

1. **Batch edits intelligently**:
   - Group related changes (e.g., all terminology fixes, all markdown issues)
   - Multiple Edit calls for logically separate changes (enables granular approval/rejection)
   - Order: Structural fixes (frontmatter, headings) → Content fixes (redundancy, clarity) → Formatting (markdown)

2. **Handle user questions**:
   - Use AskUserQuestion when confidence < 80% on source-of-truth, conflicts, diagram value
   - Present 2-4 options with clear trade-off descriptions
   - Single choice (multiSelect: false) for mutually exclusive decisions
   - Example headers: "Source of truth", "Conflict resolution", "Diagram value"

3. **Performance optimization** (docs/claude-code-agent-considerations.md:201-220):
   - Parallel Grep calls for document discovery (batch independent searches)
   - Batch Read calls for related documents (up to 5 files per message)
   - Batch WebFetch calls for external URLs (3-5 per message)
   - Just-in-time loading: Only read source files during accuracy verification phase

### Phase 4: Summary Report

**Final message format**:

```markdown
## Document Review Complete: [document-name]

**Document Context**: [1-2 sentences about type, audience, purpose]

**Changes Made**:
- Added/Updated frontmatter with metadata
- Fixed 12 clarity issues (passive voice, complex sentences, vague pronouns, long paragraphs)
- Verified 15 code references (12 accurate, 3 updated)
- Resolved 2 internal inconsistencies (terminology normalized to "subagent")
- Removed 3 instances of redundant content
- Added 4 cross-references to related documents (linked to architecture.md, design.md as source of truth)
- Removed 2 low-value diagrams, kept 1 complex architectural diagram
- Fixed 7 markdown rendering issues (list formatting, code block languages, broken links)

**Verification Depth**: standard

**Issues Requiring Attention**: [if any]
- External link timeout: https://example.com/outdated-docs (verify manually)
- Suspected inaccuracy in section 3.2: described behavior doesn't match code analysis
```

## Edge Cases

**Empty or minimal documents**:
- Still add frontmatter, check markdown, validate links
- Skip cross-reference analysis if no substantial content

**Non-markdown files**:
- Agent specialized for markdown; gracefully decline other formats
- Message: "Document Reviewer is specialized for markdown files. [filename] appears to be [detected type]."

**Document changes during review**:
- Detect via Read before final edits
- Rare in single-agent scenario, but handle gracefully

**Conflicting edits**:
- Multiple Edit calls allow user to accept some, reject others
- Agent continues with remaining fixes

## Implementation Artifacts

### Agent File Structure

```
ai-assisted-development/
└── agents/
    └── document-reviewer.md    # Main agent with frontmatter and prompt
```

### Agent Frontmatter

```yaml
---
name: document-reviewer
description: Reviews a single document for quality, accuracy, consistency, and documentation best practices. Verifies code references, eliminates redundancy, ensures proper cross-referencing, and fixes markdown rendering issues.
model: sonnet
tools: [Read, Grep, Glob, Edit, AskUserQuestion, WebFetch]
---
```

### Prompt Structure

Following Structured Instructions pattern (docs/claude-code-agent-considerations.md:298-319):

```markdown
# Agent Role
[Clear, specific role definition]

## Core Responsibilities
[5 specific responsibilities]

## Input Parameters
[document_path (required), verification_depth (optional)]

## Workflow
[Detailed step-by-step for 4 phases: Context Discovery, Quality Review, Apply Fixes, Summary Report]

## Quality Criteria
[7 dimensions with specific checks and actions]

## Output Format
[Summary report template]

## Examples

### Example 1: Adding Missing Frontmatter
[Concrete scenario showing frontmatter inference and addition]

### Example 2: Resolving Cross-Reference Conflict
[Scenario showing heuristic analysis and source-of-truth decision]

### Example 3: Fixing Low-Value Diagrams
[Scenario showing diagram quality check and removal]
```

## Success Metrics

**Quality improvements**:
- Reduction in broken links (internal and external)
- Improved readability scores (sentence length, passive voice)
- Elimination of redundant content
- Proper cross-referencing across documentation

**User experience**:
- Time saved vs manual review
- User acceptance rate of proposed edits
- Reduction in follow-up review cycles

**Accuracy**:
- Code reference verification success rate
- Source-of-truth determination accuracy (user agreement rate)
- False positive rate (incorrect "fixes")

## Future Enhancements

**Not in scope for initial implementation** (YAGNI principle):

1. **Multi-document consistency** - Check consistency across multiple related documents (requires orchestration)
2. **Style guide enforcement** - Custom organizational style rules (wait for concrete requirements)
3. **Automated testing** - Generate tests for documented APIs (separate agent responsibility)
4. **Translation validation** - Check multi-language documentation consistency (no current need)

## References

### Design Principles
- docs/claude-code-agent-considerations.md - Agent architecture, context engineering, performance optimization
- docs/research/web/2025-12-09-llm-documentation-prompting.md - Technical writing best practices

### Key Patterns Applied
- **Single Responsibility**: One goal - review single document quality
- **Hybrid Model Orchestration**: Sonnet for review/validation tasks
- **Progressive Disclosure**: Frontmatter (metadata) → Instructions (workflow) → Resources (examples)
- **Parallel Tool Execution**: Batch independent Grep/Read/WebFetch calls (40-60% speedup)
- **Just-in-Time Loading**: Load source files only during accuracy verification phase
- **Quality Gate Pattern**: User questions and permission modes enable validation thresholds

### Research-Backed Best Practices
- Google Cloud AI: Clear instructions, iterative refinement, minimize token count
- Document360: Structured prompting, step-by-step generation, consistency maintenance
- Docsie: User-focused language, mastering brevity, continuous research
- ScoutOS: Chain-of-thought approach, context awareness, iterative refinement

## Appendix: Frontmatter Schema

```yaml
---
title: <string>                    # Document title
type: <string>                     # architecture | api | research | design | tutorial | readme
audience: <string>                 # developers | architects | users | contributors
purpose: <string>                  # Brief description of document's purpose
source-of-truth-for: [<string>]   # Topics this document owns (optional)
related-docs: [<string>]          # Paths to related documents (optional)
last-reviewed: <date>             # ISO date of last review (auto-updated)
---
```

## Appendix: Research Sources

- [Google Cloud Prompt Best Practices](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/prompt-best-practices)
- [Document360 Prompt Engineering for Technical Writers](https://www.document360.com/blog/prompt-engineering-for-technical-writers)
- [ScoutOS LLM Prompts for Technical Documentation](https://www.scoutos.com/blog/top-5-llm-prompts-for-re-writing-your-technical-documentation)
- [Docsie Prompt Engineering Guide](https://www.docsie.io/blog/articles/10-ways-to-master-prompt-engineering-for-technical-writers/)
