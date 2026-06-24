"""Main Aegis loop: perception -> regime -> CRO -> playbook selection ->
sizing -> paper execution -> logging -> feedback.

Run: python scripts/run_aegis.py --symbol BTCUSDT --iterations 50
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis.execution.paper_trader import PaperTrader
from aegis.feedback.feedback_loop import FeedbackLoop
from aegis.governance.cro_engine import AccountState, ChiefRiskOfficer, TradeStance
from aegis.governance.llm_rationale import generate_rationale
from aegis.logging.trade_logger import LogEntry, TradeLogger
from aegis.perception.agent_hub_client import AgentHubClient
from aegis.perception.feature_normalizer import normalize
from aegis.playbooks.playbook_client import PlaybookClient
from aegis.playbooks.playbook_selector import PlaybookSelector
from aegis.regime.regime_detector import RegimeDetector
from aegis.risk.position_sizer import size_position


def run(symbol: str, iterations: int, starting_balance: float, mock_price: float, seed: int):
    hub_client = AgentHubClient(symbol)
    playbook_client = PlaybookClient(symbol)
    regime_detector = RegimeDetector()
    cro = ChiefRiskOfficer()
    selector = PlaybookSelector()
    trader = PaperTrader(seed=seed)
    logger = TradeLogger()
    feedback = FeedbackLoop()

    balance = starting_balance
    consecutive_losses = 0
    daily_pnl_pct = 0.0
    price = mock_price

    for i in range(iterations):
        snapshots = hub_client.fetch_all()
        features = normalize(snapshots)
        regime_result = regime_detector.detect(features)

        account = AccountState(
            balance=balance,
            starting_balance=starting_balance,
            consecutive_losses=consecutive_losses,
            daily_pnl_pct=daily_pnl_pct,
        )
        decision = cro.decide(regime_result, account)
        decision.reason = generate_rationale(
            regime=regime_result.regime.value, confidence=regime_result.confidence,
            stance=decision.stance.value, template_reason=decision.reason,
            daily_pnl_pct=daily_pnl_pct, consecutive_losses=consecutive_losses,
        )
        activation = selector.select(regime_result.regime, decision)

        if decision.stance == TradeStance.PAUSE or not activation.playbooks:
            logger.log(LogEntry(
                timestamp=TradeLogger.now(), symbol=symbol, regime=regime_result.regime.value,
                confidence=regime_result.confidence, playbook="NONE", stance=decision.stance.value,
                direction="NONE", entry_price=None, position_size_usd=None, leverage=None,
                stop_loss=None, take_profit=None, exit_price=None, realized_pnl=None,
                running_balance=balance, reason=decision.reason,
            ))
            continue

        playbook = activation.playbooks[0]
        signal = playbook_client.get_signal(playbook)

        if signal.direction == "NONE":
            logger.log(LogEntry(
                timestamp=TradeLogger.now(), symbol=symbol, regime=regime_result.regime.value,
                confidence=regime_result.confidence, playbook=playbook, stance=decision.stance.value,
                direction="NONE", entry_price=None, position_size_usd=None, leverage=None,
                stop_loss=None, take_profit=None, exit_price=None, realized_pnl=None,
                running_balance=balance, reason=f"{decision.reason}; playbook {playbook} emitted no signal",
            ))
            continue

        order = size_position(
            direction=signal.direction,
            entry_price=price,
            account_balance=balance,
            risk_budget_pct=decision.risk_budget_pct,
            max_position_size_pct=activation.max_position_size_pct,
            max_leverage=activation.max_leverage,
            volatility=0.4,
        )
        result = trader.simulate(entry_price=price, order=order)

        balance += result.realized_pnl
        daily_pnl_pct = (balance - starting_balance) / starting_balance * 100
        consecutive_losses = consecutive_losses + 1 if result.realized_pnl < 0 else 0

        logger.log(LogEntry(
            timestamp=TradeLogger.now(), symbol=symbol, regime=regime_result.regime.value,
            confidence=regime_result.confidence, playbook=playbook, stance=decision.stance.value,
            direction=signal.direction, entry_price=result.entry_price,
            position_size_usd=order.position_size_usd, leverage=order.leverage,
            stop_loss=order.stop_loss_price, take_profit=order.take_profit_price,
            exit_price=result.exit_price, realized_pnl=result.realized_pnl,
            running_balance=round(balance, 2), reason=decision.reason,
        ))
        feedback.record(regime_result.regime.value, result.realized_pnl, balance)
        price = result.exit_price

    logger.close()

    print(f"\nFinal balance: {balance:.2f} (start: {starting_balance:.2f})")
    print("Feedback suggestions:")
    for s in feedback.suggestions():
        print(f"  - {s}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--starting-balance", type=float, default=10000.0)
    parser.add_argument("--mock-price", type=float, default=65000.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    run(args.symbol, args.iterations, args.starting_balance, args.mock_price, args.seed)
