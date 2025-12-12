"""Data processing utilities for lifecycle tracking."""

import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


def get_toolbox_root(hook_input: Dict[str, Any] = None) -> str:
    """Get TOOLBOX_ROOT from environment or env file, with fallback to cwd."""
    # Try environment variable first
    toolbox_root = os.environ.get("TOOLBOX_ROOT")
    if toolbox_root:
        return toolbox_root

    # Try reading from CLAUDE_ENV_FILE
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if env_file and Path(env_file).exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('export TOOLBOX_ROOT='):
                        # Parse: export TOOLBOX_ROOT="/workspace"
                        value = line.split('=', 1)[1].strip()
                        # Remove quotes
                        toolbox_root = value.strip('"\'')
                        if toolbox_root:
                            return toolbox_root
        except Exception:
            pass

    # Fallback to cwd from hook_input
    if hook_input:
        cwd = hook_input.get("cwd")
        if cwd:
            return cwd

    return ""


def generate_request_id(hook_input: Dict[str, Any]) -> str:
    """Generate deterministic request ID: {timestamp}_{hash}"""
    session_id = hook_input.get("session_id", "")
    timestamp = hook_input.get("timestamp", "")
    prompt = hook_input.get("prompt", "")

    # If no timestamp provided, generate one
    if not timestamp:
        timestamp = datetime.now().isoformat()

    timestamp_safe = timestamp.replace(":", "-")
    hash_input = f"{session_id}{timestamp}{prompt}"
    hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()
    hash_short = hash_digest[:8]

    return f"{timestamp_safe}_{hash_short}"


def create_request_directory(toolbox_root: str, request_id: str) -> Path:
    """Create .toolbox/events/{request_id}/ with subdirs"""
    request_dir = Path(toolbox_root) / ".toolbox" / "events" / request_id
    request_dir.mkdir(parents=True, exist_ok=True)
    (request_dir / "work").mkdir(exist_ok=True)
    (request_dir / "session-logs").mkdir(exist_ok=True)
    (request_dir / "hook-events.jsonl").touch()
    (request_dir / "errors.log").touch()
    return request_dir


def parse_context_tags(text: str) -> List[str]:
    """Extract content from <context> tags"""
    pattern = r'<context>(.*?)</context>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [match.strip() for match in matches]


def parse_work_tags(text: str) -> List[Dict[str, str]]:
    """Extract {filename, content} from <work> tags"""
    pattern = r'<work\s+filename="([^"]+)"\s*>(.*?)</work>'
    matches = re.findall(pattern, text, re.DOTALL)
    return [{"filename": filename, "content": content.strip()} for filename, content in matches]
