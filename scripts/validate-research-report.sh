#!/bin/bash
# Validates web research reports
# Called by PostToolUse Write hook

FILEPATH="$1"

# Check if file exists
if [ ! -f "$FILEPATH" ]; then
  exit 0
fi

# Check for unique identifier
if ! grep -q "agent-type.*web-research-agent-v1-7k9p3x2m" "$FILEPATH"; then
  # Not a research report, exit silently
  exit 0
fi

# It's a research report - validate format
ERRORS=()

# Check if path matches docs/research/YYYY-MM-DD-*.md
if [[ ! "$FILEPATH" =~ ^.*/docs/research/[0-9]{4}-[0-9]{2}-[0-9]{2}-.+\.md$ ]]; then
  ERRORS+=("Path must be docs/research/YYYY-MM-DD-<topic>.md, got: $FILEPATH")
fi

# Check required sections
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
  if ! grep -q "^$section" "$FILEPATH"; then
    ERRORS+=("Missing required section: $section")
  fi
done

# Check metadata fields
METADATA_FIELDS=(
  "agent-type.*web-research-agent-v1-7k9p3x2m"
  "Research Date:"
  "Search Queries:"
  "Agent Model:"
)

for field in "${METADATA_FIELDS[@]}"; do
  if ! grep -q "$field" "$FILEPATH"; then
    ERRORS+=("Missing metadata field: $field")
  fi
done

# Report errors if any
if [ ${#ERRORS[@]} -gt 0 ]; then
  echo "Research report validation failed:"
  for error in "${ERRORS[@]}"; do
    echo "  - $error"
  done
  exit 1
fi

# Validation passed
exit 0
