"""Translates the CRO's risk budget into concrete order parameters:
position size, leverage, stop-loss and take-profit, using volatility
(ATR-style) based stop distance."""

from dataclasses import dataclass


@dataclass
class OrderParams:
    direction: str
    position_size_usd: float
    leverage: int
    stop_loss_price: float
    take_profit_price: float


def size_position(
    *,
    direction: str,
    entry_price: float,
    account_balance: float,
    risk_budget_pct: float,
    max_position_size_pct: float,
    max_leverage: int,
    volatility: float,
    stop_atr_multiplier: float = 1.5,
    reward_risk_ratio: float = 2.0,
) -> OrderParams:
    risk_amount_usd = account_balance * (risk_budget_pct / 100)

    # volatility is normalized [0, 1]; map it onto a realistic 0.5%-7.5% stop
    # distance band as a fraction of entry price (floor avoids zero-width stops).
    stop_distance_pct = max(0.005, volatility * stop_atr_multiplier * 0.05)

    if direction == "LONG":
        stop_loss_price = entry_price * (1 - stop_distance_pct)
        take_profit_price = entry_price * (1 + stop_distance_pct * reward_risk_ratio)
    else:
        stop_loss_price = entry_price * (1 + stop_distance_pct)
        take_profit_price = entry_price * (1 - stop_distance_pct * reward_risk_ratio)

    # position size such that hitting the stop loses exactly risk_amount_usd
    position_size_usd = min(
        risk_amount_usd / stop_distance_pct,
        account_balance * (max_position_size_pct / 100),
    )

    return OrderParams(
        direction=direction,
        position_size_usd=round(position_size_usd, 2),
        leverage=max_leverage,
        stop_loss_price=round(stop_loss_price, 4),
        take_profit_price=round(take_profit_price, 4),
    )
