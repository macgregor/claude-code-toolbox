# Context Indexing Agent Design

**Date:** 2025-12-05
**Status:** Design Phase

## Overview

This preprocessing agent takes a natural language prompt, discovers relevant local documentation files, and produces a structured index with relevance assessments. It automates finding and linking relevant files when crafting requests to other agents.

## Problem Statement

Users currently search manually for relevant documentation files when creating agent requests. For example, asking about multi-agent coordination requires remembering to link files like `docs/research/web/2025-12-05-multi-agent-orchestration-claude-code.md` and `docs/research/web/2025-12-05-claude-code-features-architecture.md`. This process is tedious and error-prone.

## Solution

This agent acts as a filter/preprocessor. Users provide a prompt describing their task. The agent discovers relevant documentation and produces a structured index showing what files exist and why they matter. Users review the index and select which files to include in their actual request.

## Core Workflow

1. User provides natural language prompt (e.g., "authentication system", "multi-agent coordination patterns")
2. Agent discovers documentation files:
   - `docs/research/**/*.md` - Research reports
   - `docs/plans/**/*.md` - Design and planning documents
   - `README*.md` - Project documentation
   - `CLAUDE.md` - Project context files
3. Agent reads and analyzes each file for relevance
4. Agent categorizes files into relevance tiers with detailed entries
5. Agent writes structured index to `/tmp/claude-context-<timestamp>.md`
6. User reviews index and copies relevant file paths into their request

## Agent Configuration

**YAML frontmatter:**
```yaml
---
name: context-indexing
description: Analyzes user prompts and discovers relevant local documentation, producing structured context indexes with tiered relevance assessments
tools: Bash, Glob, Grep, Read, Write
model: sonnet
---
```

**Input:** Natural language prompt describing the task/topic

**Output:** Structured markdown index at `/tmp/claude-context-<timestamp>.md`

## Output Format

```markdown
# Context Index: <user's prompt>

Generated: <ISO 8601 timestamp>
Prompt: <original user prompt>

## Highly Relevant

- **Path:** /workspace/docs/research/web/2025-12-05-multi-agent-orchestration.md
  **Type:** Web research report
  **Contains:** 15+ repo examples of agent coordination patterns including hub-and-spoke (vanzan01), quality gates (zhsama), and file-based state management (Dicklesworthstone). The "Orchestration Patterns" section covers handoff contracts and validation gates.
  **Relevance:** Directly addresses agent coordination mechanisms - see "Agent Coordination" and "State Management" sections

## Moderately Relevant

- **Path:** /workspace/docs/plans/2025-12-04-plugin-architecture-design.md
  **Type:** Design document
  **Contains:** Plugin structure, marketplace.json format, and component discovery mechanism
  **Relevance:** Plugin system informs how the coordination system registers and discovers agents

## Possibly Relevant

- **Path:** /workspace/README.md
  **Type:** Project documentation
  **Contains:** Project overview, installation instructions, and basic architecture description
  **Relevance:** Mentions agent system in overview but omits implementation details
```

## Entry Structure Design

Each index entry provides high-signal information for decision-making:

- **Path:** Absolute filesystem path
- **Type:** File classification (research report, design doc, README, etc.)
- **Contains:** Specific sections, patterns, examples the file includes (2-3 sentences)
- **Relevance:** Why this file matters for this prompt, which sections apply

This structure applies context engineering principles:
- High-signal tokens - every word informs
- Specific content signals - agents see what patterns and examples exist
- Just-in-time loading - sufficient information to decide whether to load the full file

## Relevance Tiers

**Highly Relevant:**
- Directly addresses the prompt's core topic
- Contains specific patterns, examples, or implementation details
- Central to understanding or solving the task

**Moderately Relevant:**
- Contains related concepts or tangential information
- Provides context or background without core implementation details
- Useful for broader understanding

**Possibly Relevant:**
- Mentions topic while focusing elsewhere
- Contains small useful sections
- Peripheral to the main task

**Not Relevant:**
- Excluded entirely from the index

## Discovery Workflow

1. **Parse Input**
   - Extract user's prompt
   - Generate timestamp for output filename

2. **Discover Documentation Files**
   - Glob `docs/research/**/*.md`
   - Glob `docs/plans/**/*.md`
   - Glob `README*.md` at root and key directories
   - Glob for `CLAUDE.md` files (`./.claude/CLAUDE.md`, `./CLAUDE.md`)
   - Result: List of absolute file paths

