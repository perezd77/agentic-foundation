"""Unit tests for the rule-evaluation engine (no network)."""

from share_alerts.config import Holding
from share_alerts.prices import Quote
from share_alerts.rules import Action, evaluate


def make_quote(price, prev=None, currency="USD"):
    return Quote(ticker="TEST", price=price, previous_close=prev, currency=currency)


def fired_rules(alerts):
    return {a.rule for a in alerts}


def test_sell_above_fires_at_and_over_target():
    h = Holding(ticker="TEST", rules={"sell_above": 100.0})
    assert "sell_above" in fired_rules(evaluate(h, make_quote(100.0)))   # exactly at
    assert "sell_above" in fired_rules(evaluate(h, make_quote(120.0)))   # above
    assert evaluate(h, make_quote(99.99)) == []                          # below


def test_sell_above_action_is_sell():
    h = Holding(ticker="TEST", rules={"sell_above": 100.0})
    alerts = evaluate(h, make_quote(105.0))
    assert len(alerts) == 1
    assert alerts[0].action is Action.SELL


def test_stop_loss_fires_at_and_under_floor():
    h = Holding(ticker="TEST", rules={"stop_loss": 50.0})
    assert "stop_loss" in fired_rules(evaluate(h, make_quote(50.0)))
    assert "stop_loss" in fired_rules(evaluate(h, make_quote(40.0)))
    assert evaluate(h, make_quote(50.01)) == []


def test_buy_below_fires_and_is_buy_action():
    h = Holding(ticker="TEST", rules={"buy_below": 80.0})
    alerts = evaluate(h, make_quote(75.0))
    assert fired_rules(alerts) == {"buy_below"}
    assert alerts[0].action is Action.BUY


def test_gain_pct_uses_avg_cost():
    h = Holding(ticker="TEST", avg_cost=100.0, rules={"gain_pct": 25.0})
    assert "gain_pct" in fired_rules(evaluate(h, make_quote(125.0)))  # +25%
    assert "gain_pct" in fired_rules(evaluate(h, make_quote(150.0)))  # +50%
    assert evaluate(h, make_quote(120.0)) == []                       # only +20%


def test_loss_pct_uses_avg_cost():
    h = Holding(ticker="TEST", avg_cost=100.0, rules={"loss_pct": 15.0})
    assert "loss_pct" in fired_rules(evaluate(h, make_quote(85.0)))   # -15%
    assert "loss_pct" in fired_rules(evaluate(h, make_quote(70.0)))   # -30%
    assert evaluate(h, make_quote(90.0)) == []                        # only -10%


def test_day_move_pct_triggers_on_up_and_down_swings():
    h = Holding(ticker="TEST", rules={"day_move_pct": 6.0})
    up = evaluate(h, make_quote(110.0, prev=100.0))     # +10%
    down = evaluate(h, make_quote(90.0, prev=100.0))    # -10%
    assert fired_rules(up) == {"day_move_pct"}
    assert fired_rules(down) == {"day_move_pct"}
    assert up[0].action is Action.INFO
    # Small move stays quiet.
    assert evaluate(h, make_quote(103.0, prev=100.0)) == []


def test_day_move_pct_needs_previous_close():
    h = Holding(ticker="TEST", rules={"day_move_pct": 6.0})
    assert evaluate(h, make_quote(110.0, prev=None)) == []


def test_multiple_rules_can_fire_together():
    # Down big vs cost AND below stop-loss AND below buy level.
    h = Holding(
        ticker="TEST",
        avg_cost=100.0,
        rules={"stop_loss": 80.0, "buy_below": 85.0, "loss_pct": 15.0},
    )
    alerts = evaluate(h, make_quote(70.0))
    assert fired_rules(alerts) == {"stop_loss", "buy_below", "loss_pct"}


def test_no_rules_match_returns_empty():
    h = Holding(ticker="TEST", rules={"sell_above": 200.0, "stop_loss": 50.0})
    assert evaluate(h, make_quote(100.0)) == []


def test_alert_key_is_ticker_and_rule():
    h = Holding(ticker="AAPL", rules={"sell_above": 100.0})
    alert = evaluate(h, make_quote(105.0))[0]
    assert alert.key == "AAPL:sell_above"


def test_currency_fallback_used_when_quote_has_none():
    h = Holding(ticker="TEST", rules={"sell_above": 100.0})
    q = make_quote(105.0, currency=None)
    alert = evaluate(h, q, currency_fallback="EUR")[0]
    assert "EUR" in alert.message
