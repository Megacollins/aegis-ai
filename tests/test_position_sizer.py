import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis.risk.position_sizer import size_position


def test_stop_loss_below_entry_for_long():
    order = size_position(
        direction="LONG", entry_price=65000.0, account_balance=10000.0,
        risk_budget_pct=1.0, max_position_size_pct=8.0, max_leverage=5, volatility=0.4,
    )
    assert order.stop_loss_price < 65000.0 < order.take_profit_price


def test_stop_loss_above_entry_for_short():
    order = size_position(
        direction="SHORT", entry_price=65000.0, account_balance=10000.0,
        risk_budget_pct=1.0, max_position_size_pct=8.0, max_leverage=5, volatility=0.4,
    )
    assert order.take_profit_price < 65000.0 < order.stop_loss_price


def test_position_size_respects_max_cap():
    order = size_position(
        direction="LONG", entry_price=65000.0, account_balance=10000.0,
        risk_budget_pct=50.0, max_position_size_pct=8.0, max_leverage=5, volatility=0.4,
    )
    assert order.position_size_usd <= 10000.0 * 0.08 + 1e-6
