"""Combines raw per-skill outputs into a single normalized feature vector
consumed by the RegimeDetector."""

from dataclasses import dataclass

from aegis.perception.agent_hub_client import SkillSnapshot


@dataclass
class FeatureVector:
    trend_strength: float
    volatility: float
    sentiment_score: float
    macro_risk_flag: bool
    news_shock_flag: bool
    liquidity_score: float


def normalize(snapshots: dict[str, SkillSnapshot]) -> FeatureVector:
    technical = snapshots["technical-analysis"].raw
    macro = snapshots["macro-analyst"].raw
    sentiment = snapshots["sentiment-analyst"].raw
    market_intel = snapshots["market-intel"].raw
    news = snapshots["news-briefing"].raw

    return FeatureVector(
        trend_strength=technical.get("trend_strength", 0.0),
        volatility=technical.get("volatility", market_intel.get("volatility", 0.0)),
        sentiment_score=sentiment.get("sentiment_score", 0.0),
        macro_risk_flag=bool(macro.get("macro_risk_flag", False)),
        news_shock_flag=bool(news.get("news_shock_flag", False)),
        liquidity_score=market_intel.get("liquidity_score", 1.0),
    )
