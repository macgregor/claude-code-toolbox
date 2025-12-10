# Orchestration Foundation Implementation Plan

**Goal:** Add request-scoped tracking to existing agent-lifecycle.py

**Approach:** Evolve the existing `agent-lifecycle.py` by adding orchestration logic to the handler functions that already exist. NO new files, NO separate utils, keep it simple.

---

## Implementation Tasks

### Task 1: Add Helper Functions to agent-lifecycle.py

Add these functions to the top of `agent-lifecycle.py` (after imports, before main()):

```python
import hashlib
import re
import os
import shutil
from typing import Dict, Any, List

def generate_request_id(hook_input: Dict[str, Any]) -> str:
    """Generate deterministic request ID: {timestamp}_{hash}"""
    session_id = hook_input.get("session_id", "")
    timestamp = hook_input.get("timestamp", "")
    prompt = hook_input.get("prompt", "")

    timestamp_safe = timestamp.replace(":", "-")
    hash_input = f"{session_id}{timestamp}{prompt}"
    hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()
    hash_short = hash_digest[:8]

    return f"{timestamp_safe}_{hash_short}"

def create_request_directory(toolbox_root: str, request_id: str) -> Path:
    """Create .toolbox/events/{request_id}/ with work/, session-logs/ subdirs"""
    request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id
    request_dir.mkdir(parents=True, exist_ok=True)
    (request_dir / "work").mkdir(exist_ok=True)
    (request_dir / "session-logs").mkdir(exist_ok=True)
    (request_dir / "hook-events.jsonl").touch()
    (request_dir / "errors.log").touch()
    return request_dir

def get_current_request_id(toolbox_root: str) -> str:
    """Read current request ID from .toolbox/events/.current-request-id"""
    try:
        current_id_file = Path(toolbox_root) / ".toolbox" / "events" / ".current-request-id"
        if current_id_file.exists():
            return current_id_file.read_text().strip()
    except Exception:
        pass
    return ""

def parse_context_tags(text: str) -> List[str]:
    """Extract content from <context> tags"""
    pattern = r'<context>(.*?)</context>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [match.strip() for match in matches]

def parse_work_tags(text: str) -> List[Dict[str, str]]:
    """Extract {relpath, content} from <work> tags"""
    pattern = r'<work\s+relpath="([^"]+)"(?:\s+abspath="[^"]+")?\s*>(.*?)</work>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [{"relpath": relpath, "content": content.strip()} for relpath, content in matches]
```

**Test:** Run the script with a test event to ensure it still works.

**Commit:**
```bash
git add scripts/agent-lifecycle.py
git commit -m "feat: add orchestration helper functions to agent-lifecycle.py"
```

---

### Task 2: Modify handle_session_start()

Replace the existing `handle_session_start()` function:

```python
def handle_session_start(hook_input):
    """Handle SessionStart event - setup TOOLBOX_ROOT and create events dir."""
    log_path = log_hook_event("SessionStart", hook_input)

    try:
        cwd = hook_input.get("cwd")
        env_file = os.environ.get("CLAUDE_ENV_FILE")

        # Write TOOLBOX_ROOT to env file
        if env_file and cwd:
            with open(env_file, 'a') as f:
                f.write(f'export TOOLBOX_ROOT="{cwd}"\n')

        # Create .toolbox/events directory
        if cwd:
            events_dir = Path(cwd) / ".toolbox" / "events"
            events_dir.mkdir(parents=True, exist_ok=True)

        print(f"[SessionStart] TOOLBOX_ROOT={cwd}")
    except Exception as e:
        print(f"[SessionStart] ERROR: {e}", file=sys.stderr)

    print(f"Logged to: {log_path}")
    sys.exit(0)
```

**Test:** Trigger SessionStart event, check that TOOLBOX_ROOT is set and .toolbox/events/ created.

**Commit:**
```bash
git add scripts/agent-lifecycle.py
git commit -m "feat: add TOOLBOX_ROOT setup to SessionStart handler"
```

---

### Task 3: Modify handle_user_prompt_submit()

