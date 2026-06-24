"""Simulated order execution. No real funds touched; mirrors what would be
sent to the Bitget API / Playbook if Aegis were live-armed."""

import random
from dataclasses import dataclass

from aegis.risk.position_sizer import OrderParams


@dataclass
class TradeResult:
    entry_price: float
    exit_price: float
    realized_pnl: float


class PaperTrader:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def simulate(self, entry_price: float, order: OrderParams) -> TradeResult:
        """Randomly resolves the trade against SL/TP for demo purposes.
        Replace with real price-path replay against historical/live candles
        for a more rigorous backtest."""
        hits_take_profit = self.rng.random() < 0.5

        if order.direction == "LONG":
            exit_price = order.take_profit_price if hits_take_profit else order.stop_loss_price
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            exit_price = order.take_profit_price if hits_take_profit else order.stop_loss_price
            pnl_pct = (entry_price - exit_price) / entry_price

        realized_pnl = order.position_size_usd * pnl_pct * order.leverage

        return TradeResult(entry_price=entry_price, exit_price=exit_price, realized_pnl=round(realized_pnl, 2))
