"""Tiny JSON-backed store so the same alert isn't emailed every run."""

from __future__ import annotations

import json
import time
from pathlib import Path


class AlertState:
    """Records when each alert key last fired, enforcing a cooldown window."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._fired: dict[str, float] = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                if isinstance(data, dict):
                    # Keep only well-formed numeric timestamps.
                    self._fired = {
                        str(k): float(v)
                        for k, v in data.get("fired", {}).items()
                        if isinstance(v, (int, float))
                    }
            except (json.JSONDecodeError, ValueError, OSError):
                # Corrupt state should never block alerting; start fresh.
                self._fired = {}

    def should_fire(self, key: str, cooldown_hours: float, now: float | None = None) -> bool:
        """True if `key` hasn't fired within the cooldown window."""
        now = time.time() if now is None else now
        last = self._fired.get(key)
        if last is None:
            return True
        return (now - last) >= cooldown_hours * 3600.0

    def mark_fired(self, key: str, now: float | None = None) -> None:
        self._fired[key] = time.time() if now is None else now

    def save(self) -> None:
        payload = {"fired": self._fired}
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(self.path)  # atomic on the same filesystem
