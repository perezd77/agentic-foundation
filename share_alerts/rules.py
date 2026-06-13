"""Evaluate a holding's rules against a live quote and produce alerts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .config import Holding
from .prices import Quote


class Action(str, Enum):
    SELL = "SELL"
    BUY = "BUY"
    INFO = "INFO"


@dataclass
class Alert:
    ticker: str
    rule: str          # the rule key that fired, e.g. "sell_above"
    action: Action
    price: float
    currency: str | None
    message: str

    @property
    def key(self) -> str:
        """Stable identity for de-duplication (ticker + rule)."""
        return f"{self.ticker}:{self.rule}"


def _fmt(value: float, currency: str | None) -> str:
    cur = f" {currency}" if currency else ""
    return f"{value:,.2f}{cur}"


def evaluate(holding: Holding, quote: Quote, currency_fallback: str = "") -> list[Alert]:
    """Return every alert triggered by `quote` for `holding`."""
    rules = holding.rules
    price = quote.price
    currency = quote.currency or currency_fallback or None
    alerts: list[Alert] = []

    def add(rule: str, action: Action, message: str) -> None:
        alerts.append(
            Alert(holding.ticker, rule, action, price, currency, message)
        )

    # --- absolute price targets ------------------------------------------
    if "sell_above" in rules and price >= rules["sell_above"]:
        add(
            "sell_above",
            Action.SELL,
            f"{holding.label} hit {_fmt(price, currency)}, at/above your "
            f"take-profit target of {_fmt(rules['sell_above'], currency)}. "
            f"Consider SELLING.",
        )

    if "stop_loss" in rules and price <= rules["stop_loss"]:
        add(
            "stop_loss",
            Action.SELL,
            f"{holding.label} fell to {_fmt(price, currency)}, at/below your "
            f"stop-loss of {_fmt(rules['stop_loss'], currency)}. "
            f"Consider SELLING to limit losses.",
        )

    if "buy_below" in rules and price <= rules["buy_below"]:
        add(
            "buy_below",
            Action.BUY,
            f"{holding.label} dropped to {_fmt(price, currency)}, at/below your "
            f"buy-the-dip level of {_fmt(rules['buy_below'], currency)}. "
            f"Consider BUYING more.",
        )

    # --- percentage vs. average cost -------------------------------------
    if holding.avg_cost:
        change_pct = (price - holding.avg_cost) / holding.avg_cost * 100.0
        if "gain_pct" in rules and change_pct >= rules["gain_pct"]:
            add(
                "gain_pct",
                Action.SELL,
                f"{holding.label} is up {change_pct:+.1f}% vs your average cost "
                f"of {_fmt(holding.avg_cost, currency)} "
                f"(now {_fmt(price, currency)}). Consider taking profit.",
            )
        if "loss_pct" in rules and change_pct <= -rules["loss_pct"]:
            add(
                "loss_pct",
                Action.SELL,
                f"{holding.label} is down {change_pct:+.1f}% vs your average cost "
                f"of {_fmt(holding.avg_cost, currency)} "
                f"(now {_fmt(price, currency)}). Consider cutting the loss.",
            )

    # --- intraday move heads-up ------------------------------------------
    if "day_move_pct" in rules:
        day_move = quote.day_change_pct
        if day_move is not None and abs(day_move) >= rules["day_move_pct"]:
            add(
                "day_move_pct",
                Action.INFO,
                f"{holding.label} moved {day_move:+.1f}% today "
                f"(now {_fmt(price, currency)}). Worth a look.",
            )

    return alerts
