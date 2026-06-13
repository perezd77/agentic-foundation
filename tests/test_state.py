"""Unit tests for the de-duplication state store."""

from share_alerts.state import AlertState


def test_first_fire_is_allowed(tmp_path):
    s = AlertState(tmp_path / "state.json")
    assert s.should_fire("AAPL:sell_above", cooldown_hours=12, now=1000.0)


def test_within_cooldown_is_suppressed(tmp_path):
    s = AlertState(tmp_path / "state.json")
    s.mark_fired("AAPL:sell_above", now=1000.0)
    # 1 hour later, cooldown is 12h -> suppressed.
    assert not s.should_fire("AAPL:sell_above", cooldown_hours=12, now=1000.0 + 3600)


def test_after_cooldown_is_allowed_again(tmp_path):
    s = AlertState(tmp_path / "state.json")
    s.mark_fired("AAPL:sell_above", now=1000.0)
    later = 1000.0 + 13 * 3600
    assert s.should_fire("AAPL:sell_above", cooldown_hours=12, now=later)


def test_state_persists_across_instances(tmp_path):
    path = tmp_path / "state.json"
    s1 = AlertState(path)
    s1.mark_fired("AAPL:sell_above", now=1000.0)
    s1.save()

    s2 = AlertState(path)
    assert not s2.should_fire("AAPL:sell_above", cooldown_hours=12, now=1000.0 + 60)


def test_corrupt_state_file_is_ignored(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not valid json")
    s = AlertState(path)  # should not raise
    assert s.should_fire("AAPL:sell_above", cooldown_hours=12, now=1000.0)


def test_different_keys_are_independent(tmp_path):
    s = AlertState(tmp_path / "state.json")
    s.mark_fired("AAPL:sell_above", now=1000.0)
    assert s.should_fire("TSLA:buy_below", cooldown_hours=12, now=1000.0 + 60)
