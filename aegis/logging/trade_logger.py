"""Comprehensive trade/decision logger. Every governance decision -- trade
or no-trade -- is written as a row so the full audit trail is verifiable,
not just the trades that executed."""

import csv
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

LOG_FIELDS = [
    "timestamp", "symbol", "regime", "confidence", "playbook", "stance",
    "direction", "entry_price", "position_size_usd", "leverage",
    "stop_loss", "take_profit", "exit_price", "realized_pnl",
    "running_balance", "reason",
]


@dataclass
class LogEntry:
    timestamp: str
    symbol: str
    regime: str
    confidence: float
    playbook: str
    stance: str
    direction: str
    entry_price: float | None
    position_size_usd: float | None
    leverage: int | None
    stop_loss: float | None
    take_profit: float | None
    exit_price: float | None
    realized_pnl: float | None
    running_balance: float
    reason: str


class TradeLogger:
    def __init__(self, path: str = "logs/trades.csv"):
        self.path = path
        is_new = not os.path.exists(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._file = open(path, "a", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=LOG_FIELDS)
        if is_new:
            self._writer.writeheader()
            self._file.flush()

    def log(self, entry: LogEntry) -> None:
        self._writer.writerow(asdict(entry))
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()
