"""The Chief Risk Officer (CRO) layer: the heart of Aegis.

Given the detected regime and current account state, decides whether
trading should happen at all, and what global risk budget / leverage
ceiling applies. Every decision carries a human-readable rationale that
gets written verbatim into the trade log.
"""

from dataclasses import dataclass
from enum import Enum

import yaml

from aegis.regime.regime_detector import Regime, RegimeResult


class TradeStance(str, Enum):
    TRADE = "TRADE"
    REDUCE = "REDUCE"
    PAUSE = "PAUSE"


@dataclass
class AccountState:
    balance: float
    starting_balance: float
    consecutive_losses: int
    daily_pnl_pct: float
    minutes_since_last_news_shock: float | None = None


@dataclass
class GovernanceDecision:
    stance: TradeStance
    risk_budget_pct: float
    max_leverage: int
    reason: str


class ChiefRiskOfficer:
    def __init__(self, risk_limits_path: str = "config/risk_limits.yaml", playbook_mapping_path: str = "config/playbook_mapping.yaml"):
        with open(risk_limits_path) as f:
            self.limits = yaml.safe_load(f)
        with open(playbook_mapping_path) as f:
            self.playbook_mapping = yaml.safe_load(f)

    def decide(self, regime_result: RegimeResult, account: AccountState, risk_multiplier: float = 1.0) -> GovernanceDecision:
        limits = self.limits
        regime_cfg = self.playbook_mapping[regime_result.regime.value]

        if account.daily_pnl_pct <= -limits["max_daily_drawdown_pct"]:
            return GovernanceDecision(
                TradeStance.PAUSE, 0.0, 1,
                f"daily drawdown {account.daily_pnl_pct:.2f}% breached max {limits['max_daily_drawdown_pct']}% -> PAUSE",
            )

        if account.minutes_since_last_news_shock is not None and account.minutes_since_last_news_shock < limits["news_shock_pause_minutes"]:
            return GovernanceDecision(
                TradeStance.PAUSE, 0.0, 1,
                f"news shock {account.minutes_since_last_news_shock:.0f}m ago, within {limits['news_shock_pause_minutes']}m pause window -> PAUSE",
            )

        if regime_result.regime == Regime.TRANSITIONING:
            return GovernanceDecision(
                TradeStance.PAUSE, 0.0, regime_cfg["max_leverage"],
                f"regime TRANSITIONING ({regime_result.reason}) -> PAUSE, no playbook trusted",
            )

        multiplier_note = f" (feedback-adjusted x{risk_multiplier:.2f})" if risk_multiplier != 1.0 else ""

        if account.consecutive_losses >= limits["max_consecutive_losses"]:
            return GovernanceDecision(
                TradeStance.REDUCE, limits["risk_budget_reduced_pct"] * risk_multiplier, max(1, regime_cfg["max_leverage"] // 2),
                f"{account.consecutive_losses} consecutive losses >= limit {limits['max_consecutive_losses']} -> REDUCE risk budget{multiplier_note}",
            )

        if regime_result.confidence < 0.6:
            return GovernanceDecision(
                TradeStance.REDUCE, limits["risk_budget_reduced_pct"] * risk_multiplier, regime_cfg["max_leverage"],
                f"regime {regime_result.regime.value} confidence {regime_result.confidence:.2f} below 0.6 -> REDUCE{multiplier_note}",
            )

        return GovernanceDecision(
            TradeStance.TRADE, limits["risk_budget_default_pct"] * risk_multiplier, regime_cfg["max_leverage"],
            f"regime {regime_result.regime.value} confidence {regime_result.confidence:.2f}, account healthy -> TRADE at default risk budget{multiplier_note}",
        )
