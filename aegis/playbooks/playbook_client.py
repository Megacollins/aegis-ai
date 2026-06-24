"""Interface to Bitget GetAgent Playbooks. For the MVP, generates a
deterministic mock trade signal per playbook so the pipeline is runnable
without live Playbook access; swap _mock_signal for a real API call when
credentials are available."""

import os
import random
from dataclasses import dataclass

import requests

PLAYBOOK_BASE_URL = os.getenv("PLAYBOOK_BASE_URL", "")
PLAYBOOK_API_KEY = os.getenv("PLAYBOOK_API_KEY", "")


@dataclass
class PlaybookSignal:
    playbook: str
    direction: str  # "LONG" | "SHORT" | "NONE"
    confidence: float


class PlaybookClient:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.live = bool(PLAYBOOK_BASE_URL and PLAYBOOK_API_KEY)
        self._rng = random.Random(symbol)

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
            return PlaybookSignal(playbook=playbook, direction=data["direction"], confidence=data["confidence"])
        return self._mock_signal(playbook)

    def _mock_signal(self, playbook: str) -> PlaybookSignal:
        rng = self._rng
        direction = rng.choice(["LONG", "SHORT", "NONE"])
        return PlaybookSignal(playbook=playbook, direction=direction, confidence=round(rng.uniform(0.4, 0.95), 2))
