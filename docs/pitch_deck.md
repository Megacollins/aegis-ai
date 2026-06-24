# Aegis AI — Pitch Deck Content

Drop each section below into its own slide. 5 slides, designed for a 3-4 minute pitch alongside the live demo in `docs/demo_script.md`.

---

## Slide 1 — Title
**Aegis AI**
*The Autonomous Chief Risk Officer for Bitget*

Bitget AI Hackathon S1 — Trading Agent Track

[Use assets/aegis_shield_banner.jpg as full-bleed background]

---

## Slide 2 — Problem
**Every trading agent answers the same question. The wrong one.**

- "Which trade should I take?" is a commoditized question — signal generation is well-trodden ground.
- The real failure mode in automated trading: no systematic governance over *when to trade, how much, and when to stop.*
- Bots and humans alike keep full-size positions on through choppy or adverse regimes with no kill-switch.
- Bitget's GetAgent Playbook ecosystem already supplies strategies. What's missing is a layer that decides whether to trust them right now.

---

## Slide 3 — Solution
**Aegis sits above the Playbooks, not beside them.**

Architecture (one line per stage, use the diagram from `docs/architecture.md`):

```
Agent Hub Skills → Regime Detection → Chief Risk Officer
   → Playbook Selection → Risk Sizing → Paper Execution → Logged
```

- Reads all 5 Bitget Agent Hub skills (macro, market-intel, sentiment, technical, news)
- Classifies market into BULLISH / BEARISH / CHOPPY / TRANSITIONING
- Governs: which Playbooks are allowed, how much capital/leverage, when to pause entirely
- Every decision — including *not* trading — is logged with a stated reason

---

## Slide 4 — Proof of Value (the headline slide)
**Same market path. Two outcomes.**

| Metric | Aegis-Governed | Ungoverned Baseline |
|---|---|---|
| Return | **+18.4%** | +14.75% |
| Max Drawdown | **1.79%** | 9.25% |
| Trades Taken | 33 | 39 |

*Generated live via `python scripts/generate_comparison_report.py` — reproducible, not cherry-picked.*

Takeaway: Aegis doesn't just reduce risk — it improves risk-adjusted return by being selective about *when* to deploy capital, not by predicting better.

---

## Slide 5 — Why It Wins / Close
- **Auditable, not a black box** — every regime call and governance decision traces to a named threshold in config, verifiable in seconds.
- **Composable** — plugs into any current or future Bitget Playbook unmodified; Aegis only decides whether/how much, never what to trade.
- **Real artifact, not a deck** — working code, passing tests, reproducible comparison report, full CSV audit trail.

*Ask: feedback on extending the rule-based feedback loop into closed-loop auto-tuning post-hackathon.*
