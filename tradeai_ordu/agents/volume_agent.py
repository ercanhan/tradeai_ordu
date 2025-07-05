from config.config import Config
# agents/volume_agent.py

from agents.base_agent import BaseAgent
import numpy as np

class VolumeAgent(BaseAgent):
    """
    Tüm hacim anomalileri, ani giriş/çıkışlar, spot-futures akış, whale hacim şoku ve meta-feature analiz.
    - Hacim spike, dağılım, spot/futures ratio, volume burst, whale onayı, pattern/momentum ensemble
    - Dump/pump risk shield, manipülasyon cross-check, feedback/auto-tune ile sürekli optimize!
    """

    default_params = {
        "min_volume_spike": 1.38,
        "spot_futures_ratio_threshold": 2.5,
        "whale_volume_confirm": 0.16,
        "pattern_confirm_weight": 0.15,
        "momentum_confirm_weight": 0.13,
        "orderbook_confirm_weight": 0.12,
        "max_anomaly_risk": 0.19,
        "history_boost_window": 10,
        "dump_pump_penalty": 0.21,
    }

    def analyze(self):
        d = self.data
        params = self.params
        df = d.get("klines_df")
        volume_anomaly = d.get("volume_anomaly", 1)
        spot_futures_ratio = d.get("spot_futures_ratio", 1)
        whale_events = d.get("whale_events", [])
        patterns = d.get("patterns", {})
        momentum_score = d.get("momentum_score", 0)
        ob_ana = d.get("orderbook_anomaly", {})
        dump_pump_flag = d.get("dump_pump_flag", False)

        confidence = 0.5
        risk = 0
        anomaly = False
        score = 0
        signals = []

        # 1. Hacim spike & burst
        if volume_anomaly > params["min_volume_spike"]:
            score += 0.27
            confidence += 0.09
            signals.append(f"Hacim spike: {volume_anomaly:.2f}")

        # 2. Spot/Futures Ratio
        if spot_futures_ratio > params["spot_futures_ratio_threshold"]:
            score += 0.19
            signals.append(f"Spot/Futures hacim oranı yüksek ({spot_futures_ratio:.2f})")
        elif spot_futures_ratio < 1 / params["spot_futures_ratio_threshold"]:
            score -= 0.19
            signals.append(f"Futures hacim aşırı baskın ({spot_futures_ratio:.2f})")

        # 3. Whale hacim şoku
        if len(whale_events) > 0:
            score += params["whale_volume_confirm"] * len(whale_events)
            signals.append("Whale hacim şoku")

        # 4. Pattern & Momentum Cross-Check
        if patterns.get("breakout") or patterns.get("double_bottom"):
            score += params["pattern_confirm_weight"]
            signals.append("Volume + bullish pattern")
        if momentum_score > 0.25:
            score += params["momentum_confirm_weight"]
            signals.append("Volume + momentum")

        # 5. Orderbook confirmation
        if ob_ana.get("spoofing", False) or ob_ana.get("spread", 0) > 2.2:
            risk += 0.11
            anomaly = True
            signals.append("Volume + orderbook manipülasyon")

        # 6. Dump/Pump risk shield
        if dump_pump_flag:
            score -= params["dump_pump_penalty"]
            risk += 0.16
            anomaly = True
            signals.append("Dump/Pump anomaly: Hacim skor kırıldı")

        # 7. Feedback geçmişiyle başarı boost
        if hasattr(self, "history") and len(self.history) > params["history_boost_window"]:
            last_wins = [r for r in self.history[-params["history_boost_window"]:] if r.get("direction") == r.get("last_trade_result", "none") and r.get("score", 0) > 0.1]
            if len(last_wins) > 4:
                score += 0.07
                confidence += 0.04
                signals.append("Hacim geçmiş başarısı boost")

        # 8. Anomaly/Risk final filter
        if risk > params["max_anomaly_risk"] or anomaly:
            score *= 0.24
            confidence *= 0.59
            signals.append("VOLUME ANOMALY SHIELD: Skor ve güven kırıldı!")

        # Nihai karar
        direction = "long" if score > 0.31 else ("short" if score < -0.31 else "none")
        explanation = (
            f"VolumeAgent: {', '.join(signals)} | Skor: {score:.2f}, Güven: {confidence:.2f}, Risk: {risk:.2f}"
        )
        self._base_output(
            score=score,
            confidence=confidence,
            risk=risk,
            direction=direction,
            type="volume",
            explanation=explanation,
            anomaly=anomaly,
        )