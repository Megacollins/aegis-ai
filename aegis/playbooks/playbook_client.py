"""Interface to Bitget GetAgent Playbooks.

Direction bias for each playbook name is fixed (trend_following_long is
always a LONG candidate, etc.) -- that's a property of which playbook was
selected, not something an API call decides. What can come from real data
is confidence: when the GetAgent Playbook catalog is reachable, Aegis looks
up a real published Playbook matching the symbol/regime tags and uses its
real backtested win_rate as the confidence instead of a random number.
Falls back to a fully mock signal if the catalog is unreachable or has no
matching evidenced Playbook.
"""

import os
import random
from dataclasses import dataclass

import requests

from aegis.playbooks import getagent_client

PLAYBOOK_BASE_URL = os.getenv("PLAYBOOK_BASE_URL", "")
PLAYBOOK_API_KEY = os.getenv("PLAYBOOK_API_KEY", "")

# Maps our local playbook names to the real-catalog tags/direction they imply.
PLAYBOOK_BIAS = {
    "trend_following_long": {"tags": ["trend"], "direction": "LONG"},
    "trend_following_short": {"tags": ["trend"], "direction": "SHORT"},
    "breakout_momentum": {"tags": ["breakout", "momentum"], "direction": "LONG"},
    "hedge_short": {"tags": ["hedge"], "direction": "SHORT"},
    "mean_reversion_range": {"tags": ["mean-reversion", "range"], "direction": "LONG"},
}


@dataclass
class PlaybookSignal:
    playbook: str
    direction: str  # "LONG" | "SHORT" | "NONE"
    confidence: float
    source: str = "mock"  # "mock" | "getagent_catalog" | "agent_hub_live"


class PlaybookClient:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.live = bool(PLAYBOOK_BASE_URL and PLAYBOOK_API_KEY)
        self.catalog_live = getagent_client.is_configured()
        self._rng = random.Random(symbol)
        self._catalog_cache: list[dict] | None = None
        self._catalog_attempted = False

    def get_signal(self, playbook: str) -> PlaybookSignal:
        if self.live:
            resp = requests.get(
                f"{PLAYBOOK_BASE_URL}/playbooks/{playbook}/signal",
                params={"symbol": self.symbol},
                headers={"Authorization": f"Bearer {PLAYBOOK_API_KEY}"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return PlaybookSignal(playbook=playbook, direction=data["direction"],
                                   confidence=data["confidence"], source="agent_hub_live")

        if self.catalog_live:
            real_signal = self._signal_from_catalog(playbook)
            if real_signal is not None:
                return real_signal

        return self._mock_signal(playbook)

    def _signal_from_catalog(self, playbook: str) -> PlaybookSignal | None:
        bias = PLAYBOOK_BIAS.get(playbook)
        if bias is None:
            return None

        if not self._catalog_attempted:
            self._catalog_attempted = True
            try:
                self._catalog_cache = getagent_client.list_published_playbooks()
            except Exception as e:
                print(f"[PlaybookClient] GetAgent catalog fetch failed ({e!r}), falling back to mock")
                self._catalog_cache = None

        if not self._catalog_cache:
            return None

        match = getagent_client.find_best_match(self._catalog_cache, self.symbol, bias["tags"])
        if match is None or match.get("backtest_support") != "full":
            return None

        win_rate = match.get("official_metrics", {}).get("win_rate")
        if win_rate is None:
            return None

        return PlaybookSignal(
            playbook=playbook, direction=bias["direction"],
            confidence=round(win_rate, 3), source="getagent_catalog",
        )

    def _mock_signal(self, playbook: str) -> PlaybookSignal:
        rng = self._rng
        direction = rng.choice(["LONG", "SHORT", "NONE"])
        return PlaybookSignal(playbook=playbook, direction=direction,
                               confidence=round(rng.uniform(0.4, 0.95), 2), source="mock")
