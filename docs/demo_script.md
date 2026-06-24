# Aegis AI — Demo Script (target: 3-4 minutes)

## 1. Hook (20s)
"Most trading agents ask 'which trade should I take?' Aegis asks 'should I be trading at all, and with how much?' It's a Chief Risk Officer that governs Bitget Playbooks, not another signal bot."

## 2. Live run (60s)
```bash
python scripts/run_aegis.py --symbol BTCUSDT --iterations 50
```
While it runs: "Each tick, Aegis pulls all 5 Bitget Agent Hub skills, classifies the regime, and decides TRADE / REDUCE / PAUSE before any Playbook is even consulted."

## 3. Show the log (45s)
```bash
head -10 logs/trades.csv
```
Point to one PAUSE row and read the `reason` column aloud — e.g. "regime TRANSITIONING ... -> PAUSE, no playbook trusted." This is the auditability differentiator: every decision, including *not* trading, is logged with a stated reason.

## 4. Proof of value — the headline number (60s)
```bash
python scripts/generate_comparison_report.py --iterations 60
```
"Same market path, two runs. Aegis-governed: higher return, 1.8% max drawdown. Ungoverned baseline trading every regime at full size: lower return, 9.25% max drawdown. Aegis isn't just safer — it's better risk-adjusted, full stop."

## 5. Close (30s)
"This plugs into any current or future Bitget Playbook unmodified — Aegis only decides whether and how much, never what to trade. That's the governance layer Bitget's Playbook ecosystem is missing."

## Backup talking points (if Q&A)
- Why rule-based, not ML? Auditability — every regime call and every governance decision traces to a named threshold in `config/*.yaml`, which is verifiable in seconds, not a black box.
- How does this extend post-hackathon? Feedback loop already tracks per-regime drawdown/win-rate; v2 closes the loop by auto-tuning `risk_limits.yaml` thresholds instead of just suggesting them.
