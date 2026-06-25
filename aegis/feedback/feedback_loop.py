"""Closed-loop feedback: tracks rolling performance per regime and actually
tightens that regime's risk budget multiplier when drawdown or win-rate
thresholds are breached -- not just logging a suggestion. The multiplier
is persisted to disk, so it carries across runs: a regime that blew through
its drawdown alert in one run starts the next run already de-risked.

Still deliberately rule-based, not a learned model -- every adjustment
traces to a named threshold, so it's auditable rather than a black box that
drifts unpredictably over time.
"""

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field

DEFAULT_STATE_PATH = "state/feedback_state.json"
MIN_MULTIPLIER = 0.2
DRAWDOWN_TIGHTEN_FACTOR = 0.7
WIN_RATE_TIGHTEN_FACTOR = 0.85


@dataclass
class RegimeStats:
    trades: int = 0
    wins: int = 0
    total_pnl: float = 0.0
    peak_balance: float = 0.0
    max_drawdown_pct: float = 0.0


class FeedbackLoop:
    def __init__(self, drawdown_alert_pct: float = 5.0, state_path: str = DEFAULT_STATE_PATH):
        self.stats: dict[str, RegimeStats] = defaultdict(RegimeStats)
        self.drawdown_alert_pct = drawdown_alert_pct
        self.state_path = state_path
        self.regime_multipliers: dict[str, float] = self._load_state()

    def get_multiplier(self, regime: str) -> float:
        return self.regime_multipliers.get(regime, 1.0)

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

    def adjust(self) -> list[str]:
        """Applies one tightening step per breached condition, mutating
        regime_multipliers in place. Call once per run (not per trade) so a
        single run can't runaway-shrink its own multiplier; persisted state
        is what lets tightening compound across multiple runs."""
        applied = []
        for regime, s in self.stats.items():
            if s.trades == 0:
                continue
            win_rate = s.wins / s.trades
            current = self.get_multiplier(regime)

            if s.max_drawdown_pct >= self.drawdown_alert_pct:
                new_mult = max(MIN_MULTIPLIER, round(current * DRAWDOWN_TIGHTEN_FACTOR, 3))
                if new_mult != current:
                    applied.append(
                        f"[{regime}] max drawdown {s.max_drawdown_pct:.1f}% >= alert threshold "
                        f"{self.drawdown_alert_pct}% -> tightened risk multiplier {current:.2f} -> {new_mult:.2f}"
                    )
                    self.regime_multipliers[regime] = new_mult
                    current = new_mult

            if s.trades >= 10 and win_rate < 0.4:
                new_mult = max(MIN_MULTIPLIER, round(current * WIN_RATE_TIGHTEN_FACTOR, 3))
                if new_mult != current:
                    applied.append(
                        f"[{regime}] win rate {win_rate:.0%} over {s.trades} trades is low -> "
                        f"tightened risk multiplier {current:.2f} -> {new_mult:.2f}"
                    )
                    self.regime_multipliers[regime] = new_mult

        return applied

    def suggestions(self) -> list[str]:
        """Read-only preview of what adjust() would flag, without mutating
        state -- kept for callers that just want to inspect, not apply."""
        out = []
        for regime, s in self.stats.items():
            if s.trades == 0:
                continue
            win_rate = s.wins / s.trades
            if s.max_drawdown_pct >= self.drawdown_alert_pct:
                out.append(
                    f"[{regime}] max drawdown {s.max_drawdown_pct:.1f}% >= alert threshold "
                    f"{self.drawdown_alert_pct}% -> would tighten risk multiplier"
                )
            if s.trades >= 10 and win_rate < 0.4:
                out.append(
                    f"[{regime}] win rate {win_rate:.0%} over {s.trades} trades is low -> "
                    f"would tighten risk multiplier"
                )
        return out

    def _load_state(self) -> dict[str, float]:
        try:
            with open(self.state_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump(self.regime_multipliers, f, indent=2, sort_keys=True)
