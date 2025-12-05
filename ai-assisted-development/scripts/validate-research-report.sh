#!/bin/bash
# Validates web research reports
# Called explicitly by web-research skill as workflow step
# Usage: validate-research-report.sh <filepath>

set -euo pipefail

# Check argument
if [ $# -ne 1 ]; then
  echo "ERROR: Usage: validate-research-report.sh <filepath>" >&2
  exit 1
fi

FILE_PATH="$1"

# Check if file exists
if [ ! -f "$FILE_PATH" ]; then
  echo "ERROR: File not found: $FILE_PATH" >&2
  exit 1
fi

ERRORS=()

# Check 1: No unfilled placeholders
if grep -q '\[REQUIRED:' "$FILE_PATH"; then
  ERRORS+=("Unfilled placeholders found:")
  while IFS= read -r line; do
    ERRORS+=("  - $line")
  done < <(grep -o '\[REQUIRED:[^]]*\]' "$FILE_PATH")
fi

# Check 2: Path pattern matches docs/research/YYYY-MM-DD-*.md
if [[ ! "$FILE_PATH" =~ docs/research/[0-9]{4}-[0-9]{2}-[0-9]{2}-.+\.md$ ]]; then
  ERRORS+=("Path does not match pattern: docs/research/YYYY-MM-DD-*.md")
  ERRORS+=("  Actual path: $FILE_PATH")
fi

# Check 3: Required sections exist
REQUIRED_SECTIONS=(
  "# Research:"
  "## Research Objective"
  "## Executive Summary"
  "## Findings"
  "### Official Documentation"
  "### Source Code Repositories"
  "### Community/Third-party"
  "## Sources"
  "## Metadata"
)

for section in "${REQUIRED_SECTIONS[@]}"; do
  if ! grep -q "^$section" "$FILE_PATH"; then
    ERRORS+=("Missing required section: $section")
  fi
done

# Report errors if any
if [ ${#ERRORS[@]} -gt 0 ]; then
  echo "ERROR: Research report validation failed for: $FILE_PATH" >&2
  for error in "${ERRORS[@]}"; do
    echo "$error" >&2
  done
  exit 1
fi

# Validation passed
echo "Validation passed: $FILE_PATH"
exit 0
