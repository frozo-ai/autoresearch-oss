#!/usr/bin/env bash
# Eval harness for test-pass template.
# Runs pytest on test_solution.py and reports pass_pct.
#
# Requirements: pip install pytest
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Run pytest and capture output
OUTPUT=$(python -m pytest test_solution.py -v --tb=short 2>&1) || true

echo "$OUTPUT"
echo ""

# Parse pytest results: "X passed, Y failed" or "X passed"
PASSED=$(echo "$OUTPUT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo "0")
FAILED=$(echo "$OUTPUT" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo "0")
ERRORS=$(echo "$OUTPUT" | grep -oE '[0-9]+ error' | grep -oE '[0-9]+' || echo "0")

TOTAL=$((PASSED + FAILED + ERRORS))

if [ "$TOTAL" -eq 0 ]; then
    echo "pass_pct:0.0"
else
    PASS_PCT=$(python3 -c "print(f'{($PASSED / $TOTAL) * 100:.1f}')")
    echo "pass_pct:${PASS_PCT}"
fi