3. **Analyze Each File (token-efficient)**
   - Read file contents (use parallel reads when possible)
   - Determine file type from path and structure
   - Extract key topics and sections from headings and content
   - Assess relevance using tier criteria
   - Skip files matching no relevance tier
   - Build detailed entry for relevant files

4. **Generate Index Document**
   - Write to `/tmp/claude-context-<timestamp>.md`
   - Group entries by relevance tier
   - Include metadata (timestamp, original prompt)
   - Return filepath to user

## Token Management

- **Parallel reads:** Batch independent file reads in single message
- **Progressive disclosure:** Prioritize most recently modified files when 20+ exist
- **Early stopping:** Stop after finding sufficient highly relevant entries (8-10 highly + 10 moderately)
- **Selective reading:** Skip files when filename or path suggests irrelevance

## Error Handling

**No documentation files found:**
- Create index with message: "No documentation files found in docs/research/, docs/plans/, or root README files"
- Return index file so workflow continues

**No relevant files:**
- Create index with: "No files matched relevance criteria for prompt: <prompt>"
- Suggest broadening search scope or checking prompt

**File read failures:**
- Skip file, note in index: "⚠ Could not read: /path/to/file.md"
- Continue processing remaining files

**Ambiguous prompts:**
- Process with best effort
- Note in index: "Prompt may be too general for accurate relevance assessment"
- Process what you receive without asking clarifying questions

**Large file counts (50+ files):**
- Process most recently modified first
- Stop after finding 10 highly + 10 moderately relevant
- Note in index: "Analysis limited to most recent files for efficiency"

**Output guarantees:**
- Agent creates index file at `/tmp/claude-context-<timestamp>.md`
- Index includes timestamp, original prompt, and filepath
- Agent reports final filepath even when errors occur

## Current Limitations

1. **Documentation-only scope**
   - Excludes source code, tests, and configuration files
   - Misses relevant implementation details in code
   - Acceptable for initial version: start simple, add features later

2. **No cross-file relationship analysis**
   - Analyzes each file independently
   - Misses related files ("File A references File B, so both matter")

3. **Static relevance assessment**
   - One-pass analysis per file
   - No re-ranking or confidence scoring

4. **Ephemeral output**
   - `/tmp/` clears on reboot
   - No persistent cache of previous analyses

5. **Manual integration**
   - Users copy file paths from index
   - No auto-injection into agent prompts

## Future Extensions

**Additional search scopes:**
- Source code analysis (`src/**/*.ts`, `lib/**/*.py`, etc.)
- Test files for implementation examples
- Configuration files for system setup

**Smarter analysis:**
- Cross-file relationship detection (follow links/references)
- Semantic search via embeddings
- Confidence scoring and re-ranking

**Persistence and caching:**
- Option to save to `.claude/context/` for reuse
- Memoization for repeated prompts
- Index versioning and updates

**Integration improvements:**
- Auto-injection into Task tool prompts
- MCP server exposure for programmatic access
- Configuration for custom search paths and patterns

## Design Rationale

**Why documentation-only initially?**
- Documentation files offer higher signal-to-noise (pre-summarized)
- Assessing relevance requires no deep code analysis
- Core workflow iterates and validates faster
- Code search extends naturally once proven valuable

**Why three-tier relevance?**
- LLMs excel at categorical thinking over numeric calibration
- Tiers force clearer reasoning about relevance
- Users can easily "grab all Highly Relevant files"

**Why manual integration?**
- Users control what context they include
- Prevents automatic context pollution
- Simplifies first implementation
- Auto-injection adds value later if workflow proves successful

**Why /tmp/ storage?**
- Ephemeral nature matches preprocessing use case
- Prevents clutter in project directories
- Auto-cleanup occurs on reboot
- Persistent storage extends naturally later

**Why detailed entry structure?**
- Applies context engineering principles (high-signal tokens)
- Agents decide without loading files
- Reduces wasted file reads
- Index serves as standalone reference

## Success Criteria

The agent succeeds when:
1. Users provide a prompt and receive relevant file suggestions
2. Index entries contain sufficient detail for informed decisions
3. Manual file linking becomes faster and more comprehensive
4. Truly relevant files appear in results (no false negatives)
5. The "possibly relevant" tier catches edge cases (acceptable false positive rate)

## Next Steps

1. Implement agent following this design
2. Create template for index output format
3. Test with real prompts from recent work
4. Validate relevance assessment accuracy
5. Iterate on entry detail level based on usage
6. Consider extensions once core workflow proven
