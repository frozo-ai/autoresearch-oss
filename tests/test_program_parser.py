"""Tests for program.md parser and validator."""

import pytest

from runner.program_parser import ParseError, parse, validate

VALID_PROGRAM = """# Test Experiment

## Goal
Optimize prompt accuracy on classification task.

## Setup
Install deps.

## Constraints
- DO NOT MODIFY: eval.py
- Keep it under 500 words

## Experiment Loop
1. Read the current prompt
2. Run: python eval.py
3. Read metric: accuracy_pct from stdout
4. If improved: keep
5. If not improved: revert
6. LOOP FOREVER

## Metric
metric_name: accuracy_pct
higher_is_better: true
"""


def test_parse_valid_program():
    config = parse(VALID_PROGRAM)
    assert config.title == "Test Experiment"
    assert config.goal == "Optimize prompt accuracy on classification task."
    assert config.metric_name == "accuracy_pct"
    assert config.higher_is_better is True
    assert len(config.constraints) == 2
    assert "DO NOT MODIFY: eval.py" in config.constraints[0]


def test_parse_extracts_eval_command():
    config = parse(VALID_PROGRAM)
    assert config.eval_command == "python eval.py"


def test_parse_missing_sections():
    incomplete = """# Title

## Goal
Some goal.
"""
    with pytest.raises(ParseError) as exc_info:
        parse(incomplete)
    assert "Setup" in str(exc_info.value)
    assert "Constraints" in str(exc_info.value)


def test_parse_missing_title():
    no_title = """## Goal
Some goal.

## Setup
Nothing.

## Constraints
- None

## Experiment Loop
1. Do stuff

## Metric
metric_name: score
higher_is_better: true
"""
    with pytest.raises(ParseError):
        parse(no_title)


def test_parse_missing_metric_name():
    missing_metric = VALID_PROGRAM.replace("metric_name: accuracy_pct", "")
    with pytest.raises(ParseError) as exc_info:
        parse(missing_metric)
    assert "metric_name" in str(exc_info.value)


def test_parse_higher_is_better_false():
    program = VALID_PROGRAM.replace("higher_is_better: true", "higher_is_better: false")
    config = parse(program)
    assert config.higher_is_better is False


def test_validate_returns_empty_for_valid():
    errors = validate(VALID_PROGRAM)
    assert errors == []


def test_validate_returns_errors_for_invalid():
    errors = validate("# Title\n\nSome content without sections.")
    assert len(errors) > 0
