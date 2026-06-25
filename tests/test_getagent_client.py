import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis.playbooks.getagent_client import find_best_match

SAMPLE_PLAYBOOKS = [
    {
        "strategy_id": "strategy-1", "name": "btc-ema-crossover", "status": "published",
        "trading_symbols": ["BTCUSDT"], "tags": ["trend", "ema", "btc"],
        "backtest_support": "full",
        "official_metrics": {"win_rate": 0.62, "sharpe_ratio": 1.8},
    },
    {
        "strategy_id": "strategy-2", "name": "btc-weak-trend", "status": "published",
        "trading_symbols": ["BTCUSDT"], "tags": ["trend"],
        "backtest_support": "full",
        "official_metrics": {"win_rate": 0.51, "sharpe_ratio": 0.4},
    },
    {
        "strategy_id": "strategy-3", "name": "eth-thing", "status": "published",
        "trading_symbols": ["ETHUSDT"], "tags": ["trend"],
        "backtest_support": "full",
        "official_metrics": {"win_rate": 0.99, "sharpe_ratio": 5.0},
    },
    {
        "strategy_id": "strategy-4", "name": "btc-draft", "status": "draft",
        "trading_symbols": ["BTCUSDT"], "tags": ["trend"],
        "backtest_support": "full",
        "official_metrics": {"win_rate": 0.99, "sharpe_ratio": 9.0},
    },
]


def test_prefers_higher_sharpe_among_matching_symbol():
    match = find_best_match(SAMPLE_PLAYBOOKS, "BTCUSDT", ["trend"])
    assert match["strategy_id"] == "strategy-1"


def test_filters_out_wrong_symbol():
    match = find_best_match(SAMPLE_PLAYBOOKS, "BTCUSDT", ["trend"])
    assert match["strategy_id"] != "strategy-3"


def test_ignores_unpublished_drafts():
    match = find_best_match(SAMPLE_PLAYBOOKS, "BTCUSDT", ["trend"])
    assert match["strategy_id"] != "strategy-4"


def test_returns_none_when_no_tag_overlap():
    match = find_best_match(SAMPLE_PLAYBOOKS, "BTCUSDT", ["mean-reversion"])
    assert match is None


def test_returns_none_for_empty_catalog():
    assert find_best_match([], "BTCUSDT", ["trend"]) is None
