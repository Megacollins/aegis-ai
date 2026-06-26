"""Thin client for Bitget Agent Hub skills (macro-analyst, market-intel,
sentiment-analyst, technical-analysis, news-briefing).

For the hackathon MVP this calls the Agent Hub HTTP endpoints if configured,
and falls back to a deterministic mock so the rest of the pipeline is
runnable without live credentials.
"""

import os
import random
from dataclasses import dataclass, field

import requests

from aegis.perception import bitget_market_client

AGENT_HUB_BASE_URL = os.getenv("AGENT_HUB_BASE_URL", "")
AGENT_HUB_API_KEY = os.getenv("AGENT_HUB_API_KEY", "")

SKILLS = ["macro-analyst", "market-intel", "sentiment-analyst", "technical-analysis", "news-briefing"]


@dataclass
class SkillSnapshot:
    skill: str
    raw: dict = field(default_factory=dict)


class AgentHubClient:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.live = bool(AGENT_HUB_BASE_URL and AGENT_HUB_API_KEY)
        self.bitget_live = bitget_market_client.is_configured()
        self._rng = random.Random(symbol)
        self.live_fetch_count = 0
        self.mock_fallback_count = 0

    def fetch_all(self) -> dict[str, SkillSnapshot]:
        # Resolve the real-data attempt exactly once per tick -- all 5
        # "skills" share its outcome, success or fallback, instead of each
        # independently retrying the same failing call 5x.
        shared_raw = self._resolve_tick_data()
        return {skill: SkillSnapshot(skill=skill, raw=shared_raw) for skill in SKILLS}

    def _resolve_tick_data(self) -> dict:
        if self.live:
            # Agent Hub skills can genuinely differ per-skill; only Bitget
            # live/mock are unified across skills for this MVP.
            data = self._fetch_agent_hub_skill(SKILLS[0])
            self.live_fetch_count += 1
            return data
        if self.bitget_live:
            try:
                data = bitget_market_client.fetch_features(self.symbol)
                self.live_fetch_count += 1
                return data
            except Exception as e:
                print(f"[AgentHubClient] Bitget live fetch failed ({e!r}), falling back to mock for this tick")
        self.mock_fallback_count += 1
        return self._mock_response()

    def _fetch_agent_hub_skill(self, skill: str) -> dict:
        resp = requests.get(
            f"{AGENT_HUB_BASE_URL}/skills/{skill}",
            params={"symbol": self.symbol},
            headers={"Authorization": f"Bearer {AGENT_HUB_API_KEY}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def _mock_response(self) -> dict:
        rng = self._rng
        return {
            "trend_strength": round(rng.uniform(-1, 1), 3),
            "volatility": round(rng.uniform(0, 1), 3),
            "sentiment_score": round(rng.uniform(-1, 1), 3),
            "macro_risk_flag": rng.random() > 0.85,
            "news_shock_flag": rng.random() > 0.93,
            "liquidity_score": round(rng.uniform(0.3, 1), 3),
        }
