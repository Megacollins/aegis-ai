"""Real Bitget GetAgent Playbook catalog client.

Calls the documented GetAgent Playbook HTTP control plane
(`https://api.bitget.com/api/v1/playbook/list`) to fetch real published
Playbooks with their real backtested metrics (Sharpe, win rate, max
drawdown). The public list endpoint needs no auth; ACCESS-KEY is only
required for private surfaces (drafts, my-playbooks, enable/disable) which
Aegis does not need for read-only governance.

This is read-only catalog access, not live signal delivery -- GetAgent's
actual trade signals are delivered asynchronously via a Telegram
subscription (enable.md), which doesn't fit Aegis's synchronous
"decide now" model. What Aegis uses this for instead: picking which real,
evidenced Playbook to defer to for a given regime, and grounding its
confidence in that Playbook's real official_metrics rather than a
hardcoded number.
"""

import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

GETAGENT_BASE_URL = "https://api.bitget.com"
PLAYBOOK_API_KEY = os.getenv("PLAYBOOK_API_KEY", "")

_session = requests.Session()
_session.mount(
    "https://",
    HTTPAdapter(max_retries=Retry(total=0, status_forcelist=[429, 500, 502, 503, 504])),
)


def is_configured() -> bool:
    return bool(PLAYBOOK_API_KEY)


def list_published_playbooks() -> list[dict]:
    """Public catalog of published Playbooks with real backtested metrics.
    No auth required; raises on failure -- callers handle fallback."""
    resp = _session.get(f"{GETAGENT_BASE_URL}/api/v1/playbook/list", timeout=4)
    resp.raise_for_status()
    return resp.json()


def find_best_match(playbooks: list[dict], symbol: str, tags: list[str]) -> dict | None:
    """Picks the published Playbook whose trading_symbols/tags best match
    the requested symbol and regime-implied tags, preferring ones with full
    backtest evidence and the highest Sharpe ratio."""
    candidates = [
        p for p in playbooks
        if p.get("status") == "published"
        and symbol in p.get("trading_symbols", [])
        and set(tags) & set(p.get("tags", []))
    ]
    if not candidates:
        return None

    def score(p: dict) -> float:
        evidenced = p.get("backtest_support") == "full"
        sharpe = p.get("official_metrics", {}).get("sharpe_ratio", 0.0)
        return (1.0 if evidenced else 0.0) * 10 + sharpe

    return max(candidates, key=score)
