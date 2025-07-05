from config.config import Config
# agents/midterm_agent.py

from agents.base_agent import BaseAgent
import numpy as np

class MidtermAgent(BaseAgent):
    """
    Orta vade ve güçlü trend/macro-formasyonlar için:
    - EMA/MA/Fibonacci, pattern, trend, volume anomaly, whale
    - Multi-layer trend & reversal tespiti, formasyon ve anomaly filtresi
    - Self-learning ve auto-tune parametrelerle optimize edilen ordu ajanı
    """

    default_params = {
        "ema_fast": 21,
        "ema_slow": 55,
        "ma_long": 200,
        "rsi_trend_high": 62,
        "rsi_trend_low": 38,
        "trend_slope_window": 24,
        "pattern_confirm": True,
        "min_volume_spike": 1.4,
        "min_trend_strength": 0.006,
        "whale_min_delta": 2,
        "max_volatility": 4.5,
    }

    def analyze(self):
        d = self.data
        params = self.params
        df = d.get("klines_df")
        ob_ana = d.get("orderbook_anomaly", {})
        whale_events = d.get("whale_events", [])
        patterns = d.get("patterns", {})
        volume_anomaly = d.get("volume_anomaly", 1)
        atr = df["ATR_14"].iloc[-1] if "ATR_14" in df else np.nan

        score = 0
        confidence = 0.5
        risk = 0
        signals = []
        anomaly = False

        # 1. Trend Gücü: EMA/MA cross, slope
        ema_fast = df["EMA_21"].iloc[-1]
        ema_slow = df["EMA_55"].iloc[-1]
        ma_long = df["SMA_200"].iloc[-1]
        last_close = df["close"].iloc[-1]
        slope = np.polyfit(range(params["trend_slope_window"]), df["close"].iloc[-params["trend_slope_window"]:], 1)[0]

        if ema_fast > ema_slow and ema_slow > ma_long and slope > params["min_trend_strength"]:
            score += 1.2
            confidence += 0.2
            signals.append("Güçlü yukarı trend (EMA>EMA>MA, slope)")
        elif ema_fast < ema_slow and ema_slow < ma_long and slope < -params["min_trend_strength"]:
            score -= 1.2
            confidence += 0.2
            signals.append("Güçlü aşağı trend (EMA<EMA<MA, slope)")

        # 2. RSI Trend Filter
        last_rsi = df["RSI_14"].iloc[-1]
        if last_rsi > params["rsi_trend_high"]:
            score += 0.35
            signals.append("RSI yüksek trend onayı")
        if last_rsi < params["rsi_trend_low"]:
            score -= 0.35
            signals.append("RSI düşük trend onayı")

        # 3. Macro Pattern & Formasyon
        if params["pattern_confirm"]:
            if patterns.get("double_bottom"):
                score += 0.6
                confidence += 0.08
                signals.append("Double Bottom formasyonu")
            if patterns.get("double_top"):
                score -= 0.6
                confidence += 0.08
                signals.append("Double Top formasyonu")
            if patterns.get("breakout"):
                score += 0.45
                signals.append("Major Breakout")
            if patterns.get("breakdown"):
                score -= 0.45
                signals.append("Major Breakdown")

        # 4. Volume Anomaly & Whale
        if volume_anomaly > params["min_volume_spike"]:
            score += 0.2
            signals.append("Hacim artışı orta vade")
        if len(whale_events) >= params["whale_min_delta"]:
            score += 0.25
            signals.append("Whale hareketi")

        # 5. Volatilite & Orderbook
        volatility = df["Volatility"].iloc[-1]
        if volatility > params["max_volatility"] * (atr if not np.isnan(atr) else 1):
            risk += 0.3
            anomaly = True
            signals.append("Aşırı volatilite, risk arttı")

        if ob_ana.get("spoofing", False):
            risk += 0.25
            anomaly = True
            signals.append("Orderbook manipülasyonu orta vade")

        # 6. Tuzak Koruması
        if risk > 0.4 or anomaly:
            score *= 0.25
            confidence *= 0.6
            signals.append("ANOMALY SHIELD: Skor azaltıldı (midterm)!")

        # --- Pozisyon Yönü Kararı (Long/Short/None) ---
        direction = "long" if score > 0.8 else ("short" if score < -0.8 else "none")

        # --- Sonuç ve Açıklama ---
        explanation = f"MidtermAgent analiz: {' | '.join(signals)} | Skor: {score:.2f}, Güven: {confidence:.2f}, Risk: {risk:.2f}"

        self._base_output(
            score=score,
            confidence=confidence,
            risk=risk,
            direction=direction,
            type="midterm",
            explanation=explanation,
            anomaly=anomaly,
        )