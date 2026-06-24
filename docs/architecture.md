# Aegis AI — Architecture

## Layers

### 1. Perception (`aegis/perception/`)
- `agent_hub_client.py` — calls Bitget Agent Hub skills (macro-analyst, market-intel, sentiment-analyst, technical-analysis, news-briefing). Falls back to a deterministic mock per-symbol RNG stream when no credentials are configured.
- `feature_normalizer.py` — flattens the 5 skill responses into one `FeatureVector`: trend_strength, volatility, sentiment_score, macro_risk_flag, news_shock_flag, liquidity_score.

### 2. Regime Detection (`aegis/regime/regime_detector.py`)
Rule-based classifier, thresholds in `config/regime_rules.yaml`. Outputs `RegimeResult(regime, confidence, reason)`. Deliberately transparent (no ML black box) so every classification is auditable in the demo.

Priority order: news shock → forced TRANSITIONING; weak trend + high volatility → CHOPPY; trend+sentiment composite vs. bull/bear thresholds; low-confidence downgrade → TRANSITIONING.

### 3. Chief Risk Officer / Governance (`aegis/governance/cro_engine.py`)
Given `RegimeResult` + `AccountState`, returns a `GovernanceDecision(stance, risk_budget_pct, max_leverage, reason)`. Stance is one of TRADE / REDUCE / PAUSE. Checks run in priority order:
1. Daily drawdown breach → PAUSE
2. Recent news shock → PAUSE
3. TRANSITIONING regime → PAUSE
4. Consecutive loss streak → REDUCE
5. Low regime confidence → REDUCE
6. Otherwise → TRADE at default risk budget

Limits configured in `config/risk_limits.yaml`.

### 4. Playbook Selection (`aegis/playbooks/`)
- `playbook_selector.py` — regime + decision → permitted Playbook list, position size cap, leverage cap (config in `config/playbook_mapping.yaml`).
- `playbook_client.py` — interface to Bitget GetAgent Playbooks; mock signal generator as fallback.

### 5. Risk Allocation (`aegis/risk/position_sizer.py`)
Converts risk budget % into position size such that hitting the stop-loss loses exactly the budgeted amount. Stop distance is volatility-scaled (ATR-style), reward:risk ratio configurable (default 2:1).

### 6. Execution (`aegis/execution/paper_trader.py`)
Simulated fills against the order's SL/TP. No real funds. Swap for historical price-path replay for a more rigorous backtest.

### 7. Logging (`aegis/logging/trade_logger.py`)
Every decision — trade or no-trade — is written to `logs/trades.csv` with the full required schema (timestamp, symbol, regime, playbook, direction, entry/exit, size, leverage, SL/TP, PnL, running balance, reason).

### 8. Feedback (`aegis/feedback/feedback_loop.py`)
Rolling per-regime stats (win rate, max drawdown). Surfaces rule-based threshold-adjustment suggestions — not auto-applied in the MVP, but the mechanism is in place for a v2 closed loop.

## Data Flow

```
AgentHubClient.fetch_all()
  → feature_normalizer.normalize()
    → RegimeDetector.detect()
      → ChiefRiskOfficer.decide()
        → PlaybookSelector.select()
          → PlaybookClient.get_signal()
            → position_sizer.size_position()
              → PaperTrader.simulate()
                → TradeLogger.log()
                  → FeedbackLoop.record()
```

Entry point: `scripts/run_aegis.py`. Comparison artifact: `scripts/generate_comparison_report.py` runs the same loop twice (governed vs. ungoverned baseline) over an identical mocked price path.
