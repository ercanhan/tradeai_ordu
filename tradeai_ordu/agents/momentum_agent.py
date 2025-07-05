from config.config import Config
# agents/momentum_agent.py

from agents.base_agent import BaseAgent
import numpy as np

class MomentumAgent(BaseAgent):
    """
    Süper momentum ve osilatör zekâsı:
    - Farklı timeframelerden momentum uyumu (multi-timeframe agreement)
    - RSI, MACD, Stoch, ROC, CCI, trend slope ve ani price/volume momentum
    - Whale ve hacim hareketiyle “fiziksel momentum” birleştirir
    - Volatility/fake breakout, pattern+momentum cross, auto-tune & feedback ready
    - Anomaly/fakeout ve dump/pump tuzağını tespit eder, skoru kırar!
    """

    default_params = {
        "rsi_buy": 31,
        "rsi_sell": 69,
        "macd_cross_weight": 0.22,
        "stoch_buy": 13,
        "stoch_sell": 87,
        "roc_threshold": 2.6,
        "cci_buy": -90,
        "cci_sell": 90,
        "slope_window": 10,
        "vol_spike_weight": 0.14,
        "osc_alert_bonus": 0.11,
        "momentum_spike_factor": 1.13,
        "whale_min": 1,
        "multi_timeframe_bonus": 0.21,
        "max_anomaly_risk": 0.24,
        "trend_strength_thresh": 0.0055,
        "pattern_conf_weight": 0.18,
        "past_win_boost": 0.17,
        "fakeout_penalty": 0.19,
    }

    def multi_timeframe_momentum(self, data_dicts):
        """
        Farklı zaman dilimi (ör: 15m, 1h, 4h) dataframe'leriyle momentum uyumunu ölçer.
        Her biri aynı yönde ise “multi-tf agreement” verir, aksi halde skor kırılır.
        """
        results = []
        for d in data_dicts:
            df = d.get("klines_df")
            if df is None:
                continue
            rsi = df["RSI_14"].iloc[-1]
            macd = df["MACD"].iloc[-1]
            macd_signal = df["MACD_SIGNAL"].iloc[-1]
            ema9 = df["EMA_9"].iloc[-1]
            ema21 = df["EMA_21"].iloc[-1]
            if rsi < 40 and macd > macd_signal and ema9 > ema21:
                results.append(1)
            elif rsi > 60 and macd < macd_signal and ema9 < ema21:
                results.append(-1)
            else:
                results.append(0)
        score = np.mean(results) if results else 0
        return score

    def analyze(self):
        d = self.data
        params = self.params
        df = d.get("klines_df")
        df1h = d.get("klines_df_1h")
        df4h = d.get("klines_df_4h")
        patterns = d.get("patterns", {})
        volume_anomaly = d.get("volume_anomaly", 1)
        ob_ana = d.get("orderbook_anomaly", {})
        whale_events = d.get("whale_events", [])
        osc_alerts = d.get("oscillator_alerts", [])
        confidence = 0.5
        risk = 0
        anomaly = False
        score = 0
        signals = []

        # 1. Multi-Timeframe Momentum Uyumu (15m-1h-4h)
        multi_tf_score = self.multi_timeframe_momentum([
            {"klines_df": df},
            {"klines_df": df1h},
            {"klines_df": df4h},
        ])
        if multi_tf_score > 0.5:
            score += params["multi_timeframe_bonus"]
            signals.append("Multi-timeframe upward momentum")
        elif multi_tf_score < -0.5:
            score -= params["multi_timeframe_bonus"]
            signals.append("Multi-timeframe downward momentum")

        # 2. Momentum Teknikleri (RSI, MACD, Stoch, CCI, ROC)
        last_rsi = df["RSI_14"].iloc[-1]
        stoch_k = df["STOCH_K"].iloc[-1]
        cci = df["CCI_20"].iloc[-1]
        roc = df["ROC"].iloc[-1]
        macd = df["MACD"].iloc[-1]
        macd_signal = df["MACD_SIGNAL"].iloc[-1]

        # RSI
        if last_rsi < params["rsi_buy"]:
            score += 0.31
            signals.append("RSI dip (momentum)")
        if last_rsi > params["rsi_sell"]:
            score -= 0.31
            signals.append("RSI tepe (momentum)")

        # Stoch
        if stoch_k < params["stoch_buy"]:
            score += 0.21
            signals.append("Stoch aşırı satım")
        if stoch_k > params["stoch_sell"]:
            score -= 0.21
            signals.append("Stoch aşırı alım")

        # CCI
        if cci < params["cci_buy"]:
            score += 0.14
            signals.append("CCI aşırı satım")
        if cci > params["cci_sell"]:
            score -= 0.14
            signals.append("CCI aşırı alım")

        # ROC
        if roc > params["roc_threshold"]:
            score += 0.18
            signals.append("ROC momentum +")
        if roc < -params["roc_threshold"]:
            score -= 0.18
            signals.append("ROC momentum -")

        # MACD
        if macd > macd_signal and df["MACD"].iloc[-2] < df["MACD_SIGNAL"].iloc[-2]:
            score += params["macd_cross_weight"]
            confidence += 0.07
            signals.append("MACD AL cross")
        if macd < macd_signal and df["MACD"].iloc[-2] > df["MACD_SIGNAL"].iloc[-2]:
            score -= params["macd_cross_weight"]
            confidence += 0.07
            signals.append("MACD SAT cross")

        # 3. Hacim & Whale Momentum
        if volume_anomaly > params["momentum_spike_factor"]:
            score += params["vol_spike_weight"]
            signals.append("Volume spike (momentum)")
        if len(whale_events) >= params["whale_min"]:
            score += 0.08 * len(whale_events)
            signals.append(f"{len(whale_events)}x whale momentum")

        # 4. Trend slope/price momentum spike
        slope = np.polyfit(range(params["slope_window"]), df["close"].iloc[-params["slope_window"]:], 1)[0]
        if abs(slope) > params["trend_strength_thresh"]:
            score += np.sign(slope) * 0.13
            signals.append(f"Slope trend {slope:.5f}")

        # 5. Pattern & Momentum cross-confirmation
        if any([patterns.get("breakout"), patterns.get("double_bottom")]):
            score += params["pattern_conf_weight"]
            signals.append("Momentum + breakout pattern")

        # 6. Osilatör Alertleri & Ensemble
        if osc_alerts:
            score += params["osc_alert_bonus"] * len(osc_alerts)
            signals += osc_alerts

        # 7. Fakeout/fake breakout/fake momentum tespiti & Volatility/Anomaly Shield
        volatility = df["Volatility"].iloc[-1]
        atr = df["ATR_14"].iloc[-1] if "ATR_14" in df else 1
        if volatility > 2.4 * (atr if not np.isnan(atr) else 1):
            risk += 0.12
            anomaly = True
            signals.append("Volatility anomaly (momentum)")
        # Dump/pump tuzağı veya sert yön değiştirme
        if ob_ana.get("spoofing", False) or ob_ana.get("spread", 0) > 2.5:
            risk += 0.14
            anomaly = True
            score -= params["fakeout_penalty"]
            signals.append("Orderbook anomaly (momentum) / Fakeout penalty")

        # 8. Feedback—geçmiş başarıya göre skor boost
        if hasattr(self, "history") and len(self.history) > 12:
            last_wins = [r for r in self.history[-12:] if r.get("direction") == r.get("last_trade_result", "none") and r.get("score", 0) > 0.1]
            if len(last_wins) > 6:
                score += params["past_win_boost"]
                confidence += 0.07
                signals.append("Geçmiş momentum başarısı: skor arttı")

        # 9. Anomaly/risk final filter
        if risk > params["max_anomaly_risk"] or anomaly:
            score *= 0.29
            confidence *= 0.6
            signals.append("MOMENTUM ANOMALY SHIELD: Skor ve güven kırıldı!")

        # --- Nihai Yön Kararı ---
        direction = "long" if score > 0.5 else ("short" if score < -0.5 else "none")
        explanation = (
            f"MomentumAgent (Tanrı): Ensemble: {', '.join(signals)} | Skor: {score:.2f}, Güven: {confidence:.2f}, Risk: {risk:.2f}"
        )
        self._base_output(
            score=score,
            confidence=confidence,
            risk=risk,
            direction=direction,
            type="momentum",
            explanation=explanation,
            anomaly=anomaly,
        )