import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aegis.perception.feature_normalizer import FeatureVector
from aegis.regime.regime_detector import Regime, RegimeDetector


def make_features(**overrides) -> FeatureVector:
    base = dict(
        trend_strength=0.0, volatility=0.2, sentiment_score=0.0,
        macro_risk_flag=False, news_shock_flag=False, liquidity_score=1.0,
    )
    base.update(overrides)
    return FeatureVector(**base)


def test_news_shock_forces_transitioning():
    detector = RegimeDetector()
    result = detector.detect(make_features(trend_strength=0.8, news_shock_flag=True))
    assert result.regime == Regime.TRANSITIONING


def test_strong_uptrend_is_bullish():
    detector = RegimeDetector()
    result = detector.detect(make_features(trend_strength=0.8, sentiment_score=0.5))
    assert result.regime == Regime.BULLISH


def test_strong_downtrend_is_bearish():
    detector = RegimeDetector()
    result = detector.detect(make_features(trend_strength=-0.8, sentiment_score=-0.5))
    assert result.regime == Regime.BEARISH


def test_weak_trend_high_volatility_is_choppy():
    detector = RegimeDetector()
    result = detector.detect(make_features(trend_strength=0.05, volatility=0.8))
    assert result.regime == Regime.CHOPPY
