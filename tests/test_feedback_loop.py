import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis.feedback.feedback_loop import FeedbackLoop


def test_default_multiplier_is_one(tmp_path):
    fb = FeedbackLoop(state_path=str(tmp_path / "state.json"))
    assert fb.get_multiplier("BULLISH") == 1.0


def test_drawdown_breach_tightens_multiplier(tmp_path):
    fb = FeedbackLoop(drawdown_alert_pct=5.0, state_path=str(tmp_path / "state.json"))
    fb.record("BULLISH", realized_pnl=100, running_balance=10100)
    fb.record("BULLISH", realized_pnl=-700, running_balance=9400)  # ~6.9% drawdown from peak

    applied = fb.adjust()
    assert len(applied) == 1
    assert fb.get_multiplier("BULLISH") < 1.0


def test_no_adjustment_when_thresholds_not_breached(tmp_path):
    fb = FeedbackLoop(drawdown_alert_pct=5.0, state_path=str(tmp_path / "state.json"))
    fb.record("BULLISH", realized_pnl=10, running_balance=10010)

    applied = fb.adjust()
    assert applied == []
    assert fb.get_multiplier("BULLISH") == 1.0


def test_multiplier_floors_at_minimum(tmp_path):
    fb = FeedbackLoop(drawdown_alert_pct=1.0, state_path=str(tmp_path / "state.json"))
    fb.regime_multipliers["BULLISH"] = 0.21
    fb.record("BULLISH", realized_pnl=-500, running_balance=9000)
    fb.stats["BULLISH"].peak_balance = 10000
    fb.stats["BULLISH"].max_drawdown_pct = 10.0

    fb.adjust()
    assert fb.get_multiplier("BULLISH") >= 0.2


def test_persistence_round_trip(tmp_path):
    state_path = str(tmp_path / "state.json")
    fb1 = FeedbackLoop(drawdown_alert_pct=5.0, state_path=state_path)
    fb1.record("CHOPPY", realized_pnl=-800, running_balance=9200)
    fb1.stats["CHOPPY"].peak_balance = 10000
    fb1.stats["CHOPPY"].max_drawdown_pct = 8.0
    fb1.adjust()
    fb1.save()

    tightened_value = fb1.get_multiplier("CHOPPY")
    assert tightened_value < 1.0

    fb2 = FeedbackLoop(drawdown_alert_pct=5.0, state_path=state_path)
    assert fb2.get_multiplier("CHOPPY") == tightened_value


def test_adjustment_compounds_across_separate_runs(tmp_path):
    state_path = str(tmp_path / "state.json")

    fb1 = FeedbackLoop(drawdown_alert_pct=5.0, state_path=state_path)
    fb1.stats["BEARISH"].trades = 1
    fb1.stats["BEARISH"].peak_balance = 10000
    fb1.stats["BEARISH"].max_drawdown_pct = 9.0
    fb1.adjust()
    fb1.save()
    after_run_1 = fb1.get_multiplier("BEARISH")

    fb2 = FeedbackLoop(drawdown_alert_pct=5.0, state_path=state_path)
    fb2.stats["BEARISH"].trades = 1
    fb2.stats["BEARISH"].peak_balance = 10000
    fb2.stats["BEARISH"].max_drawdown_pct = 9.0
    fb2.adjust()
    fb2.save()
    after_run_2 = fb2.get_multiplier("BEARISH")

    assert after_run_2 < after_run_1


def test_suggestions_does_not_mutate_state(tmp_path):
    fb = FeedbackLoop(drawdown_alert_pct=5.0, state_path=str(tmp_path / "state.json"))
    fb.stats["BULLISH"].trades = 1
    fb.stats["BULLISH"].peak_balance = 10000
    fb.stats["BULLISH"].max_drawdown_pct = 9.0

    fb.suggestions()
    assert fb.get_multiplier("BULLISH") == 1.0
