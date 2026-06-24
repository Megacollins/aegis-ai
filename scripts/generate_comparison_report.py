"""Runs two parallel simulations over the same mocked market path:
  1. Aegis-governed: full CRO + regime gating
  2. Ungoverned baseline: every regime trades at full default risk budget,
     never paused, leverage fixed at the regime's max ceiling

Prints a side-by-side comparison (max drawdown, final balance, trade count)
that is the core "proof of value" artifact for judging. Pass --export-json
to also write the full equity curves + regime sequence to a JSON file for
the web dashboard.

Run: python scripts/generate_comparison_report.py --iterations 60
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis.execution.paper_trader import PaperTrader
from aegis.governance.cro_engine import AccountState, ChiefRiskOfficer, GovernanceDecision, TradeStance
from aegis.perception.agent_hub_client import AgentHubClient
from aegis.perception.feature_normalizer import normalize
from aegis.playbooks.playbook_client import PlaybookClient
from aegis.playbooks.playbook_selector import PlaybookActivation, PlaybookSelector
from aegis.regime.regime_detector import RegimeDetector
from aegis.risk.position_sizer import size_position


def simulate(symbol: str, iterations: int, starting_balance: float, mock_price: float, seed: int, governed: bool) -> dict:
    hub_client = AgentHubClient(symbol)
    playbook_client = PlaybookClient(symbol)
    regime_detector = RegimeDetector()
    cro = ChiefRiskOfficer()
    selector = PlaybookSelector()
    trader = PaperTrader(seed=seed)

    balance = starting_balance
    peak_balance = starting_balance
    max_drawdown_pct = 0.0
    consecutive_losses = 0
    daily_pnl_pct = 0.0
    price = mock_price
    trades_taken = 0
    equity_curve = [round(starting_balance, 2)]
    regime_sequence = []

    for _ in range(iterations):
        snapshots = hub_client.fetch_all()
        features = normalize(snapshots)
        regime_result = regime_detector.detect(features)
        regime_sequence.append(regime_result.regime.value)

        if governed:
            account = AccountState(balance, starting_balance, consecutive_losses, daily_pnl_pct)
            decision = cro.decide(regime_result, account)
            activation = selector.select(regime_result.regime, decision)
        else:
            # ungoverned baseline: always TRADE, full default risk, regime's leverage ceiling
            decision = GovernanceDecision(TradeStance.TRADE, cro.limits["risk_budget_default_pct"], 999, "ungoverned baseline")
            cfg = cro.playbook_mapping[regime_result.regime.value]
            playbooks = cfg["playbooks"] or ["trend_following_long"]  # baseline ignores TRANSITIONING lockout
            activation = PlaybookActivation(playbooks, max(cfg["max_position_size_pct"], 8.0), max(cfg["max_leverage"], 5))

        if decision.stance == TradeStance.PAUSE or not activation.playbooks:
            equity_curve.append(round(balance, 2))
            continue

        signal = playbook_client.get_signal(activation.playbooks[0])
        if signal.direction == "NONE":
            equity_curve.append(round(balance, 2))
            continue

        order = size_position(
            direction=signal.direction, entry_price=price, account_balance=balance,
            risk_budget_pct=decision.risk_budget_pct, max_position_size_pct=activation.max_position_size_pct,
            max_leverage=activation.max_leverage, volatility=0.4,
        )
        result = trader.simulate(entry_price=price, order=order)

        balance += result.realized_pnl
        trades_taken += 1
        daily_pnl_pct = (balance - starting_balance) / starting_balance * 100
        consecutive_losses = consecutive_losses + 1 if result.realized_pnl < 0 else 0
        peak_balance = max(peak_balance, balance)
        if peak_balance > 0:
            max_drawdown_pct = max(max_drawdown_pct, (peak_balance - balance) / peak_balance * 100)
        price = result.exit_price
        equity_curve.append(round(balance, 2))

    return {
        "final_balance": round(balance, 2),
        "return_pct": round((balance - starting_balance) / starting_balance * 100, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "trades_taken": trades_taken,
        "equity_curve": equity_curve,
        "regime_sequence": regime_sequence,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--iterations", type=int, default=60)
    parser.add_argument("--starting-balance", type=float, default=10000.0)
    parser.add_argument("--mock-price", type=float, default=65000.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--export-json", default=None, help="Path to write full comparison JSON (equity curves + regimes) for the web dashboard")
    args = parser.parse_args()

    governed = simulate(args.symbol, args.iterations, args.starting_balance, args.mock_price, args.seed, governed=True)
    ungoverned = simulate(args.symbol, args.iterations, args.starting_balance, args.mock_price, args.seed, governed=False)

    print(f"\n{'Metric':<20}{'Aegis-Governed':<20}{'Ungoverned':<20}")
    print("-" * 60)
    for key in ["final_balance", "return_pct", "max_drawdown_pct", "trades_taken"]:
        print(f"{key:<20}{governed[key]:<20}{ungoverned[key]:<20}")

    if args.export_json:
        Path(args.export_json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.export_json, "w") as f:
            json.dump({"governed": governed, "ungoverned": ungoverned}, f)
        print(f"\nWrote dashboard data to {args.export_json}")
