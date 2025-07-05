from config.config import Config
# agents/orderbook_agent.py

from agents.base_agent import BaseAgent
import numpy as np

class OrderbookAgent(BaseAgent):
    """
    Tüm orderbook hareketleri, duvarlar, spoofing, spread, fake volume ve instant edge tespiti.
    - Büyük bid/ask wall, ani boşalma/dolma, spread anomaly, spoofing, dump/pump signal
    - Hacim ve fiyat hareketiyle cross-check, whale ile ensemble, anomaly shield
    - Feedback/auto-tune ve insan gibi açıklama!
    """

    default_params = {
        "min_wall_size": 200_000,
        "max_spread_atr": 1.8,
        "spoof_factor": 7.0,
        "instant_spike_factor": 2.9,
        "orderbook_score_weight": 0.31,
        "pattern_confirm_weight": 0.19,
        "whale_confirm_weight": 0.12,
        "momentum_confirm_weight": 0.14,
        "max_anomaly_risk": 0.24,
        "history_boost_window": 12,
        "fakeout_penalty": 0.17,
    }

    def analyze(self):
        d = self.data
        params = self.params
        df = d.get("klines_df")
        ob_ana = d.get("orderbook_anomaly", {})
        whale_events = d.get("whale_events", [])
        volume_anomaly = d.get("volume_anomaly", 1)
        patterns = d.get("patterns", {})
        momentum_score = d.get("momentum_score", 0)
        price = df["close"].iloc[-1]
        atr = df["ATR_14"].iloc[-1] if "ATR_14" in df else 1

        confidence = 0.5
        risk = 0
        anomaly = False
        score = 0
        signals = []

        # 1. Büyük Bid/Ask Wall
        if ob_ana.get("big_bid", 0) > params["min_wall_size"]:
            score += params["orderbook_score_weight"]
            signals.append(f"Büyük bid wall: {ob_ana['big_bid']:.0f}")
        if ob_ana.get("big_ask", 0) > params["min_wall_size"]:
            score -= params["orderbook_score_weight"]
            signals.append(f"Büyük ask wall: {ob_ana['big_ask']:.0f}")

        # 2. Spoofing Detection
        if ob_ana.get("spoofing", False):
            risk += 0.22
            anomaly = True
            score -= 0.19
            signals.append("Spoofing detected (manipülasyon)")

        # 3. Spread anomaly (fiyat aralığı)
        if ob_ana.get("spread", 0) > atr * params["max_spread_atr"]:
            risk += 0.12
            anomaly = True
            signals.append(f"Spread anomaly: {ob_ana.get('spread', 0):.2f}")

        # 4. Ani Hacim Spike
        if volume_anomaly > params["instant_spike_factor"]:
            score += 0.15
            confidence += 0.05
            signals.append("Ani hacim spike (orderbook edge)")

        # 5. Whale onayı
        if len(whale_events) > 0:
            score += params["whale_confirm_weight"] * len(whale_events)
            signals.append("Orderbook + whale hareketi")

        # 6. Pattern & Momentum Cross-Check
        if patterns.get("breakout"):
            score += params["pattern_confirm_weight"]
            signals.append("Orderbook + breakout pattern")
        if momentum_score > 0.3:
            score += params["momentum_confirm_weight"]
            signals.append("Orderbook + momentum")

        # 7. Fakeout & Manipülasyon Risk Kalkanı
        if risk > params["max_anomaly_risk"] or anomaly:
            score *= 0.19
            confidence *= 0.67
            signals.append("ORDERBOOK ANOMALY SHIELD: Skor ve güven kırıldı!")

        # 8. Feedback geçmişiyle başarı boost
        if hasattr(self, "history") and len(self.history) > params["history_boost_window"]:
            last_wins = [r for r in self.history[-params["history_boost_window"]:] if r.get("direction") == r.get("last_trade_result", "none") and r.get("score", 0) > 0.1]
            if len(last_wins) > 5:
                score += 0.07
                confidence += 0.04
                signals.append("Orderbook geçmiş başarısı boost")

        # Nihai karar
        direction = "long" if score > 0.37 else ("short" if score < -0.37 else "none")
        explanation = (
            f"OrderbookAgent: {', '.join(signals)} | Skor: {score:.2f}, Güven: {confidence:.2f}, Risk: {risk:.2f}"
        )
        self._base_output(
            score=score,
            confidence=confidence,
            risk=risk,
            direction=direction,
            type="orderbook",
            explanation=explanation,
            anomaly=anomaly,
        )