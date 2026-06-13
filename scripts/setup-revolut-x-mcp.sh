#!/usr/bin/env bash
#
# Build the official Revolut X MCP server locally so the MCP client config in
# this repo (.mcp.json) can launch it.
#
# The server is NOT published to npm — it must be built from source. This
# script clones it into vendor/ (git-ignored) and builds the `mcp` workspace,
# producing vendor/revolut-x-api/mcp/dist/index.js — the path .mcp.json points
# at by default.
#
# Re-running is safe: it pulls the latest source and rebuilds.
#
# Requirements: git, Node.js >= 20, npm.
set -euo pipefail

REPO_URL="https://github.com/revolut-engineering/revolut-x-api.git"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR_DIR="$ROOT_DIR/vendor"
SRC_DIR="$VENDOR_DIR/revolut-x-api"

command -v git  >/dev/null || { echo "error: git is required" >&2; exit 1; }
command -v node >/dev/null || { echo "error: Node.js >= 20 is required" >&2; exit 1; }
command -v npm  >/dev/null || { echo "error: npm is required" >&2; exit 1; }

mkdir -p "$VENDOR_DIR"

if [ -d "$SRC_DIR/.git" ]; then
  echo "==> Updating existing checkout in $SRC_DIR"
  git -C "$SRC_DIR" pull --ff-only
else
  echo "==> Cloning $REPO_URL"
  git clone --depth 1 "$REPO_URL" "$SRC_DIR"
fi

echo "==> Installing dependencies (npm ci)"
( cd "$SRC_DIR" && npm ci )

echo "==> Building api and mcp workspaces"
( cd "$SRC_DIR" && npm run build -w api && npm run build -w mcp )

OUT="$SRC_DIR/mcp/dist/index.js"
if [ ! -f "$OUT" ]; then
  echo "error: build did not produce $OUT" >&2
  exit 1
fi

cat <<EOF

==> Done. MCP server built at:
      $OUT

The .mcp.json in this repo already points here, so open the project in
Claude Code and the "revolutx" server will start automatically.

Next: authenticate. In Claude Code, ask:
      "Set up my Revolut X API keys"

That generates an Ed25519 keypair, has you register the public key in your
Revolut X account, and stores credentials under ~/.config/revolut-x/.
The server is read-only — it can view balances/orders/market data but
cannot place, modify, or cancel trades.
EOF
