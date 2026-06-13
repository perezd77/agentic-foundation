"""Command-line entry point: `python -m share_alerts`."""

from __future__ import annotations

import argparse
import sys

from .config import ConfigError, load_config
from .notifier import NotifyError, send_email
from .prices import PriceError, get_quote
from .rules import Alert, evaluate
from .state import AlertState


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="share_alerts",
        description="Watch your shares and email you when to buy or sell.",
    )
    p.add_argument("--config", default="config.yaml", help="Path to config file.")
    p.add_argument("--state", default=".alert_state.json",
                   help="Path to de-duplication state file.")
    p.add_argument("--dry-run", action="store_true",
                   help="Evaluate and print alerts but send no email.")
    p.add_argument("--ignore-cooldown", action="store_true",
                   help="Re-fire alerts even if recently sent.")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="Print each ticker's price as it is checked.")
    return p.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2

    state = AlertState(args.state)
    triggered: list[Alert] = []
    had_fetch_error = False

    for holding in cfg.holdings:
        try:
            quote = get_quote(holding.ticker)
        except PriceError as exc:
            had_fetch_error = True
            print(f"  ! {holding.ticker}: {exc}", file=sys.stderr)
            continue

        if args.verbose:
            day = quote.day_change_pct
            day_s = f"  ({day:+.1f}% today)" if day is not None else ""
            cur = f" {quote.currency}" if quote.currency else ""
            print(f"  {holding.ticker}: {quote.price:,.2f}{cur}{day_s}")

        for alert in evaluate(holding, quote, cfg.currency):
            if args.ignore_cooldown or state.should_fire(alert.key, cfg.cooldown_hours):
                triggered.append(alert)
            elif args.verbose:
                print(f"    (skipped, in cooldown: {alert.key})")

    if not triggered:
        print("No new alerts.")
        return 1 if had_fetch_error else 0

    print(f"{len(triggered)} alert(s) triggered:")
    for a in triggered:
        print(f"  - {a.action.value} {a.ticker}: {a.message}")

    if args.dry_run:
        print("\n(dry run — no email sent)")
        return 0

    if cfg.email.enabled:
        try:
            send_email(cfg.email, triggered)
            print(f"\nEmail sent to {cfg.email.to}.")
        except NotifyError as exc:
            print(f"Email error: {exc}", file=sys.stderr)
            return 3
    else:
        print("\n(email notifications disabled in config — nothing sent)")

    # Only record as fired once successfully delivered (or intentionally not).
    for a in triggered:
        state.mark_fired(a.key)
    state.save()
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
