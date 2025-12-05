#!/usr/bin/env python3
"""Extract all messages in a trace from Claude Code transcript."""

import json
import sys
import os
import glob
import argparse
import time

parser = argparse.ArgumentParser(description="Extract messages in a trace from Claude Code transcript")
parser.add_argument("trace_prefix", help="Trace ID prefix to search for")
parser.add_argument("-w", "--watch", action="store_true", help="Watch for new messages in the trace")
args = parser.parse_args()

trace_prefix = args.trace_prefix
transcript_path = None

# Try to read transcript path from trace info file
try:
    with open(f"/tmp/claude-trace-info-{trace_prefix}") as f:
        transcript_path = f.read().strip()
except FileNotFoundError:
    pass

# Fallback: look for most recent transcript in current project
if not transcript_path or not os.path.exists(transcript_path):
    project_dir = os.path.expanduser("~/.claude/projects/-workspace")
    if os.path.isdir(project_dir):
        transcripts = glob.glob(os.path.join(project_dir, "*.jsonl"))
        if transcripts:
            # Sort by modification time, most recent first
            transcript_path = max(transcripts, key=os.path.getmtime)

if not transcript_path:
    print(f"Error: No transcript found for trace {trace_prefix}", file=sys.stderr)
    sys.exit(1)

# Load all messages
messages = []
try:
    with open(transcript_path) as f:
        for line in f:
            try:
                msg = json.loads(line)
                if isinstance(msg, dict):
                    messages.append(msg)
            except json.JSONDecodeError:
                continue
except FileNotFoundError:
    print(f"Error: Transcript not found at {transcript_path}", file=sys.stderr)
    sys.exit(1)

# Find root message
root = None
for msg in messages:
    if msg.get('uuid', '').startswith(trace_prefix):
        root = msg
        break

if not root:
    print(f"Error: No message found with trace ID starting with {trace_prefix}", file=sys.stderr)
    sys.exit(1)

# Build set of all UUIDs in trace by following parent chain
# Stop when we hit another user message (next turn)
trace_uuids = {root['uuid']}
changed = True
while changed:
    changed = False
    for msg in messages:
        parent_uuid = msg.get('parentUuid')
        if parent_uuid and parent_uuid in trace_uuids and msg['uuid'] not in trace_uuids:
            # Stop if this is a user message (marks start of next turn)
            if msg.get('type') == 'user':
                continue
            trace_uuids.add(msg['uuid'])
            changed = True

# Output all messages in the trace
output_uuids = set()
for msg in messages:
    if msg.get('uuid') in trace_uuids:
        print(json.dumps(msg))
        sys.stdout.flush()
        output_uuids.add(msg['uuid'])

# Watch mode: continue monitoring for new messages
if args.watch:
    try:
        with open(transcript_path) as f:
            # Seek to end of file
            f.seek(0, os.SEEK_END)

            while True:
                line = f.readline()
                if line:
                    try:
                        msg = json.loads(line)
                        if isinstance(msg, dict):
                            msg_uuid = msg.get('uuid')
                            parent_uuid = msg.get('parentUuid')

                            # Check if this message belongs to our trace
                            if msg_uuid and msg_uuid not in output_uuids:
                                if parent_uuid and parent_uuid in trace_uuids:
                                    # This is a child of a message in our trace
                                    trace_uuids.add(msg_uuid)
                                    output_uuids.add(msg_uuid)
                                    print(json.dumps(msg))
                                    sys.stdout.flush()
                    except json.JSONDecodeError:
                        continue
                else:
                    # No new data, wait a bit
                    time.sleep(0.1)
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        pass
