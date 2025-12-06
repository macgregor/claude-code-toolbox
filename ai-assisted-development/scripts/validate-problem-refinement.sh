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
  echo "Error: File path must match pattern: docs/plans/<name>-refinement.md" >&2
  echo "Got: $REPORT_FILE" >&2
  exit 1
fi

# Check for unfilled REQUIRED placeholders
SPECIFIC_PLACEHOLDERS=(
  "[REQUIRED: Problem Name]"
  "[REQUIRED: Original user-provided problem statement]"
  "[REQUIRED: Evolving description based on refinement - initially same as problem statement]"
  "[REQUIRED: ready | needs_more_refinement]"
  "[REQUIRED: high | medium | low]"
)

# Check each specific placeholder
for placeholder in "${SPECIFIC_PLACEHOLDERS[@]}"; do
  if grep -q -F "$placeholder" "$REPORT_FILE"; then
    echo "Error: Placeholder not replaced: $placeholder" >&2
    exit 1
  fi
done

# If status is needs_more_refinement, require Missing Information
STATUS=$(grep -E '^\*\*Status:\*\* (ready|needs_more_refinement)' "$REPORT_FILE" | sed 's/\*\*Status:\*\* //')
if [[ "$STATUS" == "needs_more_refinement" ]]; then
  if ! grep -q '^\*\*Missing Information:\*\* ' "$REPORT_FILE"; then
    echo "Error: Missing Information field required when status is needs_more_refinement" >&2
    exit 1
  fi
  if grep -q -F "[REQUIRED if needs_more_refinement: List of gaps]" "$REPORT_FILE"; then
    echo "Error: Missing Information placeholder must be replaced" >&2
    exit 1
  fi
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

echo "Validation passed: $REPORT_FILE"
exit 0