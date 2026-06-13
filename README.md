# Revolut Share Alerts

A small, dependency-light tool that watches the shares you hold (e.g. on
Revolut) and **emails you when it's time to act** — take profit, buy the dip,
or cut a loss — based on rules you define.

It does **not** connect to Revolut or place any trades. It only reads public
market prices and sends you an email so *you* can decide and act in the Revolut
app. Think of it as a personal price-alert watchdog you fully control.

## What it does

For each holding you configure, it fetches the latest price and checks your
rules:

| Rule          | Fires a **SELL** / **BUY** alert when…                       |
| ------------- | ------------------------------------------------------------ |
| `sell_above`  | price rises to/above your take-profit target                 |
| `stop_loss`   | price falls to/below your stop-loss floor                    |
| `buy_below`   | price drops to/below your buy-the-dip level                  |
| `gain_pct`    | price is up ≥ X% vs your average cost (take profit)          |
| `loss_pct`    | price is down ≥ X% vs your average cost (cut loss)           |
| `day_move_pct`| price moves ≥ X% in a single day (up *or* down) — heads-up   |

Matching alerts are emailed to you. A small state file remembers what already
fired so you don't get the same alert every run (configurable cooldown).

## Quick start

```bash
# 1. Install the one dependency
pip install -r requirements.txt

# 2. Create your config from the template and edit it
cp config.example.yaml config.yaml
$EDITOR config.yaml

# 3. Try it without sending any email
python -m share_alerts --config config.yaml --dry-run

# 4. Set up email and run for real
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASSWORD="your-16-char-app-password"   # see note below
python -m share_alerts --config config.yaml
```

### Gmail app password

Gmail blocks plain-password SMTP. Create a free **App Password**:
Google Account → Security → 2-Step Verification → App passwords. Use that
16-character value as `GMAIL_APP_PASSWORD`. The tool sends via
`smtp.gmail.com` over STARTTLS — your password never leaves your machine /
CI secret store.

## Configuration

See [`config.example.yaml`](config.example.yaml) for a fully commented
template. Minimal example:

```yaml
notifications:
  email:
    enabled: true
    to: you@gmail.com          # where alerts are sent

defaults:
  cooldown_hours: 12           # don't repeat the same alert within this window

holdings:
  - ticker: AAPL
    name: Apple Inc.
    avg_cost: 180.00           # optional — enables % rules and P/L context
    rules:
      sell_above: 240.00
      buy_below: 175.00
      stop_loss: 160.00
      gain_pct: 25             # also sell if up 25% vs avg_cost
      day_move_pct: 6          # heads-up on a >6% daily swing
```

Tickers use standard exchange symbols. For non-US listings add the exchange
suffix Yahoo Finance uses, e.g. `VOD.L` (London), `SAP.DE` (Frankfurt),
`AIR.PA` (Paris). Money amounts are in the share's own currency.

## Running on a schedule (GitHub Actions)

A ready-made workflow lives at
[`.github/workflows/alerts.yml`](.github/workflows/alerts.yml). It runs on a
cron schedule during market hours. Add two repository secrets
(`GMAIL_USER`, `GMAIL_APP_PASSWORD`) under
**Settings → Secrets and variables → Actions** and you're done.

You can also run it from cron on any machine:

```cron
*/30 13-21 * * 1-5  cd /path/to/agentic-foundation && /usr/bin/python3 -m share_alerts --config config.yaml
```

## Command-line options

```
python -m share_alerts [--config PATH] [--dry-run] [--once] [--ignore-cooldown] [-v]

  --config PATH       Path to config file (default: config.yaml)
  --dry-run           Evaluate and print alerts, but send no email
  --ignore-cooldown   Re-fire alerts even if recently sent (useful for testing)
  --state PATH        Where to store de-duplication state (default: .alert_state.json)
  -v, --verbose       Print each ticker's price and which rules were checked
```

## Related: Revolut X MCP server

This repo is also wired up to connect an MCP client (Claude Code / Claude
Desktop) to the official **Revolut X crypto exchange** MCP server, so you can
ask an AI assistant about your crypto balances, market data, and order history
(read-only). See [`docs/revolut-x-mcp.md`](docs/revolut-x-mcp.md). Quick start:
`./scripts/setup-revolut-x-mcp.sh`, then open the project in Claude Code.

Note this is separate from the share-alert tool above: the alert tool watches
**stock** prices and emails you; the MCP server is for your **crypto** account.

## Disclaimer

This is a personal tooling/automation project, **not financial advice**. Price
data is best-effort from public sources and may be delayed or wrong. You are
responsible for every trade you make. Always double-check prices in Revolut
before acting.
