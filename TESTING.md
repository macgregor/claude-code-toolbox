# Document Reviewer Testing Guide

## Implementation Status

**Completed:**
- ✅ Hook infrastructure (SubagentStart/SubagentStop)
- ✅ Hook script (`agent-lifecycle.py`) with JSON extraction
- ✅ Document reviewer agent prompt
- ✅ Plugin manifest registration
- ✅ Hook script validation with mock data

**Pending:**
- ⏳ Plugin reload (required before testing)
- ⏳ End-to-end integration test
- ⏳ Real document review test

## Next Steps

### 1. Reload Plugin

The plugin must be reloaded to activate the new hooks and updated agent:

```bash
# Option A: Restart Claude Code CLI
# Exit and restart the CLI

# Option B: Reload plugin (if available)
/plugin reload ai-assisted-development
```

### 2. Test Document Reviewer

Create a simple test document:

```bash
cat > /tmp/test-doc.md << 'EOF'
# Test Document

This document is used to test the document reviewer agent.

## Section 1

Requests are processed by the system. The data is transformed by the processor.

## Section 2

This is a very long sentence that contains more than thirty words which makes it difficult to read and understand and should probably be split into multiple shorter sentences for better clarity.

## Section 3

We use sub-agent sometimes and subagent other times.
EOF
```

### 3. Invoke Document Reviewer

```bash
# Standard review
Task(
  subagent_type="document-reviewer",
  prompt="Review /tmp/test-doc.md"
)

# Quick review
Task(
  subagent_type="document-reviewer",
  prompt="Quick review of /tmp/test-doc.md"
)

# Thorough review
Task(
  subagent_type="document-reviewer",
  prompt="Thorough review of /tmp/test-doc.md"
)
```

### 4. Expected Behavior

**During Execution:**

SubagentStart hook should:
- Print: `[SubagentStart] document-reviewer initialized`
- Print: `Workspace: /tmp/document-reviewer-workspace`
- Create workspace directory

Agent should:
- Read the document
- Analyze across 7 quality dimensions
- Output ONLY valid JSON (no extra text)

SubagentStop hook should:
- Extract final assistant message
- Parse as JSON
- Print: `[SubagentStop] document-reviewer completed`
- Print: `Output: /tmp/document-reviewer-output/test-doc-YYYY-MM-DD-HHMMSS.json`
- Save JSON to that path

**Validation:**

Check the output file exists:
```bash
ls -la /tmp/document-reviewer-output/
```

Verify JSON structure:
```bash
cat /tmp/document-reviewer-output/test-doc-*.json | python -m json.tool
```

Expected JSON fields:
- `document`: Path to reviewed file
- `reviewed_at`: ISO 8601 timestamp
- `verification_depth`: "standard" | "quick" | "thorough"
- `summary`: Issue counts and overall score
- `issues`: Array of issues with confidence scores
- `scores_by_category`: Scores for all 7 dimensions

### 5. Test Cases

**Test 1: Valid markdown document**
- Should produce JSON report with identified issues
- Expected: Passive voice, complex sentences, terminology inconsistency

**Test 2: Non-markdown file**
```bash
Task(
  subagent_type="document-reviewer",
  prompt="Review /tmp/test.py"
)
```
- Should output error JSON: `{"error": "Document reviewer only supports markdown files", ...}`

**Test 3: Missing file**
```bash
Task(
  subagent_type="document-reviewer",
  prompt="Review /tmp/does-not-exist.md"
)
```
- Should output error JSON: `{"error": "Document not found", "path": "/tmp/does-not-exist.md"}`

**Test 4: Perfect document (no issues)**
```bash
cat > /tmp/perfect-doc.md << 'EOF'
# Perfect Document

This document follows all best practices.

The system processes requests efficiently.
EOF

Task(
  subagent_type="document-reviewer",
  prompt="Review /tmp/perfect-doc.md"
)
```
- Should output JSON with empty issues array and all scores = 10.0

## Troubleshooting

### Hook not firing

**Symptom:** No `[SubagentStart]` or `[SubagentStop]` messages

**Cause:** Plugin not reloaded after hook changes

**Fix:** Restart Claude Code or reload plugin

### Exit Code 2 / Blocked

**Symptom:** `[SubagentStop] ERROR: Invalid JSON in agent output`

**Cause:** Agent output non-JSON text in final message

**Fix:** Check agent transcript, ensure final message is pure JSON

### No output file created

**Symptom:** Hook prints completion but no file in `/tmp/document-reviewer-output/`

**Cause:** JSON parsing succeeded but file write failed

**Fix:** Check permissions on `/tmp/`, verify disk space

### Field name errors

**Symptom:** `[agent-lifecycle] ERROR: Cannot find agent name in hook input`

**Cause:** Hook input doesn't contain expected `subagent_type` field

**Fix:** Check actual hook input structure, update `extract_agent_name()` fallback chain

## Implementation Notes

**Hook Pattern:**
- Universal script handles all agents via convention
- Agent-specific output directories: `/tmp/{agent-name}-output/`
- Workspace directories: `/tmp/{agent-name}-workspace/`

**JSON Output Contract:**
- Agent MUST output pure JSON in final message
- Hook validates and blocks with Exit Code 2 if invalid
- Hook persists to filesystem deterministically

**Agent Name Extraction:**
- Tries: `subagent_type` → `agent_id` → `agent_name`
- Strips plugin prefix if present (`plugin:name` → `name`)
- Exits with code 2 if no identifier found

## References

- Design: `docs/plans/2025-12-09-document-reviewer-phase1-design.md`
- Implementation Plan: `docs/plans/2025-12-09-document-reviewer-phase1-implementation.md`
- Hook Script: `ai-assisted-development/scripts/agent-lifecycle.py`
- Agent Prompt: `ai-assisted-development/agents/document-reviewer.md`
- Hooks Config: `ai-assisted-development/hooks/hooks.json`
