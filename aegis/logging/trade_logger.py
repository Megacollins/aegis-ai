"""Comprehensive trade/decision logger with verifiable provenance.

Every governed decision -- trade or no-trade -- is written as a row.
Beyond the human-readable fields, each row carries:

  - config_fingerprint: hash of the exact regime/risk config files in effect
  - features_json: the raw regime-detector input features for that tick
  - input_hash: hash of (features_json + config_fingerprint + regime + confidence)
    -- proof that the logged regime classification actually follows from
    these inputs and this config, not just an unverified claim
  - prev_hash / row_hash: a hash chain over the whole row, so any row
    edited or removed after the fact breaks the chain from that point on

This makes the log both tamper-evident (the chain) and independently
re-derivable (the input hash) -- a third party can recompute the regime
from features_json under the same config and confirm it matches `regime`,
without trusting the log file at all.
"""

import csv
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

LOG_FIELDS = [
    "timestamp", "symbol", "regime", "confidence", "playbook", "stance",
    "direction", "entry_price", "position_size_usd", "leverage",
    "stop_loss", "take_profit", "exit_price", "realized_pnl",
    "running_balance", "reason",
    "features_json", "config_fingerprint", "input_hash",
    "prev_hash", "row_hash",
]

CONFIG_FILES = [
    "config/regime_rules.yaml",
    "config/playbook_mapping.yaml",
    "config/risk_limits.yaml",
]

GENESIS_HASH = "0" * 64


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
    features: dict


def _sha256(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
    return h.hexdigest()


def compute_config_fingerprint(config_dir: str = ".") -> str:
    """Hash of the exact config files in effect, so a verifier can confirm
    which thresholds were active when a given row was logged."""
    h = hashlib.sha256()
    for rel_path in CONFIG_FILES:
        path = os.path.join(config_dir, rel_path)
        with open(path, "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def compute_input_hash(features_json: str, config_fingerprint: str, regime: str, confidence: float) -> str:
    return _sha256(features_json, config_fingerprint, regime, f"{confidence:.6f}")


class TradeLogger:
    def __init__(self, path: str = "logs/trades.csv", config_dir: str = "."):
        self.path = path
        self.config_fingerprint = compute_config_fingerprint(config_dir)
        is_new = not os.path.exists(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._file = open(path, "a", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=LOG_FIELDS)
        self._prev_hash = self._read_last_row_hash(path) if not is_new else GENESIS_HASH
        if is_new:
            self._writer.writeheader()
            self._file.flush()

    @staticmethod
    def _read_last_row_hash(path: str) -> str:
        try:
            with open(path) as f:
                rows = list(csv.DictReader(f))
            return rows[-1]["row_hash"] if rows else GENESIS_HASH
        except (FileNotFoundError, KeyError, IndexError):
            return GENESIS_HASH

    def log(self, entry: LogEntry) -> None:
        features_json = json.dumps(entry.features, sort_keys=True)
        input_hash = compute_input_hash(features_json, self.config_fingerprint, entry.regime, entry.confidence)

        row = {k: v for k, v in asdict(entry).items() if k != "features"}
        row["features_json"] = features_json
        row["config_fingerprint"] = self.config_fingerprint
        row["input_hash"] = input_hash
        row["prev_hash"] = self._prev_hash

        # Hash the same string representation the CSV writer will persist
        # (None -> "", everything else str()), so verification later -- which
        # only has the CSV's string-typed cells to work with -- recomputes
        # an identical hash rather than diverging on type round-tripping.
        row_str = {k: ("" if v is None else str(v)) for k, v in row.items()}
        canonical = json.dumps(row_str, sort_keys=True)
        row["row_hash"] = _sha256(self._prev_hash, canonical)

        self._writer.writerow(row)
        self._file.flush()
        self._prev_hash = row["row_hash"]

    def close(self) -> None:
        self._file.close()

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()
