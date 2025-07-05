from config.config import Config
# agents/sentiment_agent.py

from agents.base_agent import BaseAgent
import numpy as np

class SentimentAgent(BaseAgent):
    """
    Haber, sosyal medya, zincir üstü ve fon akışıyla duygu analizi yapan ajan.
    - Twitter/X, haber, telegram, Google trend, zincir üstü cüzdanlar, fon akışı edge’leri
    - Teknik ajanlarla ensemble, fake news spike, anomaly & feedback korumalı
    - Parametre, feedback, meta-feature ile sonsuz geliştirilebilir!
    """

    default_params = {
        "min_sentiment_score": 0.17,
        "news_weight": 0.14,
        "social_weight": 0.11,
        "onchain_weight": 0.12,
        "google_trend_weight": 0.07,
        "whale_sentiment_weight": 0.10,
        "pattern_confirm_weight": 0.12,
        "volume_confirm_weight": 0.10,
        "max_anomaly_risk": 0.22,
        "fake_news_penalty": 0.19,
        "history_boost_window": 12,
    }

    def analyze(self):
        d = self.data
        params = self.params

        sentiment_news = d.get("sentiment_news", 0)
        sentiment_social = d.get("sentiment_social", 0)
        sentiment_onchain = d.get("sentiment_onchain", 0)
        google_trend = d.get("google_trend", 0)
        whale_sentiment = d.get("whale_sentiment", 0)
        patterns = d.get("patterns", {})
        volume_anomaly = d.get("volume_anomaly", 1)
        dump_pump_flag = d.get("dump_pump_flag", False)
        fake_news_flag = d.get("fake_news_flag", False)

        confidence = 0.5
        risk = 0
        anomaly = False
        score = 0
        signals = []

        # 1. News ve sosyal duygu skoru
        score += sentiment_news * params["news_weight"]
        signals.append(f"Haber skoru: {sentiment_news:.2f}")
        score += sentiment_social * params["social_weight"]
        signals.append(f"Sosyal medya skoru: {sentiment_social:.2f}")

        # 2. Zincir üstü ve google trend
        score += sentiment_onchain * params["onchain_weight"]
        signals.append(f"Onchain skoru: {sentiment_onchain:.2f}")
        score += google_trend * params["google_trend_weight"]
        signals.append(f"Google trend: {google_trend:.2f}")

        # 3. Whale sentiment
        score += whale_sentiment * params["whale_sentiment_weight"]
        signals.append(f"Whale sentiment: {whale_sentiment:.2f}")

        # 4. Pattern, volume ve dump/pump cross-confirmation
        if patterns.get("breakout") or patterns.get("double_bottom"):
            score += params["pattern_confirm_weight"]
            signals.append("Sentiment + bullish pattern")
        if volume_anomaly > 1.18:
            score += params["volume_confirm_weight"]
            signals.append("Sentiment + volume")

        # 5. Fake news & anomaly shield
        if fake_news_flag or dump_pump_flag:
            score -= params["fake_news_penalty"]
            risk += 0.13
            anomaly = True
            signals.append("Fake news/dump-pump anomaly")

        # 6. Feedback geçmişiyle başarı boost
        if hasattr(self, "history") and len(self.history) > params["history_boost_window"]:
            last_wins = [r for r in self.history[-params["history_boost_window"]:] if r.get("direction") == r.get("last_trade_result", "none") and r.get("score", 0) > 0.1]
            if len(last_wins) > 4:
                score += 0.07
                confidence += 0.04
                signals.append("Sentiment geçmiş başarısı boost")

        # 7. Anomaly/risk final filter
        if risk > params["max_anomaly_risk"] or anomaly:
            score *= 0.24
            confidence *= 0.53
            signals.append("SENTIMENT ANOMALY SHIELD: Skor ve güven kırıldı!")

        # Nihai karar
        direction = "long" if score > params["min_sentiment_score"] else ("short" if score < -params["min_sentiment_score"] else "none")
        explanation = (
            f"SentimentAgent: {', '.join(signals)} | Skor: {score:.2f}, Güven: {confidence:.2f}, Risk: {risk:.2f}"
        )
        self._base_output(
            score=score,
            confidence=confidence,
            risk=risk,
            direction=direction,
            type="sentiment",
            explanation=explanation,
            anomaly=anomaly,
        )