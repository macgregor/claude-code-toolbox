#!/bin/bash

set -e

# Setup: Create test directory
mkdir -p /workspace/docs/plans

# Helper function to run validation script
validate() {
    bash /workspace/ai-assisted-development/scripts/validate-problem-refinement.sh "$1"
}

# Test helper function to expect failure
expect_failure() {
    if validate "$1"; then
        echo "Test failed: Expected validation to fail for $1"
        exit 1
    else
        echo "Test passed: Validation failed as expected for $1"
    fi
}

# Test helper function to expect success
expect_success() {
    if validate "$1"; then
        echo "Test passed: Validation succeeded for $1"
    else
        echo "Test failed: Validation failed unexpectedly for $1"
        exit 1
    fi
}

# Test 1: Valid file with filled placeholders
cat > /workspace/docs/plans/001-refinement.md << EOF
# Problem Refinement:

## Problem Statement
A complete problem statement

## Current Understanding
Detailed understanding

## Refinement Log
### Iteration 1
Initial refinement details

## Readiness Assessment
**Status:** ready
**Confidence:** medium

## Miscellaneous
No placeholders remain
EOF
expect_success /workspace/docs/plans/001-refinement.md

# Test 2: File with unfilled placeholder (should fail)
cat > /workspace/docs/plans/002-refinement.md << EOF
# Problem Refinement:

## Problem Statement
[REQUIRED: Problem Name]

## Current Understanding
Detailed understanding

## Refinement Log
### Iteration 1
Initial refinement details

## Readiness Assessment
**Status:** ready
**Confidence:** medium
EOF
expect_failure /workspace/docs/plans/002-refinement.md

# Test 3: Needs more refinement with filled Missing Information
cat > /workspace/docs/plans/003-refinement.md << EOF
# Problem Refinement:

## Problem Statement
A clear problem statement

## Current Understanding
Detailed understanding

## Refinement Log
### Iteration 1
Initial refinement details

## Readiness Assessment
**Status:** needs_more_refinement
**Confidence:** medium
**Missing Information:** Additional research needed on X, Y, and Z
EOF
expect_success /workspace/docs/plans/003-refinement.md

# Test 4: Needs more refinement without Missing Information (should fail)
cat > /workspace/docs/plans/004-refinement.md << EOF
# Problem Refinement:

## Problem Statement
A clear problem statement

## Current Understanding
Detailed understanding

## Refinement Log
### Iteration 1
Initial refinement details

## Readiness Assessment
**Status:** needs_more_refinement
**Confidence:** medium
EOF
expect_failure /workspace/docs/plans/004-refinement.md

# Test 5: Needs more refinement with placeholder (should fail)
cat > /workspace/docs/plans/005-refinement.md << EOF
# Problem Refinement:

## Problem Statement
A clear problem statement

## Current Understanding
Detailed understanding

## Refinement Log
### Iteration 1
Initial refinement details

## Readiness Assessment
**Status:** needs_more_refinement
**Confidence:** medium
**Missing Information:** [REQUIRED if needs_more_refinement: List of gaps]
EOF
expect_failure /workspace/docs/plans/005-refinement.md

echo "All tests passed successfully!"