Replace the existing `handle_user_prompt_submit()` function:

```python
def handle_user_prompt_submit(hook_input):
    """Handle UserPromptSubmit - create request, initialize context.md."""
    log_path = log_hook_event("UserPromptSubmit", hook_input)

    try:
        toolbox_root = os.environ.get("TOOLBOX_ROOT")
        if not toolbox_root:
            print("[UserPromptSubmit] TOOLBOX_ROOT not set, skipping orchestration")
            sys.exit(0)

        # Generate request ID
        request_id = generate_request_id(hook_input)

        # Write to .current-request-id
        events_dir = Path(toolbox_root) / ".toolbox" / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        current_id_file = events_dir / ".current-request-id"
        current_id_file.write_text(request_id)

        # Create request directory
        request_dir = create_request_directory(toolbox_root, request_id)

        # Initialize context.md
        prompt = hook_input.get("prompt", "")
        context_file = request_dir / "context.md"
        context_file.write_text(f"""<userPrompt>
{prompt}
</userPrompt>

<!-- Hooks append agent context below as agents complete -->
""")

        # Extract start UUID from session log
        transcript_path = hook_input.get("transcript_path")
        if transcript_path and Path(transcript_path).exists():
            with open(transcript_path, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_msg = json.loads(lines[-1])
                    start_uuid = last_msg.get("uuid", "")
                    if start_uuid:
                        (request_dir / ".start-uuid").write_text(start_uuid)

        # Log to request's hook-events.jsonl
        hook_events_file = request_dir / "hook-events.jsonl"
        with open(hook_events_file, 'a') as f:
            f.write(json.dumps(hook_input) + '\n')

        print(f"[UserPromptSubmit] Created request: {request_id}")
    except Exception as e:
        print(f"[UserPromptSubmit] ERROR: {e}", file=sys.stderr)

    print(f"Logged to: {log_path}")
    sys.exit(0)
```

**Test:** Submit a prompt, verify request directory created with context.md.

**Commit:**
```bash
git add scripts/agent-lifecycle.py
git commit -m "feat: add request creation to UserPromptSubmit handler"
```

---

### Task 4: Modify handle_subagent_stop()

Replace the existing `handle_subagent_stop()` function:

```python
def handle_subagent_stop(hook_input):
    """Handle SubagentStop - copy transcript, extract context/work tags."""
    log_path = log_hook_event("SubagentStop", hook_input)

    try:
        toolbox_root = os.environ.get("TOOLBOX_ROOT")
        if not toolbox_root:
            sys.exit(0)

        request_id = get_current_request_id(toolbox_root)
        if not request_id:
            print("[SubagentStop] No active request")
            sys.exit(0)

        request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id
        agent_id = hook_input.get("agent_id", "unknown")
        agent_type = hook_input.get("agent_type", "unknown")
        agent_transcript_path = hook_input.get("agent_transcript_path")

        if not agent_transcript_path or not Path(agent_transcript_path).exists():
            print(f"[SubagentStop] No transcript for {agent_type}")
            sys.exit(0)

        # Copy agent transcript
        transcript_copy = request_dir / "session-logs" / f"agent-{agent_id}.jsonl"
        shutil.copy2(agent_transcript_path, transcript_copy)

        # Extract final agent output
        with open(agent_transcript_path, 'r') as f:
            lines = f.readlines()

        final_output = ""
        for line in reversed(lines):
            msg = json.loads(line)
            if msg.get("type") == "assistant":
                final_output = msg.get("message", {}).get("content", "")
                break

        # Parse and append context tags
        contexts = parse_context_tags(final_output)
        if contexts:
            context_file = request_dir / "context.md"
            with open(context_file, 'a') as f:
                f.write(f'\n<agent-{agent_id} type="{agent_type}">\n')
                for context in contexts:
                    f.write(context + '\n')
                f.write(f'</agent-{agent_id}>\n')

        # Parse and write work files
        work_items = parse_work_tags(final_output)
        for item in work_items:
            work_path = request_dir / item["relpath"]
            work_path.parent.mkdir(parents=True, exist_ok=True)
            work_path.write_text(item["content"])

        # Log to request's hook-events.jsonl
        hook_events_file = request_dir / "hook-events.jsonl"
        with open(hook_events_file, 'a') as f:
            f.write(json.dumps(hook_input) + '\n')

        print(f"[SubagentStop] {agent_type} completed")
        if contexts:
            print(f"  Extracted {len(contexts)} context tag(s)")
        if work_items:
            print(f"  Wrote {len(work_items)} work file(s)")
    except Exception as e:
        print(f"[SubagentStop] ERROR: {e}", file=sys.stderr)

    print(f"Logged to: {log_path}")
    sys.exit(0)
```

