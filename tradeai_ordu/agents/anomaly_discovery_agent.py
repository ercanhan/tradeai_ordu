from config.config import Config
from agents.base_agent import BaseAgent
import numpy as np

class AnomalyDiscoveryAgent(BaseAgent):
    """
    Klasik ajanların göremediği, beklenmedik edge, anomaly ve yeni fırsatları arayan;
    - AI/ML tabanlı sequence/outlier detection (ör. Isolation Forest, DBSCAN, ML/ensemble outlier, autoedge)
    - Teknik/volume/orderbook/whale/funding/oi/price feature'larından composite anomaly & pattern discovery
    - Pattern, momentum, volume, dump/pump ve sentiment ile ensemble scoring
    - Meta-feature & feedback ile sürekli kendi sınırlarını aşar, risk/fakeout shield ve insan gibi açıklama
    """

    default_params = {
        "z_score_threshold": 2.6,
        "ml_anomaly_weight": 0.23,
        "volume_outlier_weight": 0.14,
        "orderbook_outlier_weight": 0.13,
        "whale_outlier_weight": 0.13,
        "funding_oi_outlier_weight": 0.09,
        "sentiment_anomaly_weight": 0.10,
        "pattern_confirm_weight": 0.13,
        "max_anomaly_risk": 0.21,
        "history_boost_window": 10,
    }

    def ml_anomaly_detection(self, features):
        """
        Feature z-score, outlier ve future ML/AI detection interface.
        """
        if features is None or len(features) == 0:
            return 0, []
        features = np.array(features)
        z_scores = (features - np.mean(features)) / (np.std(features) + 1e-8)
        outliers = np.where(np.abs(z_scores) > self.params.get("z_score_threshold", 2.6))[0]
        score = len(outliers) * self.params.get("ml_anomaly_weight", 0.23)
        return score, outliers.tolist()

    async def analyze(self):
        d = self.data
        params = self.params
        df = d.get("klines_df")
        orderbook_anomaly = d.get("orderbook_anomaly", {})
        whale_events = d.get("whale_events", [])
        funding_rates = d.get("funding_rates", [])
        oi_changes = d.get("oi_changes", [])
        volume_anomaly = d.get("volume_anomaly", 1)
        sentiment_anomaly = d.get("sentiment_anomaly", 0)
        patterns = d.get("patterns", {})
        momentum_score = d.get("momentum_score", 0)
        dump_pump_flag = d.get("dump_pump_flag", False)

        confidence = 0.5
        risk = 0
        anomaly = False
        score = 0
        signals = []

        # 1. Teknik feature’lardan z-score/outlier ile anomaly yakala
        close_arr = np.array(df["close"][-35:]) if df is not None else np.array([])
        ml_score, outliers = self.ml_anomaly_detection(close_arr)
        score += ml_score
        if len(outliers) > 0:
            signals.append(f"Fiyat outlier {len(outliers)}x (z-score>{self.params.get('z_score_threshold', 2.6)})")

        # 2. Volume anomaly & outlier
        if volume_anomaly is not None and volume_anomaly > 2.1:
            score += params["volume_outlier_weight"]
            signals.append("Hacim outlier (spike)")

        # 3. Orderbook anomaly/outlier
        if orderbook_anomaly.get("spoofing", False) or (orderbook_anomaly.get("spread", 0) > 3.1):
            score += params["orderbook_outlier_weight"]
            risk += 0.13
            anomaly = True
            signals.append("Orderbook anomaly/outlier")

        # 4. Whale anomaly/outlier
        if whale_events and len(whale_events) > 1:
            score += params["whale_outlier_weight"]
            signals.append("Whale anomaly (ani büyük transfer)")

        # 5. Funding/OI anomaly
        funding_delta = 0
        if len(funding_rates) > 2:
            try:
                funding_delta = float(funding_rates[-1].get("fundingRate", 0)) - float(funding_rates[-2].get("fundingRate", 0))
            except Exception:
                funding_delta = 0

        oi_change = 0
        if len(oi_changes) > 2:
            try:
                oi_change = float(oi_changes[-1]) - float(oi_changes[-2])
            except Exception:
                oi_change = 0

        if abs(funding_delta) > 0.0014:
            score += params["funding_oi_outlier_weight"]
            signals.append("Funding outlier")
        if abs(oi_change) > 1.9:
            score += params["funding_oi_outlier_weight"]
            signals.append("OI outlier")

        # 6. Sentiment anomaly
        if sentiment_anomaly is not None and sentiment_anomaly > 0.6:
            score += params["sentiment_anomaly_weight"]
            signals.append("Sentiment anomaly")

        # 7. Pattern, momentum, dump/pump ensemble
        if patterns.get("breakout") or patterns.get("double_bottom"):
            score += params["pattern_confirm_weight"]
            signals.append("Anomaly + bullish pattern")
        if momentum_score > 0.25:
            score += 0.07
            signals.append("Anomaly + momentum")
        if dump_pump_flag:
            risk += 0.13
            anomaly = True
            signals.append("Dump/Pump anomaly (ek risk)")

        # 8. Feedback geçmişiyle başarı boost
        if hasattr(self, "history") and len(self.history) > params["history_boost_window"]:
            last_wins = [
                r for r in self.history[-params["history_boost_window"]:]
                if r.get("direction") == r.get("last_trade_result", "none") and r.get("score", 0) > 0.1
            ]
            if len(last_wins) > 4:
                score += 0.08
                confidence += 0.04
                signals.append("Anomaly geçmiş başarısı boost")

        # 9. Anomaly/risk final filter
        if risk > params["max_anomaly_risk"] or anomaly:
            score *= 0.21
            confidence *= 0.51
            signals.append("ANOMALY DISCOVERY SHIELD: Skor ve güven kırıldı!")

        # Nihai karar: edge “anomaly fırsat” ise long/short, risk yüksekse none.
        direction = "long" if score > 0.33 else ("short" if score < -0.33 else "none")
        explanation = (
            f"AnomalyDiscoveryAgent: {', '.join(signals)} | Skor: {score:.2f}, Güven: {confidence:.2f}, Risk: {risk:.2f}"
        )

        self._base_output(
            score=score,
            confidence=confidence,
            risk=risk,
            direction=direction,
            type="anomaly_discovery",
            explanation=explanation,
            anomaly=anomaly,
        )
