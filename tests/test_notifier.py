"""Unit tests for email rendering and the send guard (no real SMTP)."""

import pytest

from share_alerts.config import EmailConfig
from share_alerts.notifier import (
    NotifyError,
    render_body,
    render_subject,
    send_email,
)
from share_alerts.rules import Action, Alert


def alert(action=Action.SELL, ticker="AAPL", rule="sell_above", price=240.0):
    return Alert(
        ticker=ticker, rule=rule, action=action, price=price,
        currency="USD", message=f"{ticker} did the thing.",
    )


def test_subject_single_alert_mentions_ticker_and_action():
    subj = render_subject([alert()])
    assert "AAPL" in subj
    assert "SELL" in subj


def test_subject_multiple_alerts_counts_them():
    subj = render_subject([alert(), alert(action=Action.BUY, ticker="TSLA")])
    assert "2 signals" in subj


def test_body_includes_each_message_and_disclaimer():
    body = render_body([alert(), alert(ticker="TSLA")])
    assert "AAPL did the thing." in body
    assert "TSLA did the thing." in body
    assert "not financial advice" in body


def test_send_email_requires_credentials(monkeypatch):
    monkeypatch.delenv("GMAIL_USER", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    with pytest.raises(NotifyError, match="GMAIL_USER"):
        send_email(EmailConfig(enabled=True, to="me@example.com"), [alert()])


def test_send_email_requires_recipient(monkeypatch):
    monkeypatch.setenv("GMAIL_USER", "me@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "secret")
    with pytest.raises(NotifyError, match="recipient"):
        send_email(EmailConfig(enabled=True, to=None), [alert()])
