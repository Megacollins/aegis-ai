import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis.logging.trade_logger import GENESIS_HASH, LogEntry, TradeLogger, compute_input_hash


def make_entry(**overrides):
    base = dict(
        timestamp="2026-01-01T00:00:00+00:00", symbol="BTCUSDT", regime="BULLISH",
        confidence=0.9, playbook="trend_following_long", stance="TRADE", direction="LONG",
        entry_price=100.0, position_size_usd=50.0, leverage=2, stop_loss=95.0,
        take_profit=110.0, exit_price=105.0, realized_pnl=10.0, running_balance=10010.0,
        reason="test", features={"trend_strength": 0.5, "volatility": 0.2, "sentiment_score": 0.1,
                                  "macro_risk_flag": False, "news_shock_flag": False, "liquidity_score": 0.9},
    )
    base.update(overrides)
    return LogEntry(**base)


def test_first_row_chains_from_genesis(tmp_path):
    log_path = tmp_path / "trades.csv"
    logger = TradeLogger(path=str(log_path))
    logger.log(make_entry())
    logger.close()

    with open(log_path) as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["prev_hash"] == GENESIS_HASH


def test_rows_chain_sequentially(tmp_path):
    log_path = tmp_path / "trades.csv"
    logger = TradeLogger(path=str(log_path))
    logger.log(make_entry())
    logger.log(make_entry())
    logger.close()

    with open(log_path) as f:
        rows = list(csv.DictReader(f))
    assert rows[1]["prev_hash"] == rows[0]["row_hash"]


def test_input_hash_changes_if_features_change(tmp_path):
    log_path = tmp_path / "trades.csv"
    logger = TradeLogger(path=str(log_path))
    logger.log(make_entry(features={"trend_strength": 0.5, "volatility": 0.2, "sentiment_score": 0.1,
                                     "macro_risk_flag": False, "news_shock_flag": False, "liquidity_score": 0.9}))
    logger.log(make_entry(features={"trend_strength": -0.5, "volatility": 0.2, "sentiment_score": 0.1,
                                     "macro_risk_flag": False, "news_shock_flag": False, "liquidity_score": 0.9}))
    logger.close()

    with open(log_path) as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["input_hash"] != rows[1]["input_hash"]


def test_resuming_logger_continues_chain(tmp_path):
    log_path = tmp_path / "trades.csv"
    logger = TradeLogger(path=str(log_path))
    logger.log(make_entry())
    logger.close()

    logger2 = TradeLogger(path=str(log_path))
    logger2.log(make_entry())
    logger2.close()

    with open(log_path) as f:
        rows = list(csv.DictReader(f))
    assert rows[1]["prev_hash"] == rows[0]["row_hash"]
