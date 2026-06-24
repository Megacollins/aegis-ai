import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis.governance.cro_engine import AccountState, ChiefRiskOfficer, TradeStance
from aegis.regime.regime_detector import Regime, RegimeResult


def make_account(**overrides) -> AccountState:
    base = dict(balance=10000.0, starting_balance=10000.0, consecutive_losses=0, daily_pnl_pct=0.0)
    base.update(overrides)
    return AccountState(**base)


def test_pauses_on_daily_drawdown_breach():
    cro = ChiefRiskOfficer()
    regime = RegimeResult(Regime.BULLISH, 0.9, "test")
    decision = cro.decide(regime, make_account(daily_pnl_pct=-9.0))
    assert decision.stance == TradeStance.PAUSE


def test_pauses_on_transitioning_regime():
    cro = ChiefRiskOfficer()
    regime = RegimeResult(Regime.TRANSITIONING, 0.9, "test")
    decision = cro.decide(regime, make_account())
    assert decision.stance == TradeStance.PAUSE


def test_reduces_on_consecutive_losses():
    cro = ChiefRiskOfficer()
    regime = RegimeResult(Regime.BULLISH, 0.9, "test")
    decision = cro.decide(regime, make_account(consecutive_losses=3))
    assert decision.stance == TradeStance.REDUCE


def test_trades_when_healthy_and_confident():
    cro = ChiefRiskOfficer()
    regime = RegimeResult(Regime.BULLISH, 0.9, "test")
    decision = cro.decide(regime, make_account())
    assert decision.stance == TradeStance.TRADE
