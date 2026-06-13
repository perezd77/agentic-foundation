"""End-to-end CLI tests with price fetching and email stubbed out."""

import share_alerts.__main__ as cli
from share_alerts.prices import PriceError, Quote


CONFIG = """
notifications:
  email:
    enabled: true
    to: me@example.com
defaults:
  cooldown_hours: 12
holdings:
  - ticker: AAPL
    avg_cost: 100
    rules:
      sell_above: 200
      buy_below: 90
"""


def write_config(tmp_path, text=CONFIG):
    p = tmp_path / "config.yaml"
    p.write_text(text)
    return p


def test_dry_run_triggers_alert_but_sends_nothing(tmp_path, monkeypatch, capsys):
    cfg = write_config(tmp_path)
    state = tmp_path / "state.json"
    monkeypatch.setattr(cli, "get_quote",
                        lambda t: Quote(t, price=250.0, previous_close=240.0, currency="USD"))

    sent = []
    monkeypatch.setattr(cli, "send_email", lambda *a, **k: sent.append(a))

    rc = cli.run(["--config", str(cfg), "--state", str(state), "--dry-run"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "SELL AAPL" in out
    assert sent == []                 # dry-run sends nothing
    assert not state.exists()         # and records no state


def test_alert_sends_email_and_records_state(tmp_path, monkeypatch):
    cfg = write_config(tmp_path)
    state = tmp_path / "state.json"
    monkeypatch.setattr(cli, "get_quote",
                        lambda t: Quote(t, price=250.0, previous_close=240.0, currency="USD"))

    sent = []
    monkeypatch.setattr(cli, "send_email", lambda c, alerts: sent.append(alerts))

    rc = cli.run(["--config", str(cfg), "--state", str(state)])
    assert rc == 0
    assert len(sent) == 1
    assert sent[0][0].ticker == "AAPL"
    assert state.exists()


def test_cooldown_suppresses_second_run(tmp_path, monkeypatch):
    cfg = write_config(tmp_path)
    state = tmp_path / "state.json"
    monkeypatch.setattr(cli, "get_quote",
                        lambda t: Quote(t, price=250.0, previous_close=240.0, currency="USD"))

    sent = []
    monkeypatch.setattr(cli, "send_email", lambda c, alerts: sent.append(alerts))

    assert cli.run(["--config", str(cfg), "--state", str(state)]) == 0
    # Second run immediately after: still in cooldown, nothing new.
    rc = cli.run(["--config", str(cfg), "--state", str(state)])
    assert rc == 0
    assert len(sent) == 1             # not sent again


def test_ignore_cooldown_resends(tmp_path, monkeypatch):
    cfg = write_config(tmp_path)
    state = tmp_path / "state.json"
    monkeypatch.setattr(cli, "get_quote",
                        lambda t: Quote(t, price=250.0, previous_close=240.0, currency="USD"))
    sent = []
    monkeypatch.setattr(cli, "send_email", lambda c, alerts: sent.append(alerts))

    cli.run(["--config", str(cfg), "--state", str(state)])
    cli.run(["--config", str(cfg), "--state", str(state), "--ignore-cooldown"])
    assert len(sent) == 2


def test_no_alerts_returns_zero(tmp_path, monkeypatch, capsys):
    cfg = write_config(tmp_path)
    state = tmp_path / "state.json"
    # Price sits between buy_below (90) and sell_above (200): nothing fires.
    monkeypatch.setattr(cli, "get_quote",
                        lambda t: Quote(t, price=120.0, previous_close=119.0, currency="USD"))
    rc = cli.run(["--config", str(cfg), "--state", str(state)])
    assert rc == 0
    assert "No new alerts." in capsys.readouterr().out


def test_fetch_error_is_isolated_and_reported(tmp_path, monkeypatch):
    cfg = write_config(tmp_path)
    state = tmp_path / "state.json"

    def boom(ticker):
        raise PriceError("network down")

    monkeypatch.setattr(cli, "get_quote", boom)
    # No alerts possible + a fetch error -> exit code 1.
    rc = cli.run(["--config", str(cfg), "--state", str(state)])
    assert rc == 1


def test_bad_config_returns_exit_code_2(tmp_path, capsys):
    bad = tmp_path / "config.yaml"
    bad.write_text("holdings: []")
    rc = cli.run(["--config", str(bad)])
    assert rc == 2
    assert "Config error" in capsys.readouterr().err
