# Test Pass Rate Optimization

## Goal
Maximize the pass_pct of a Python solution against a test suite, measured as percentage of tests passing (0-100 scale).

## Setup
1. Read `solution.py` to understand the current implementation and its bugs.
2. Read `test_solution.py` to understand what the tests expect.
3. Run the eval once to get the baseline pass rate.

## Constraints
- DO NOT MODIFY: `eval.sh`, `test_solution.py`
- Only modify `solution.py`
- Do not delete or rename existing functions; the test suite depends on their signatures
- Do not use any external packages beyond the Python standard library

## Experiment Loop
1. Analyze test failures from the eval output, then fix bugs or improve logic in `solution.py`
2. Run: `bash eval.sh`
3. Read metric: parse `pass_pct:<value>` from stdout
4. If improved: keep the change to `solution.py`
5. If not improved: revert `solution.py` to the previous version
6. LOOP FOREVER

## Metric
metric_name: pass_pct
higher_is_better: true
