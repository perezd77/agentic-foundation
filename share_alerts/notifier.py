"""Render alerts and deliver them by email (Gmail SMTP)."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage

from .config import EmailConfig
from .rules import Action, Alert

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


class NotifyError(Exception):
    """Raised when an email could not be sent."""


_ACTION_ICON = {Action.SELL: "🔴 SELL", Action.BUY: "🟢 BUY", Action.INFO: "🔵 INFO"}


def render_subject(alerts: list[Alert]) -> str:
    actions = {a.action for a in alerts}
    if len(alerts) == 1:
        a = alerts[0]
        return f"[Share Alert] {_ACTION_ICON[a.action]} {a.ticker} @ {a.price:,.2f}"
    tag = "/".join(sorted(act.value for act in actions))
    return f"[Share Alert] {len(alerts)} signals ({tag})"


def render_body(alerts: list[Alert]) -> str:
    lines = ["You have new share alerts:\n"]
    for a in alerts:
        lines.append(f"{_ACTION_ICON[a.action]}  {a.message}")
    lines.append(
        "\n—\nThis is an automated price alert, not financial advice. "
        "Verify the price in Revolut before trading."
    )
    return "\n".join(lines)


def send_email(cfg: EmailConfig, alerts: list[Alert]) -> None:
    """Send `alerts` as a single email using Gmail SMTP.

    Credentials come from the environment: GMAIL_USER and GMAIL_APP_PASSWORD.
    """
    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not password:
        raise NotifyError(
            "Email enabled but GMAIL_USER / GMAIL_APP_PASSWORD are not set in "
            "the environment. See the README for how to create an app password."
        )
    if not cfg.to:
        raise NotifyError("No recipient configured (notifications.email.to).")

    msg = EmailMessage()
    from_name = cfg.from_name or "Share Alerts"
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = cfg.to
    msg["Subject"] = render_subject(alerts)
    msg.set_content(render_body(alerts))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls(context=context)
            server.login(user, password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise NotifyError(f"Failed to send email: {exc}") from exc
