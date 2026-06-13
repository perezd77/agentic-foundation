"""Load and validate the YAML configuration into typed objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when the configuration file is missing or invalid."""


# Rule names the engine understands. Anything else in a holding's `rules`
# block is rejected early so typos don't silently disable an alert.
KNOWN_RULES = {
    "sell_above",
    "buy_below",
    "stop_loss",
    "gain_pct",
    "loss_pct",
    "day_move_pct",
}


@dataclass
class Holding:
    ticker: str
    name: str | None = None
    shares: float | None = None
    avg_cost: float | None = None
    rules: dict[str, float] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.name} ({self.ticker})" if self.name else self.ticker


@dataclass
class EmailConfig:
    enabled: bool = False
    to: str | None = None
    from_name: str | None = None


@dataclass
class Config:
    email: EmailConfig
    holdings: list[Holding]
    currency: str = "USD"
    cooldown_hours: float = 12.0


def _as_float(value: Any, where: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{where}: expected a number, got {value!r}") from exc


def load_config(path: str | Path) -> Config:
    """Parse `path` and return a validated :class:`Config`."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(
            f"Config file not found: {path}\n"
            "Copy config.example.yaml to config.yaml and edit it."
        )

    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Could not parse YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: top level must be a mapping/object.")

    defaults = raw.get("defaults") or {}
    currency = str(defaults.get("currency", "USD"))
    cooldown_hours = _as_float(
        defaults.get("cooldown_hours", 12), "defaults.cooldown_hours"
    )

    email_raw = (raw.get("notifications") or {}).get("email") or {}
    email = EmailConfig(
        enabled=bool(email_raw.get("enabled", False)),
        to=email_raw.get("to"),
        from_name=email_raw.get("from_name"),
    )
    if email.enabled and not email.to:
        raise ConfigError("notifications.email.enabled is true but no `to:` set.")

    holdings_raw = raw.get("holdings")
    if not holdings_raw:
        raise ConfigError(f"{path}: no `holdings` configured — nothing to watch.")
    if not isinstance(holdings_raw, list):
        raise ConfigError(f"{path}: `holdings` must be a list.")

    holdings: list[Holding] = []
    seen: set[str] = set()
    for i, item in enumerate(holdings_raw):
        where = f"holdings[{i}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{where}: must be a mapping.")
        ticker = item.get("ticker")
        if not ticker:
            raise ConfigError(f"{where}: missing required `ticker`.")
        ticker = str(ticker).strip().upper()
        if ticker in seen:
            raise ConfigError(f"{where}: duplicate ticker {ticker!r}.")
        seen.add(ticker)

        rules_raw = item.get("rules") or {}
        if not isinstance(rules_raw, dict):
            raise ConfigError(f"{where}.rules: must be a mapping.")
        unknown = set(rules_raw) - KNOWN_RULES
        if unknown:
            raise ConfigError(
                f"{where}.rules: unknown rule(s) {sorted(unknown)}. "
                f"Valid rules: {sorted(KNOWN_RULES)}"
            )
        rules = {k: _as_float(v, f"{where}.rules.{k}") for k, v in rules_raw.items()}
        if not rules:
            raise ConfigError(f"{where}: ticker {ticker} has no rules — add at least one.")

        avg_cost = item.get("avg_cost")
        if avg_cost is not None:
            avg_cost = _as_float(avg_cost, f"{where}.avg_cost")
        shares = item.get("shares")
        if shares is not None:
            shares = _as_float(shares, f"{where}.shares")

        # Percentage rules need a cost basis to compare against.
        if ("gain_pct" in rules or "loss_pct" in rules) and avg_cost is None:
            raise ConfigError(
                f"{where}: gain_pct/loss_pct require `avg_cost` to be set."
            )

        holdings.append(
            Holding(
                ticker=ticker,
                name=item.get("name"),
                shares=shares,
                avg_cost=avg_cost,
                rules=rules,
            )
        )

    return Config(
        email=email,
        holdings=holdings,
        currency=currency,
        cooldown_hours=cooldown_hours,
    )
