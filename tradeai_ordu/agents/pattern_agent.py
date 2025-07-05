from config.config import Config
# agents/pattern_agent.py

from agents.base_agent import BaseAgent
import numpy as np

# (Kendi ML modeli, autoedge veya yeni pattern fonksiyonu ileride kolayca enjekte edilebilir!)

class PatternAgent(BaseAgent):
    """
    Gelişmiş pattern & formasyon tespiti + ML/autoedge + meta-anomaly:
    - Ensemble scoring (pattern, hacim, whale, orderbook, volatilite, onay ağırlıkları)
    - ML/AI ile pattern doğrulama (autoedge interface)
    - Pattern başarı oranı feedback ile kendi ağırlığını optimize eder
    - Sonsuz gelişime, yeni edge injection’a açık
    """

    default_params = {
        "lookback": 45,
        "pattern_min_score": 0.45,
        "pattern_ml_threshold": 0.63,
        "multi_pattern_bonus": 0.22,
        "pattern_cross_check": True,
        "max_anomaly_risk": 0.38,
        "autoedge_enabled": True,
        "volume_confirm_weight": 0.19,
        "whale_confirm_weight": 0.11,
        "orderbook_confirm_weight": 0.12,
        "volatility_penalty": 0.17,
        "min_pattern_count": 1
    }

    def ml_pattern_score(self, df):
        """
        (Örnek ML model interface, ileride gerçek pattern ML modeliyle swap edilebilir)
        Şimdilik meta-feature ensemble ile örnek skor üret.
        """
        meta_score = 0
        pattern_count = 0
        if "patterns" in self.data:
            for pname, detected in self.data["patterns"].items():
                if detected:
                    meta_score += 0.17
                    pattern_count += 1
        # Meta-feature ile hacim, whale ve orderbook + pattern ağırlıkları
        meta_score += self.data.get("volume_anomaly", 1) * 0.08
        meta_score += len(self.data.get("whale_events", [])) * 0.04
        meta_score -= self.data.get("orderbook_anomaly", {}).get("spoofing", False) * 0.15
        meta_score -= self.data.get("orderbook_anomaly", {}).get("spread", 0) * 0.05
        # Ekstra: ATR/volatility cezası
        df = self.data["klines_df"]
        volatility = df["Volatility"].iloc[-1]
        atr = df["ATR_14"].iloc[-1] if "ATR_14" in df else 1
        if volatility > 2.7 * (atr if not np.isnan(atr) else 1):
            meta_score -= 0.13
        return meta_score, pattern_count

    def analyze(self):
        d = self.data
        params = self.params
        df = d.get("klines_df")
        patterns = d.get("patterns", {})
        volume_anomaly = d.get("volume_anomaly", 1)
        ob_ana = d.get("orderbook_anomaly", {})
        whale_events = d.get("whale_events", [])
        confidence = 0.5
        risk = 0
        signals = []
        anomaly = False
        score = 0

        # 1. Klasik Pattern Scanning (multi-detection + weighting)
        pattern_hits = []
        pattern_weights = {
            "double_bottom": 0.8, "double_top": -0.8,
            "bullish_engulfing": 0.42, "bearish_engulfing": -0.42,
            "doji": 0, "breakout": 0.66, "breakdown": -0.66, "wedge": 0.18
        }
        for pname, weight in pattern_weights.items():
            if patterns.get(pname):
                score += weight
                if pname not in ["doji"]:  # Doji risk skoruna yazar
                    pattern_hits.append(pname)
                else:
                    risk += 0.13

        # 2. ML/AI Pattern Skor (ensemble/autoedge onayı)
        ml_score, pattern_count = self.ml_pattern_score(df)
        score += ml_score
        if params["autoedge_enabled"] and hasattr(self, "autoedge"):
            # Kendi autoedge fonksiyonun varsa uygula (future ML/AI support)
            autoedge_score = self.autoedge(df, patterns, self.data)
            score += autoedge_score
            signals.append(f"AutoEdge (AI): {autoedge_score:.2f}")

        # 3. Cross-check: Pattern + Volume/Whale/Orderbook onay ağırlıkları
        if pattern_count >= params["min_pattern_count"]:
            score += (volume_anomaly - 1) * params["volume_confirm_weight"]
            score += len(whale_events) * params["whale_confirm_weight"]
            score += (ob_ana.get("spoofing", False) * -1) * params["orderbook_confirm_weight"]
            signals.append(f"Pattern-ensemble: {pattern_hits}, Hacim/Whale/Orderbook onayı")

        # 4. Volatility/anomaly penalty
        volatility = df["Volatility"].iloc[-1]
        atr = df["ATR_14"].iloc[-1] if "ATR_14" in df else 1
        if volatility > 2.7 * (atr if not np.isnan(atr) else 1):
            score -= params["volatility_penalty"]
            risk += 0.18
            anomaly = True
            signals.append("Volatilite penalty (pattern)")

        # 5. Anomaly shield / cross-confirmation
        if risk > params["max_anomaly_risk"] or anomaly:
            score *= 0.23
            confidence *= 0.5
            signals.append("PATTERN ANOMALY SHIELD: Skor ve güven düştü!")

        # 6. Feedback/auto-tune integration (future; buradan pattern başarısını takip edebilir)
        # self.feedback(trade_result)

        direction = "long" if score > params["pattern_min_score"] else ("short" if score < -params["pattern_min_score"] else "none")
        explanation = (
            f"PatternAgent (ultra): Klasik: {pattern_hits}, ML/Meta: {ml_score:.2f}, "
            f"Toplam skor: {score:.2f}, Güven: {confidence:.2f}, Risk: {risk:.2f}, Sinyaller: {' | '.join(signals)}"
        )
        self._base_output(
            score=score,
            confidence=confidence,
            risk=risk,
            direction=direction,
            type="pattern",
            explanation=explanation,
            anomaly=anomaly,
        )

    # Gelecekte ML/autoedge entegrasyonu için fonksiyon yeri:
    # def autoedge(self, df, patterns, data):
    #     # ML/AI ile yeni pattern/edge tespiti, score döndür
    #     return 0