# Copy Optimization

## Goal
Maximize the conversion_quality score of landing page copy, judged by an LLM evaluator on clarity, persuasiveness, specificity, and emotional appeal (0-100 scale).

## Setup
1. Read `landing_copy.txt` to understand the current marketing copy.
2. Read `eval.py` to understand the judging criteria and rubric.
3. Run the eval once to get the baseline score.

## Constraints
- DO NOT MODIFY: `eval.py`
- Only modify `landing_copy.txt`
- The copy must remain under 3000 characters
- The copy must be for a project management SaaS product (do not change the product category)
- Do not include fabricated statistics or fake testimonials

## Experiment Loop
1. Analyze the judge feedback from the eval output, then edit `landing_copy.txt` with improved copy
2. Run: `python eval.py`
3. Read metric: parse `conversion_quality:<value>` from stdout
4. If improved: keep the change to `landing_copy.txt`
5. If not improved: revert `landing_copy.txt` to the previous version
6. LOOP FOREVER

## Metric
metric_name: conversion_quality
higher_is_better: true
