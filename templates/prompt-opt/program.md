# Prompt Optimization

## Goal
Maximize the accuracy of an LLM system prompt against a suite of test cases, measured as accuracy_pct (percentage of correct responses).

## Setup
1. Read `system_prompt.txt` to understand the current prompt.
2. Read `test_cases.json` to understand the expected input/output pairs.
3. Run the eval once to get the baseline score.

## Constraints
- DO NOT MODIFY: `eval.py`, `test_cases.json`
- Only modify `system_prompt.txt`
- The system prompt must remain under 2000 characters
- Do not hard-code answers to specific test cases; the prompt must generalize

## Experiment Loop
1. Analyze current failures by reviewing eval output, then edit `system_prompt.txt` with an improved prompt
2. Run: `python eval.py`
3. Read metric: parse `accuracy_pct:<value>` from stdout
4. If improved: keep the change to `system_prompt.txt`
5. If not improved: revert `system_prompt.txt` to the previous version
6. LOOP FOREVER

## Metric
metric_name: accuracy_pct
higher_is_better: true
