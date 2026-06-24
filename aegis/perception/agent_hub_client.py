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
        self._rng = random.Random(symbol)

    def fetch_all(self) -> dict[str, SkillSnapshot]:
        return {skill: self._fetch_skill(skill) for skill in SKILLS}

    def _fetch_skill(self, skill: str) -> SkillSnapshot:
        if self.live:
            resp = requests.get(
                f"{AGENT_HUB_BASE_URL}/skills/{skill}",
                params={"symbol": self.symbol},
                headers={"Authorization": f"Bearer {AGENT_HUB_API_KEY}"},
                timeout=10,
            )
            resp.raise_for_status()
            return SkillSnapshot(skill=skill, raw=resp.json())
        return SkillSnapshot(skill=skill, raw=self._mock_response(skill))

    def _mock_response(self, skill: str) -> dict:
        rng = self._rng
        return {
            "trend_strength": round(rng.uniform(-1, 1), 3),
            "volatility": round(rng.uniform(0, 1), 3),
            "sentiment_score": round(rng.uniform(-1, 1), 3),
            "macro_risk_flag": rng.random() > 0.85,
            "news_shock_flag": rng.random() > 0.93,
            "liquidity_score": round(rng.uniform(0.3, 1), 3),
        }
