"""Fetch current share prices from free, key-less public sources.

Primary source is Yahoo Finance's chart endpoint; if that fails for a symbol
we fall back to Stooq's CSV quote. Neither requires an API key. Network and
parsing errors are surfaced as :class:`PriceError` per ticker so one bad
symbol never aborts the whole run.
"""

from __future__ import annotations

import csv
import io
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

USER_AGENT = "Mozilla/5.0 (compatible; share-alerts/0.1; +https://github.com/)"
TIMEOUT = 15


class PriceError(Exception):
    """Raised when a price could not be obtained for a ticker."""


@dataclass
class Quote:
    ticker: str
    price: float
    previous_close: float | None
    currency: str | None

    @property
    def day_change_pct(self) -> float | None:
        if self.previous_close in (None, 0):
            return None
        return (self.price - self.previous_close) / self.previous_close * 100.0


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310
        return resp.read()


def _from_yahoo(ticker: str) -> Quote:
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(ticker)}?interval=1d&range=1d"
    )
    data = json.loads(_http_get(url))
    result = (data.get("chart") or {}).get("result")
    if not result:
        err = (data.get("chart") or {}).get("error")
        raise PriceError(f"Yahoo returned no data for {ticker}: {err}")
    meta = result[0].get("meta") or {}
    price = meta.get("regularMarketPrice")
    if price is None:
        raise PriceError(f"Yahoo response for {ticker} had no price")
    return Quote(
        ticker=ticker,
        price=float(price),
        previous_close=(
            float(meta["previousClose"]) if meta.get("previousClose") is not None
            else (float(meta["chartPreviousClose"])
                  if meta.get("chartPreviousClose") is not None else None)
        ),
        currency=meta.get("currency"),
    )


def _from_stooq(ticker: str) -> Quote:
    # Stooq uses lowercase symbols and a ".us" suffix for US listings.
    symbol = ticker.lower()
    if "." not in symbol:
        symbol += ".us"
    url = f"https://stooq.com/q/l/?s={urllib.parse.quote(symbol)}&f=sd2t2ohlcv&h&e=csv"
    text = _http_get(url).decode("utf-8", "replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise PriceError(f"Stooq returned no rows for {ticker}")
    row = rows[0]
    close = row.get("Close")
    open_ = row.get("Open")
    if not close or close in ("N/D", ""):
        raise PriceError(f"Stooq had no price for {ticker}")
    return Quote(
        ticker=ticker,
        price=float(close),
        # Stooq's intraday quote has no prior close; approximate with the open.
        previous_close=float(open_) if open_ and open_ not in ("N/D", "") else None,
        currency=None,
    )


def get_quote(ticker: str) -> Quote:
    """Return a :class:`Quote` for `ticker`, trying Yahoo then Stooq."""
    errors = []
    for source in (_from_yahoo, _from_stooq):
        try:
            return source(ticker)
        except (urllib.error.URLError, PriceError, ValueError, KeyError,
                json.JSONDecodeError, TimeoutError) as exc:
            errors.append(f"{source.__name__}: {exc}")
    raise PriceError(
        f"Could not fetch a price for {ticker}. Tried: " + " | ".join(errors)
    )
