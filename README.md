# Aegis AI — The Autonomous Chief Risk Officer for Bitget

![Aegis AI](assets/aegis_shield_banner.jpg)

**Bitget AI Hackathon S1 — Trading Agent Track**

## Overview

Most AI trading agents answer "which trade should I take?" Aegis AI answers a more important question first: **"should I be trading right now, with how much capital, and using which strategy?"**

Aegis is an autonomous Chief Risk Officer that sits *above* Bitget GetAgent Playbooks. It continuously reads Bitget Agent Hub skills (macro-analyst, market-intel, sentiment-analyst, technical-analysis, news-briefing), classifies the market into one of four regimes, and governs — not generates — trading activity: which Playbooks are allowed, how much capital and leverage can be deployed, and when all trading should pause.

## Thesis

**Problem.** Signal generation is a commodity. The actual failure mode in automated trading is the lack of risk governance — full-size trading continues through choppy/adverse regimes with no systematic kill-switch.

**Solution.** Aegis is a governance layer over existing Bitget Playbooks: regime detection → risk budget + leverage ceiling → permitted Playbook set → sized, logged paper trades.

**Why it works.** Risk-adjusted return is dominated by avoiding catastrophic regimes, not by edge in good ones (the same principle behind institutional vol-targeting). Decoupling "regime + risk budget" from "strategy selection" lets Aegis plug into any current or future Playbook unmodified, and produces a fully auditable decision trail.

**Expected edge.** Side-by-side simulation (see `scripts/generate_comparison_report.py`) shows Aegis-governed execution beating an ungoverned baseline on **both** return and drawdown over the same market path — e.g. a sample 60-iteration run returned **+18.4% with 1.8% max drawdown**, vs. **+14.75% with 9.25% max drawdown** ungoverned.

## Architecture

```
Perception (Agent Hub Skills)
        ↓
Regime Detection Engine (BULLISH / BEARISH / CHOPPY / TRANSITIONING)
        ↓
Chief Risk Officer — Governance Layer (TRADE / REDUCE / PAUSE + risk budget)
        ↓
Playbook Selection & Activation Engine
        ↓
Risk Allocation & Position Sizing (volatility-adjusted SL/TP)
        ↓
Paper Trading Execution
        ↓
Comprehensive Trade Logger (CSV, fully auditable)
        ↓
Performance Feedback Loop (rule-based threshold suggestions)
```

See `docs/architecture.md` for the full diagram and module-level detail.

## Installation

```bash
git clone <repo-url>
cd aegis-ai
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # optional: fill in Agent Hub / Playbook credentials for live mode
```

Without credentials, Aegis runs against deterministic mock data so the full pipeline is runnable out of the box.

## Usage

Run the main governed paper-trading loop:

```bash
python scripts/run_aegis.py --symbol BTCUSDT --iterations 50
```

Outputs a full trade/decision log to `logs/trades.csv` — every row includes timestamp, regime, Playbook, stance, position parameters, realized PnL, running balance, and the CRO's stated reason for the decision.

Generate the governed-vs-ungoverned proof-of-value comparison:

```bash
python scripts/generate_comparison_report.py --iterations 60
```

Summarize a log (regime distribution, win rate, max drawdown):

```bash
python scripts/summarize_log.py --log logs/trades.csv
```

Run tests:

```bash
python -m pytest tests/ -q
```

A pre-generated 300-iteration sample log is committed at `logs/sample/sample_trades_300iter.csv` for judges who want to inspect real output without running the code — it covers all 4 regimes and all 3 governance stances (TRADE/REDUCE/PAUSE), including PAUSE rows triggered by simulated news shocks.

## Demo Instructions

1. Run `generate_comparison_report.py` live during the demo — point to the drawdown column as the headline number.
2. Open `logs/trades.csv` and walk through 2-3 rows, reading the `reason` column aloud — this is the auditability story.
3. Show a TRANSITIONING regime row where Aegis paused trading entirely — this is the "smarter than just trading more" story.

## Submission Notes

- Track: Trading Agent
- Built against Bitget Agent Hub skills: macro-analyst, market-intel, sentiment-analyst, technical-analysis, news-briefing
- Built to govern (not replace) Bitget GetAgent Playbooks
- All trading shown is paper/simulated — no real funds at risk