**Test:** Spawn an agent that outputs `<context>` and `<work>` tags, verify extraction.

**Commit:**
```bash
git add scripts/agent-lifecycle.py
git commit -m "feat: add context/work extraction to SubagentStop handler"
```

---

### Task 5: Modify handle_stop_event()

Replace the existing `handle_stop_event()` function:

```python
def handle_stop_event(hook_input):
    """Handle Stop - prune session log between start and end UUIDs."""
    log_path = log_hook_event("Stop", hook_input)

    try:
        toolbox_root = os.environ.get("TOOLBOX_ROOT")
        if not toolbox_root:
            sys.exit(0)

        request_id = get_current_request_id(toolbox_root)
        if not request_id:
            print("[Stop] No active request")
            sys.exit(0)

        request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id

        # Read start UUID
        start_uuid_file = request_dir / ".start-uuid"
        if not start_uuid_file.exists():
            print("[Stop] No start UUID found")
            sys.exit(0)

        start_uuid = start_uuid_file.read_text().strip()

        # Get end UUID from session log
        transcript_path = hook_input.get("transcript_path")
        if not transcript_path or not Path(transcript_path).exists():
            sys.exit(0)

        with open(transcript_path, 'r') as f:
            lines = f.readlines()

        messages = [json.loads(line) for line in lines]

        # Find start and end indices
        start_idx = None
        end_idx = None
        for idx, msg in enumerate(messages):
            if msg.get("uuid") == start_uuid:
                start_idx = idx
            if msg == messages[-1]:  # Last message is end
                end_idx = idx

        # Prune and save
        if start_idx is not None and end_idx is not None:
            pruned_messages = messages[start_idx:end_idx + 1]
            session_id = hook_input.get("session_id", "unknown")
            pruned_log_path = request_dir / "session-logs" / f"{session_id}-pruned.jsonl"

            with open(pruned_log_path, 'w') as f:
                for msg in pruned_messages:
                    f.write(json.dumps(msg) + '\n')

            print(f"[Stop] Pruned session log: {len(pruned_messages)} messages")

        # Log to request's hook-events.jsonl
        hook_events_file = request_dir / "hook-events.jsonl"
        with open(hook_events_file, 'a') as f:
            f.write(json.dumps(hook_input) + '\n')
    except Exception as e:
        print(f"[Stop] ERROR: {e}", file=sys.stderr)

    print(f"Logged to: {log_path}")
    sys.exit(0)
```

**Test:** Complete a session, verify pruned session log created.

**Commit:**
```bash
git add scripts/agent-lifecycle.py
git commit -m "feat: add session log pruning to Stop handler"
```

---

## Verification

After all tasks:

```bash
# Test with a real session
# 1. Submit a prompt
# 2. Check .toolbox/events/ structure
ls -la .toolbox/events/
cat .toolbox/events/.current-request-id
ls -la .toolbox/events/$(cat .toolbox/events/.current-request-id)/

# 3. Spawn an agent that outputs tags
# 4. Verify context.md updated
cat .toolbox/events/$(cat .toolbox/events/.current-request-id)/context.md
```

---

## Success Criteria

✅ All changes in ONE file: `agent-lifecycle.py`
✅ Request directories created on UserPromptSubmit
✅ Context extracted from agent `<context>` tags
✅ Work files written from agent `<work>` tags
✅ Session logs pruned on Stop
✅ All errors graceful (exit 0, log to stderr)
