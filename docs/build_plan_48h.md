# Aegis AI — 48-Hour Build Plan

Status: the skeleton in this repo already covers Hours 0-20 (runnable end to end on mocks, tests passing, comparison report producing a real proof-of-value number). Treat this plan as the checklist for what's left.

## Hours 0-6: Foundations (DONE)
- [x] Repo structure, config files (regime_rules, playbook_mapping, risk_limits)
- [x] Perception layer with mock fallback
- [x] Regime detector + unit tests
- [x] CRO governance engine + unit tests

## Hours 6-14: Core Loop (DONE)
- [x] Playbook selector + mock playbook client
- [x] Position sizer (volatility-scaled SL/TP) + unit tests
- [x] Paper trader
- [x] Trade logger (full CSV schema)
- [x] `run_aegis.py` end-to-end wiring — verified working

## Hours 14-20: Proof of Value (DONE)
- [x] `generate_comparison_report.py` — governed vs. ungoverned baseline
- [x] Confirmed headline result: higher return AND ~5x lower max drawdown

## Hours 20-30: Real Integration (PRIORITY — do this next)
- [ ] Wire `AGENT_HUB_BASE_URL` / `AGENT_HUB_API_KEY` to real Bitget Agent Hub endpoints (replace mock branch only — interface already supports it via `.live` flag)
- [ ] Wire `PLAYBOOK_BASE_URL` / `PLAYBOOK_API_KEY` to real GetAgent Playbook endpoints
- [ ] Replace `PaperTrader.simulate`'s random TP/SL resolution with real historical/live candle replay so PnL reflects actual price paths, not a coin flip
- [ ] Re-run comparison report against real data; confirm the proof-of-value story still holds (if it doesn't, that's also useful — tune `config/*.yaml` thresholds)

If live Agent Hub / Playbook access isn't available in time, this is fine to skip — the mock-based pipeline with stated rationale is itself defensible for judging, since the architecture and decision logic are real, only the data source is synthetic. State this clearly in the README/demo.

## Hours 30-38: Logging & Feedback Polish
- [ ] Run a longer simulation (300-500 iterations) to generate a richer `logs/trades.csv` showing all 4 regimes and at least one PAUSE-triggered drawdown breach
- [ ] Export/clean a sample `logs/trades.csv` to commit to the repo for judges who don't run the code themselves
- [ ] Add a simple `pandas`-based summary script (regime distribution, win rate per regime, equity curve) — nice-to-have, not required if time-constrained

## Hours 38-44: Demo & Materials
- [ ] Record demo video following `docs/demo_script.md`
- [ ] Drop in the chosen shield logo at `assets/aegis_shield_banner.png`
- [ ] Final README pass — make sure install/run instructions work on a clean checkout
- [ ] Pitch deck (3-5 slides): Problem → Solution → Architecture diagram → Proof-of-value comparison table → Ask/Close

## Hours 44-48: Submission
- [ ] Fill out submission form with thesis, repo link, demo video link
- [ ] Final smoke test: clone repo fresh, `pip install -r requirements.txt`, `python scripts/run_aegis.py`, confirm no errors
- [ ] Submit

## Non-negotiable cut line
If time runs short, the **comparison report number** and a **clean trades.csv** are the two artifacts that must exist no matter what gets cut. Everything in "Real Integration" is upgrade work, not MVP-critical — the architecture and governance logic are what's being judged, not whether the data source is live.
