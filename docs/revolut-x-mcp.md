# Connecting to the Revolut X MCP server

This repo is preconfigured to connect an MCP client (Claude Code / Claude
Desktop) to the **official Revolut X MCP server**
([`revolut-engineering/revolut-x-api`](https://github.com/revolut-engineering/revolut-x-api)).

That server lets you ask an AI assistant about your Revolut X **crypto
exchange** account — balances, market data, your order history — and run grid
strategy backtests. It is **read-only by design**: it cannot place, modify, or
cancel orders. (Note: Revolut X is Revolut's crypto exchange; this is separate
from the stock-price alert tool in this repo, which watches shares.)

## What's already wired up

- **[`.mcp.json`](../.mcp.json)** — committed MCP client config. It declares a
  server named `revolutx` launched with
  `node vendor/revolut-x-api/mcp/dist/index.js`. The path is overridable with
  the `REVOLUTX_MCP_PATH` environment variable if you build the server
  elsewhere.
- **[`scripts/setup-revolut-x-mcp.sh`](../scripts/setup-revolut-x-mcp.sh)** —
  builds the server from source into `vendor/` (git-ignored), since it is not
  published to npm.

## One-time setup

```bash
# 1. Build the server (clones + builds into vendor/). Needs Node >= 20.
./scripts/setup-revolut-x-mcp.sh

# 2. Open this project in Claude Code. The "revolutx" server starts
#    automatically from .mcp.json. Verify with:
claude mcp list            # should show: revolutx
#    or inside a session:  /mcp
```

If you'd rather not use the committed `.mcp.json`, you can register the server
globally instead:

```bash
claude mcp add revolutx node "$(pwd)/vendor/revolut-x-api/mcp/dist/index.js"
```

## Authenticate

The server ships tools that walk you through auth. In a Claude Code session,
ask:

> Set up my Revolut X API keys

This will:
1. Generate an **Ed25519** keypair locally.
2. Prompt you to register the **public** key in your Revolut X account
   (Profile → API in the Revolut X web app).
3. Store credentials under `~/.config/revolut-x/`
   (`config.json`, `private.pem` at `chmod 600`, `public.pem`). The location
   can be changed with `REVOLUTX_CONFIG_DIR`.

Your private key never leaves your machine, and no API keys are stored in this
repo.

## Tools exposed (verified)

The built server advertises 19 tools over stdio:

| Group        | Tools |
| ------------ | ----- |
| Auth/setup   | `get_instructions`, `get_trading_setup`, `generate_keypair`, `configure_api_key`, `get_cli_install_command`, `check_auth_status` |
| Account      | `get_balances`, `get_active_orders`, `get_historical_orders`, `get_order_fills`, `get_order_by_id` |
| Market data  | `get_currencies`, `get_currency_pairs`, `get_order_book`, `get_tickers`, `get_candles`, `get_public_trades` |
| Strategy     | `grid_backtest`, `grid_optimize` |

## Updating

Re-run `./scripts/setup-revolut-x-mcp.sh` to pull and rebuild the latest server.

## Security notes

- Read-only: the server cannot trade on your behalf.
- Treat `~/.config/revolut-x/private.pem` like a password; keep it `600`.
- `vendor/` is git-ignored so build artifacts and any local state stay out of
  version control.
