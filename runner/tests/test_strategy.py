"""Tests for explore/exploit strategy state machine."""


def test_starts_in_explore_mode():
    from runner.strategy import LoopStrategy
    s = LoopStrategy()
    assert s.get_mode() == "explore"


def test_switches_to_exploit_after_improvements():
    from runner.strategy import LoopStrategy
    s = LoopStrategy()
    for i in range(8):
        s.record(kept=False)
    s.record(kept=True)
    s.record(kept=True)
    assert s.get_mode() == "exploit"


def test_switches_back_to_explore_after_stagnation():
    from runner.strategy import LoopStrategy
    s = LoopStrategy()
    s.record(kept=True)
    s.record(kept=True)
    assert s.get_mode() == "exploit"
    for _ in range(8):
        s.record(kept=False)
    assert s.get_mode() == "explore"


def test_stays_in_explore_when_no_improvements():
    from runner.strategy import LoopStrategy
    s = LoopStrategy()
    for _ in range(20):
        s.record(kept=False)
    assert s.get_mode() == "explore"


def test_get_temperature_varies_by_mode():
    from runner.strategy import LoopStrategy
    s = LoopStrategy()
    assert s.get_temperature() == 1.0
    s.record(kept=True)
    s.record(kept=True)
    assert s.get_temperature() == 0.3


def test_get_prompt_addition_differs_by_mode():
    from runner.strategy import LoopStrategy
    s = LoopStrategy()
    explore_prompt = s.get_prompt_addition()
    assert "EXPLORATION" in explore_prompt
    s.record(kept=True)
    s.record(kept=True)
    exploit_prompt = s.get_prompt_addition()
    assert "REFINEMENT" in exploit_prompt


def test_override_explore_only():
    from runner.strategy import LoopStrategy
    s = LoopStrategy(override="explore_only")
    s.record(kept=True)
    s.record(kept=True)
    assert s.get_mode() == "explore"


def test_override_exploit_only():
    from runner.strategy import LoopStrategy
    s = LoopStrategy(override="exploit_only")
    assert s.get_mode() == "exploit"
