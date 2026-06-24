"""Lightweight, rule-based feedback loop. Tracks rolling performance per
regime and surfaces threshold-adjustment suggestions. Deliberately not a
learned model for the MVP -- judges can read exactly why a suggestion
fired, and it's safe to demo without overfitting risk."""

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class RegimeStats:
    trades: int = 0
    wins: int = 0
    total_pnl: float = 0.0
    peak_balance: float = 0.0
    max_drawdown_pct: float = 0.0


class FeedbackLoop:
    def __init__(self, drawdown_alert_pct: float = 5.0):
        self.stats: dict[str, RegimeStats] = defaultdict(RegimeStats)
        self.drawdown_alert_pct = drawdown_alert_pct

    def record(self, regime: str, realized_pnl: float, running_balance: float) -> None:
        s = self.stats[regime]
        s.trades += 1
        s.total_pnl += realized_pnl
        if realized_pnl > 0:
            s.wins += 1
        s.peak_balance = max(s.peak_balance, running_balance)
        if s.peak_balance > 0:
            drawdown_pct = (s.peak_balance - running_balance) / s.peak_balance * 100
            s.max_drawdown_pct = max(s.max_drawdown_pct, drawdown_pct)

    def suggestions(self) -> list[str]:
        out = []
        for regime, s in self.stats.items():
            if s.trades == 0:
                continue
            win_rate = s.wins / s.trades
            if s.max_drawdown_pct >= self.drawdown_alert_pct:
                out.append(
                    f"[{regime}] max drawdown {s.max_drawdown_pct:.1f}% >= alert threshold "
                    f"{self.drawdown_alert_pct}% -> consider tightening risk_budget_default_pct for this regime"
                )
            if s.trades >= 10 and win_rate < 0.4:
                out.append(
                    f"[{regime}] win rate {win_rate:.0%} over {s.trades} trades is low -> "
                    f"consider removing a playbook from this regime's permitted set"
                )
        return out
