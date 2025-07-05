from config.config import Config
# agents/scalp_agent.py

from agents.base_agent import BaseAgent
import numpy as np

class ScalpAgent(BaseAgent):
    """
    Hızlı edge, trend dönüşü, scalp için ultra-akıllı analiz:
    - Momentum, pattern, orderbook anomaly, whale activity
    - Birden fazla onay + cross-check + anomaly shield
    - Kendi auto-tune parametreleri ve feedback tabanlı öğrenme
    """

    default_params = {
        "rsi_lower": 23,
        "rsi_upper": 77,
        "macd_cross_confirm": True,
        "ema_fast": 9,
        "ema_slow": 21,
        "atr_mult": 1.4,
        "min_volume_spike": 1.7,
        "confirm_pattern": True,
        "orderbook_spoof_factor": 7.0,
        "whale_min_delta": 3,
    }

    def analyze(self):
        d = self.data
        params = self.params
        df = d.get("klines_df")
        ob_ana = d.get("orderbook_anomaly", {})
        whale_events = d.get("whale_events", [])
        patterns = d.get("patterns", {})
        volume_anomaly = d.get("volume_anomaly", 1)
        osc_alerts = d.get("oscillator_alerts", [])

        # --- Multi-Layer Sinyal Üretimi ---
        score = 0
        signals = []
        risk = 0
        confidence = 0.5
        anomaly = False

        # 1. Teknik Momentum ve Trend
        last_rsi = df["RSI_14"].iloc[-1]
        last_macd = df["MACD"].iloc[-1]
        last_macd_signal = df["MACD_SIGNAL"].iloc[-1]
        ema_fast = df["EMA_9"].iloc[-1]
        ema_slow = df["EMA_21"].iloc[-1]
        last_close = df["close"].iloc[-1]
        atr = df["ATR_14"].iloc[-1] if "ATR_14" in df else np.nan

        # 2. Momentum: RSI & MACD & EMA Cross
        if last_rsi < params["rsi_lower"] and last_macd > last_macd_signal and ema_fast > ema_slow:
            score += 1.4
            confidence += 0.15
            signals.append("RSI aşırı satım + MACD AL + EMA cross")
        if last_rsi > params["rsi_upper"] and last_macd < last_macd_signal and ema_fast < ema_slow:
            score -= 1.4
            confidence += 0.15
            signals.append("RSI aşırı alım + MACD SAT + EMA aşağı")
        # EMA trend güçlüyse
        if abs(ema_fast - ema_slow) / last_close > 0.003:
            score += np.sign(ema_fast - ema_slow) * 0.3
            signals.append("EMA güç farkı")

        # 3. Pattern & Formasyon Onayı
        if params["confirm_pattern"]:
            if patterns.get("double_bottom"):
                score += 0.5
                confidence += 0.10
                signals.append("Double Bottom formasyonu")
            if patterns.get("double_top"):
                score -= 0.5
                confidence += 0.10
                signals.append("Double Top formasyonu")
            if patterns.get("bullish_engulfing"):
                score += 0.3
                signals.append("Bullish Engulfing")
            if patterns.get("bearish_engulfing"):
                score -= 0.3
                signals.append("Bearish Engulfing")
            if patterns.get("breakout"):
                score += 0.4
                signals.append("Breakout")
            if patterns.get("breakdown"):
                score -= 0.4
                signals.append("Breakdown")

        # 4. Volume Anomaly ve Spike
        if volume_anomaly > params["min_volume_spike"]:
            score += 0.25
            confidence += 0.05
            signals.append("Hacim spike +")
        if volume_anomaly < 0.6:
            score -= 0.25
            signals.append("Hacim düşüşü -")

        # 5. Orderbook Anomaly & Spoofing
        spoofing = ob_ana.get("spoofing", False)
        if spoofing:
            risk += 0.3
            anomaly = True
            signals.append("Orderbook spoofing tespit!")
        if ob_ana.get("spread", 0) > atr * params["atr_mult"]:
            risk += 0.15
            signals.append("Spread anomaly")

        # 6. Whale & Funding Edge (opsiyonel)
        if len(whale_events) >= params["whale_min_delta"]:
            score += 0.4
            confidence += 0.08
            signals.append("Whale transfer/funding spike")

        # 7. Oscillator Alert
        if any("RSI aşırı" in s for s in osc_alerts):
            risk += 0.07
            signals.append("RSI aşırı seviye alarmı")

        # 8. Anomaly/Tuzak Koruması
        if risk > 0.6 or anomaly:
            score *= 0.2
            confidence *= 0.5
            signals.append("ANOMALY SHIELD: Skor azaltıldı!")

        # --- Pozisyon Yönü Kararı (Long/Short/None) ---
        direction = "long" if score > 0.75 else ("short" if score < -0.75 else "none")

        # --- Sonuç ve Açıklama ---
        explanation = f"ScalpAgent sinyalleri: {' | '.join(signals)} | Toplam skor: {score:.2f}, Güven: {confidence:.2f}, Risk: {risk:.2f}"

        self._base_output(
            score=score,
            confidence=confidence,
            risk=risk,
            direction=direction,
            type="scalp",
            explanation=explanation,
            anomaly=anomaly,
        )