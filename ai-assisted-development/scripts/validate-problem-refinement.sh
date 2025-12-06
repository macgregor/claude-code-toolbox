#!/bin/bash

set -e

if [ $# -lt 1 ]; then
  echo "Usage: $0 <problem-refinement-file>" >&2
  exit 1
fi

REPORT_FILE="$1"

# Verify file exists
if [ ! -f "$REPORT_FILE" ]; then
  echo "Error: File not found: $REPORT_FILE" >&2
  exit 1
fi

# Verify path pattern (docs/plans/*-refinement.md)
if [[ ! "$REPORT_FILE" =~ docs/plans/.*-refinement\.md$ ]]; then
  echo "Error: File path must match pattern: docs/plans/<n>-refinement.md" >&2
  echo "Got: $REPORT_FILE" >&2
  exit 1
fi

# Check for unfilled REQUIRED placeholders
UNFILLED=$(grep -c '\[REQUIRED:' "$REPORT_FILE" || true)
if [ "$UNFILLED" -gt 0 ]; then
  echo "Error: Found $UNFILLED unfilled REQUIRED placeholders in $REPORT_FILE" >&2
  grep '\[REQUIRED:' "$REPORT_FILE" >&2
  exit 1
fi

# Verify required sections exist
REQUIRED_SECTIONS=(
  "# Problem Refinement:"
  "## Problem Statement"
  "## Current Understanding"
  "## Refinement Log"
  "## Readiness Assessment"
)

for section in "${REQUIRED_SECTIONS[@]}"; do
  if ! grep -q "^${section}" "$REPORT_FILE"; then
    echo "Error: Required section not found: $section" >&2
    exit 1
  fi
done

# Verify status is valid value
if ! grep -E '^\*\*Status:\*\* (ready|needs_more_refinement)' "$REPORT_FILE" > /dev/null; then
  echo "Error: Status must be 'ready' or 'needs_more_refinement'" >&2
  exit 1
fi

# Verify confidence is valid value
if ! grep -E '^\*\*Confidence:\*\* (high|medium|low)' "$REPORT_FILE" > /dev/null; then
  echo "Error: Confidence must be 'high', 'medium', or 'low'" >&2
  exit 1
fi

# Verify at least one iteration in log
if ! grep -E '^### Iteration [0-9]+' "$REPORT_FILE" > /dev/null; then
  echo "Error: Refinement log must contain at least one iteration" >&2
  exit 1
fi

echo "Validation passed: $REPORT_FILE"
exit 0