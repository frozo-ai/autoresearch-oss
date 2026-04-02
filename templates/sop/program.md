# SOP Optimization

## Goal
Maximize the sop_quality score of a Standard Operating Procedure document, judged by an LLM evaluator on completeness, clarity, actionability, and safety coverage (0-100 scale).

## Setup
1. Read `sop.md` to understand the current procedure document.
2. Read `eval.py` to understand the judging criteria and rubric.
3. Run the eval once to get the baseline score.

## Constraints
- DO NOT MODIFY: `eval.py`
- Only modify `sop.md`
- The SOP must remain under 5000 characters
- The SOP must remain about the same topic (incident response procedure)
- Do not fabricate company-specific details; keep the SOP generic and reusable

## Experiment Loop
1. Analyze the judge feedback from the eval output, then edit `sop.md` with improvements
2. Run: `python eval.py`
3. Read metric: parse `sop_quality:<value>` from stdout
4. If improved: keep the change to `sop.md`
5. If not improved: revert `sop.md` to the previous version
6. LOOP FOREVER

## Metric
metric_name: sop_quality
higher_is_better: true
