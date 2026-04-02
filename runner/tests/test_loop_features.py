"""Tests for loop engine features: cancellation, early stopping, eval caching."""

from unittest.mock import MagicMock, patch


def test_check_cancel_flag_returns_false_when_no_flag():
    """Cancel check returns False when no Redis cancel key exists."""
    from runner.loop import _check_cancel_flag
    result = _check_cancel_flag("test-run-id")
    assert result is False


def test_check_cancel_flag_returns_true_when_flag_set():
    """Cancel check returns True when Redis cancel key is set."""
    from runner.loop import _check_cancel_flag
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"1"
    with patch("runner.loop._get_redis_client", return_value=mock_redis):
        result = _check_cancel_flag("test-run-id")
    assert result is True
    mock_redis.get.assert_called_once_with("run:test-run-id:cancel")


def test_stagnation_detected_after_window():
    """Stagnation is detected when last N experiments all reverted."""
    from runner.loop import _check_stagnation
    kept_history = [False] * 15
    assert _check_stagnation(kept_history, window=15) is True


def test_stagnation_not_detected_with_recent_improvement():
    """Stagnation is NOT detected when a recent experiment was kept."""
    from runner.loop import _check_stagnation
    kept_history = [False] * 14 + [True]
    assert _check_stagnation(kept_history, window=15) is False


def test_stagnation_not_detected_when_history_too_short():
    """Stagnation is NOT detected when fewer experiments than window."""
    from runner.loop import _check_stagnation
    kept_history = [False] * 10
    assert _check_stagnation(kept_history, window=15) is False


def test_eval_cache_hit():
    """Eval cache returns cached score for identical content."""
    from runner.loop import EvalCache
    cache = EvalCache()
    cache.record("hello world", 85.0, False, 3)
    hit = cache.lookup("hello world")
    assert hit is not None
    assert hit == (85.0, False, 3)


def test_eval_cache_miss():
    """Eval cache returns None for unseen content."""
    from runner.loop import EvalCache
    cache = EvalCache()
    hit = cache.lookup("never seen this")
    assert hit is None


def test_eval_cache_different_content():
    """Eval cache distinguishes different content."""
    from runner.loop import EvalCache
    cache = EvalCache()
    cache.record("version A", 85.0, False, 1)
    cache.record("version B", 72.0, False, 2)
    assert cache.lookup("version A") == (85.0, False, 1)
    assert cache.lookup("version B") == (72.0, False, 2)
