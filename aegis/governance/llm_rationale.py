"""Optional LLM-generated rationale for CRO decisions, using the Qwen API
credits provided for Bitget AI Hackathon S1 (OpenAI-compatible endpoint).

If QWEN_API_KEY is unset or the call fails for any reason, callers should
fall back to the deterministic template reason already produced by
ChiefRiskOfficer -- this module never blocks or breaks the governance
pipeline, it only enriches the logged explanation text.
"""

import os

import requests

QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://hackathon.bitgetops.com/v1")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen3.6-plus")


def is_enabled() -> bool:
    return bool(QWEN_API_KEY)


def generate_rationale(*, regime: str, confidence: float, stance: str, template_reason: str, daily_pnl_pct: float, consecutive_losses: int) -> str:
    """Returns an LLM-written rationale, or the template_reason unchanged on
    any failure (missing key, network error, bad response)."""
    if not is_enabled():
        return template_reason

    prompt = (
        f"You are the Chief Risk Officer of an autonomous crypto trading system called Aegis. "
        f"Write ONE concise sentence (max 30 words) explaining this governance decision to a trader. "
        f"Facts: regime={regime}, confidence={confidence:.2f}, decision={stance}, "
        f"daily_pnl_pct={daily_pnl_pct:.2f}, consecutive_losses={consecutive_losses}. "
        f"Base template reason: '{template_reason}'. "
        f"Do not invent facts not given above. Output only the sentence, no quotes."
    )

    try:
        resp = requests.post(
            f"{QWEN_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": QWEN_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
                "temperature": 0.4,
                "enable_thinking": False,
            },
            timeout=15,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return text if text else template_reason
    except Exception:
        return template_reason
