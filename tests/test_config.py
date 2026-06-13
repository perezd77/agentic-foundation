"""Unit tests for configuration loading and validation."""

import pytest

from share_alerts.config import ConfigError, load_config


def write(tmp_path, text):
    p = tmp_path / "config.yaml"
    p.write_text(text)
    return p


def test_loads_minimal_valid_config(tmp_path):
    cfg = load_config(write(tmp_path, """
notifications:
  email:
    enabled: true
    to: me@example.com
holdings:
  - ticker: aapl
    rules:
      sell_above: 240
"""))
    assert cfg.email.enabled is True
    assert cfg.email.to == "me@example.com"
    assert len(cfg.holdings) == 1
    # Tickers are normalised to upper case.
    assert cfg.holdings[0].ticker == "AAPL"
    assert cfg.holdings[0].rules["sell_above"] == 240.0


def test_defaults_applied(tmp_path):
    cfg = load_config(write(tmp_path, """
holdings:
  - ticker: AAPL
    rules: {sell_above: 100}
"""))
    assert cfg.currency == "USD"
    assert cfg.cooldown_hours == 12.0
    assert cfg.email.enabled is False


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_no_holdings_raises(tmp_path):
    with pytest.raises(ConfigError, match="no `holdings`"):
        load_config(write(tmp_path, "notifications: {email: {enabled: false}}"))


def test_holding_without_rules_raises(tmp_path):
    with pytest.raises(ConfigError, match="no rules"):
        load_config(write(tmp_path, """
holdings:
  - ticker: AAPL
"""))


def test_unknown_rule_raises(tmp_path):
    with pytest.raises(ConfigError, match="unknown rule"):
        load_config(write(tmp_path, """
holdings:
  - ticker: AAPL
    rules: {sel_above: 100}
"""))


def test_duplicate_ticker_raises(tmp_path):
    with pytest.raises(ConfigError, match="duplicate ticker"):
        load_config(write(tmp_path, """
holdings:
  - ticker: AAPL
    rules: {sell_above: 100}
  - ticker: aapl
    rules: {buy_below: 80}
"""))


def test_pct_rule_without_avg_cost_raises(tmp_path):
    with pytest.raises(ConfigError, match="require `avg_cost`"):
        load_config(write(tmp_path, """
holdings:
  - ticker: AAPL
    rules: {gain_pct: 25}
"""))


def test_email_enabled_without_recipient_raises(tmp_path):
    with pytest.raises(ConfigError, match="no `to:`"):
        load_config(write(tmp_path, """
notifications:
  email:
    enabled: true
holdings:
  - ticker: AAPL
    rules: {sell_above: 100}
"""))


def test_non_numeric_rule_value_raises(tmp_path):
    with pytest.raises(ConfigError, match="expected a number"):
        load_config(write(tmp_path, """
holdings:
  - ticker: AAPL
    rules: {sell_above: "high"}
"""))
