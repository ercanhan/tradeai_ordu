from config.config import Config
# agents/dump_pump_agent.py

from agents.base_agent import BaseAgent
import numpy as np

class DumpPumpAgent(BaseAgent):
    """
    Dump/pump, ani tuzak, fakeout ve whale-panic edge’lerini tespit eden
    - Hacim ve fiyat spike, ani transfer, orderbook wipe/fakeout, funding/OI spike
    - Tüm edge’ler pattern, momentum, whale ve volume ile ensemble analiz
    - Sinyaller geçmiş başarıya göre optimize, anomaly shield ve insan gibi açıklama
    """

    default_params = {
        "dump_pump_vol_spike": 2.55,
        "dump_pump_price_spike": 0.027,   # %2.7 hareket
        "orderbook_wipe_factor": 5.5,
        "funding_spike": 0.0019,
        "oi_spike": 2.15,
        "pattern_reverse_weight": 0.21,
        "volume_confirm_weight": 0.16,
        "momentum_confirm_weight": 0.13,
        "max_anomaly_risk": 0.23,
        "history_boost_window": 12,
    }

    def analyze(self):
        d = self.data
        params = self.params
        df = d.get("klines_df")
        volume_anomaly = d.get("volume_anomaly", 1)
        price_now = df["close"].iloc[-1]
        price_prev = df["close"].iloc[-2]
        price_change = abs(price_now - price_prev) / price_prev if price_prev else 0
        whale_events = d.get("whale_events", [])
        funding_rates = d.get("funding_rates", [])
        oi_changes = d.get("oi_changes", [])
        ob_ana = d.get("orderbook_anomaly", {})
        patterns = d.get("patterns", {})
        momentum_score = d.get("momentum_score", 0)

        confidence = 0.5
        risk = 0
        anomaly = False
        score = 0
        signals = []

        # 1. Volume ve fiyat spike (ani dump/pump edge)
        if volume_anomaly > params["dump_pump_vol_spike"] and price_change > params["dump_pump_price_spike"]:
            score -= 0.21
            risk += 0.11
            anomaly = True
            signals.append("Dump/Pump: Hacim ve fiyat spike")
        elif volume_anomaly > params["dump_pump_vol_spike"]:
            risk += 0.09
            signals.append("Hacim spike (tuzak riski)")
        elif price_change > params["dump_pump_price_spike"]:
            risk += 0.09
            signals.append("Fiyat spike (tuzak riski)")

        # 2. Whale edge
        if len(whale_events) > 0:
            score -= 0.09 * len(whale_events)
            risk += 0.04 * len(whale_events)
            signals.append(f"{len(whale_events)}x whale transfer dump/pump riski")

        # 3. Funding ve OI spike
        funding_delta = float(funding_rates[-1]["fundingRate"]) - float(funding_rates[-2]["fundingRate"]) if len(funding_rates) > 2 else 0
        oi_change = float(oi_changes[-1]) - float(oi_changes[-2]) if len(oi_changes) > 2 else 0
        if abs(funding_delta) > params["funding_spike"]:
            risk += 0.13
            anomaly = True
            signals.append("Funding spike (dump/pump edge)")
        if abs(oi_change) > params["oi_spike"]:
            risk += 0.13
            anomaly = True
            signals.append("OI spike (dump/pump edge)")

        # 4. Orderbook wipe/fakeout (ani büyük wall kaybolması vs.)
        if ob_ana.get("spoofing", False) or ob_ana.get("spread", 0) > 3.3:
            score -= 0.15
            risk += 0.13
            anomaly = True
            signals.append("Orderbook wipe/fakeout")

        # 5. Pattern ve momentum reverse
        if patterns.get("double_top") or patterns.get("breakdown"):
            score -= params["pattern_reverse_weight"]
            signals.append("Dump/Pump + bearish pattern")
        if patterns.get("double_bottom") or patterns.get("breakout"):
            score -= params["pattern_reverse_weight"] * 0.6
            signals.append("Dump/Pump + bullish pattern (fakeout riski)")
        if momentum_score < -0.28:
            score -= params["momentum_confirm_weight"]
            signals.append("Dump/Pump + momentum (down)")

        # 6. Volume ve diğer edge onayı
        if volume_anomaly > 1.5:
            score -= params["volume_confirm_weight"]
            signals.append("Dump/Pump + volume onay")

        # 7. Feedback/Geçmiş başarıya göre risk optimizasyonu
        if hasattr(self, "history") and len(self.history) > params["history_boost_window"]:
            last_fails = [r for r in self.history[-params["history_boost_window"]:] if abs(r.get("score", 0)) < 0.05]
            if len(last_fails) > 4:
                risk += 0.09
                signals.append("Dump/Pump geçmişi: risk boost")

        # 8. Anomaly/risk shield
        if risk > params["max_anomaly_risk"] or anomaly:
            score *= 0.21
            confidence *= 0.58
            signals.append("DUMP/PUMP ANOMALY SHIELD: Skor ve güven kırıldı!")

        # Dump/Pump flag output (diğer ajanlara kullanabilmesi için)
        d["dump_pump_flag"] = (risk > 0.15 or anomaly)

        # Nihai karar (burada çoğunlukla “none” veya “işlemden kaç” önerir)
        direction = "none" if score < 0.15 else ("short" if score < -0.25 else "long" if score > 0.25 else "none")
        explanation = (
            f"DumpPumpAgent: {', '.join(signals)} | Skor: {score:.2f}, Güven: {confidence:.2f}, Risk: {risk:.2f}"
        )
        self._base_output(
            score=score,
            confidence=confidence,
            risk=risk,
            direction=direction,
            type="dump_pump",
            explanation=explanation,
            anomaly=anomaly,
        )