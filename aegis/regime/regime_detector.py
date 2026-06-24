"""Rule-based, fully auditable regime classifier.

Deliberately not a black-box ML model: every classification can be traced
back to a specific threshold in config/regime_rules.yaml, which matters for
hackathon judges verifying the logic and for live debugging.
"""

from dataclasses import dataclass
from enum import Enum

import yaml

from aegis.perception.feature_normalizer import FeatureVector


class Regime(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    CHOPPY = "CHOPPY"
    TRANSITIONING = "TRANSITIONING"


@dataclass
class RegimeResult:
    regime: Regime
    confidence: float
    reason: str


class RegimeDetector:
    def __init__(self, rules_path: str = "config/regime_rules.yaml"):
        with open(rules_path) as f:
            self.rules = yaml.safe_load(f)

    def detect(self, features: FeatureVector) -> RegimeResult:
        r = self.rules

        if features.news_shock_flag and r["news_shock_forces_transitioning"]:
            return RegimeResult(Regime.TRANSITIONING, 0.9, "news_shock_flag triggered forced TRANSITIONING")

        trend = features.trend_strength
        sentiment_adj = trend + r["sentiment_confirm_weight"] * features.sentiment_score

        if abs(trend) < r["trend_strength_weak_band"] and features.volatility >= r["volatility_choppy_min"]:
            confidence = min(1.0, features.volatility)
            return RegimeResult(Regime.CHOPPY, confidence, f"weak trend ({trend:.2f}) + high volatility ({features.volatility:.2f})")

        if sentiment_adj >= r["trend_strength_bull_min"]:
            confidence = min(1.0, abs(sentiment_adj))
            result = RegimeResult(Regime.BULLISH, confidence, f"trend+sentiment score {sentiment_adj:.2f} above bull threshold")
        elif sentiment_adj <= r["trend_strength_bear_max"]:
            confidence = min(1.0, abs(sentiment_adj))
            result = RegimeResult(Regime.BEARISH, confidence, f"trend+sentiment score {sentiment_adj:.2f} below bear threshold")
        else:
            confidence = 0.5
            result = RegimeResult(Regime.CHOPPY, confidence, f"trend+sentiment score {sentiment_adj:.2f} in neutral band")

        if result.confidence < r["confidence_floor"]:
            return RegimeResult(Regime.TRANSITIONING, result.confidence, f"low confidence ({result.confidence:.2f}) on {result.regime.value} -> downgraded to TRANSITIONING")

        return result
