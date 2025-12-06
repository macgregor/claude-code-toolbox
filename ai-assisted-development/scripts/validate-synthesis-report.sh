#!/bin/bash

set -e

if [ $# -lt 1 ]; then
  echo "Usage: $0 <synthesis-report-file>" >&2
  exit 1
fi

REPORT_FILE="$1"

# Verify file exists
if [ ! -f "$REPORT_FILE" ]; then
  echo "Error: File not found: $REPORT_FILE" >&2
  exit 1
fi

# Verify path pattern (.orchestrator/synthesis/YYYY-MM-DD-*.md)
if [[ ! "$REPORT_FILE" =~ \.orchestrator/synthesis/[0-9]{4}-[0-9]{2}-[0-9]{2}-.+\.md$ ]]; then
  echo "Error: File path must match pattern: .orchestrator/synthesis/YYYY-MM-DD-<topic>-<desc>.md" >&2
  echo "Got: $REPORT_FILE" >&2
  exit 1
fi

# Check for unfilled placeholders
UNFILLED=$(grep -c '\[REQUIRED:' "$REPORT_FILE" || true)
if [ "$UNFILLED" -gt 0 ]; then
  echo "Error: Found $UNFILLED unfilled placeholders in $REPORT_FILE" >&2
  grep '\[REQUIRED:' "$REPORT_FILE" >&2
  exit 1
fi

# Verify required sections exist
REQUIRED_SECTIONS=(
  "# Synthesis:"
  "## User Objective"
  "## Input Sources"
  "## Key Patterns Identified"
  "## Conflicting Information"
  "## Recommendations"
)

for section in "${REQUIRED_SECTIONS[@]}"; do
  if ! grep -q "^${section}" "$REPORT_FILE"; then
    echo "Error: Required section not found: $section" >&2
    exit 1
  fi
done

echo "Validation passed: $REPORT_FILE"
exit 0
