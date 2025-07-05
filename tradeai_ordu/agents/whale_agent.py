from config.config import Config
# agents/whale_agent.py

from agents.base_agent import BaseAgent
import numpy as np

class WhaleAgent(BaseAgent):
    """
    En gelişmiş whale/funding/OI/volume/orderbook & meta-anomaly ajanı!
    """

    default_params = {
        "min_funding_delta": 0.00014,
        "min_oi_change": 1.16,
        "min_whale_transfer": 2,
        "min_whale_usdt": 500_000,
        "whale_funding_bonus": 0.24,
        "whale_oi_bonus": 0.18,
        "volume_burst_weight": 0.14,
        "orderbook_wall_penalty": 0.15,
        "pattern_confirm_weight": 0.19,
        "momentum_confirm_weight": 0.13,
        "max_anomaly_risk": 0.21,
        "dump_pump_shield": True,
        "history_boost_window": 10,
        "fakeout_penalty": 0.21,
    }

    def analyze(self):
        d = self.data
        params = self.params
        df = d.get("klines_df")
        whale_events = d.get("whale_events", [])
        whale_usdt = sum(w.get("amount", 0) for w in whale_events) if whale_events else 0
        funding_rates = d.get("funding_rates", [])
        oi_changes = d.get("oi_changes", [])
        volume_anomaly = d.get("volume_anomaly", 1)
        patterns = d.get("patterns", {})
        momentum_score = d.get("momentum_score", 0)
        dump_pump_flag = d.get("dump_pump_flag", False)
        ob_ana = d.get("orderbook_anomaly", {})
        price = df["close"].iloc[-1]
        price_prev = df["close"].iloc[-2]

        confidence = 0.5
        risk = 0
        anomaly = False
        score = 0
        signals = []

        # 1. Whale Transfer + Boyut
        if len(whale_events) >= params["min_whale_transfer"] and whale_usdt > params["min_whale_usdt"]:
            score += params["whale_funding_bonus"]
            confidence += 0.12
            signals.append(f"{len(whale_events)}x whale transfer (toplam {whale_usdt/1e6:.2f}M USDT)")

        # 2. Whale transfer + fiyat hareketi korelasyonu
        if len(whale_events) >= 2:
            if (price > price_prev and whale_usdt > 0) or (price < price_prev and whale_usdt < 0):
                score += 0.17
                signals.append("Whale & fiyat uyumlu hareket: BOOM!")
            else:
                score -= 0.13
                risk += 0.11
                signals.append("Whale-fiyat ters korelasyon (fakeout riski)")

        # 3. Funding rate delta
        funding_delta = float(funding_rates[-1]["fundingRate"]) - float(funding_rates[-2]["fundingRate"]) if len(funding_rates) > 2 else 0
        if funding_delta > params["min_funding_delta"]:
            score += 0.13
            signals.append("Funding rate artışı (long bias)")
        elif funding_delta < -params["min_funding_delta"]:
            score -= 0.13
            signals.append("Funding rate düşüşü (short bias)")

        # 4. OI değişimi
        oi_change = float(oi_changes[-1]) - float(oi_changes[-2]) if len(oi_changes) > 2 else 0
        if oi_change > params["min_oi_change"]:
            score += params["whale_oi_bonus"]
            signals.append("Açık pozisyon (OI) artışı")
        elif oi_change < -params["min_oi_change"]:
            score -= params["whale_oi_bonus"]
            signals.append("Açık pozisyon (OI) düşüşü")

        # 5. Volume Burst
        if volume_anomaly > 1.28:
            score += params["volume_burst_weight"]
            signals.append("Whale hacim burst (spot+vadeli)")

        # 6. Orderbook wall ve manipülasyon
        if ob_ana.get("big_bid", 0) > whale_usdt * 0.9:
            score -= params["orderbook_wall_penalty"]
            risk += 0.12
            signals.append("Orderbook wall (bid) — fake pump riski")
        if ob_ana.get("big_ask", 0) > whale_usdt * 0.9:
            score -= params["orderbook_wall_penalty"]
            risk += 0.12
            signals.append("Orderbook wall (ask) — fake dump riski")
        if ob_ana.get("spoofing", False):
            risk += 0.18
            anomaly = True
            signals.append("Orderbook manipülasyon")

        # 7. Pattern & Momentum onayı
        if patterns.get("breakout") or patterns.get("double_bottom"):
            score += params["pattern_confirm_weight"]
            signals.append("Whale + bullish pattern")
        if momentum_score > 0.4:
            score += params["momentum_confirm_weight"]
            signals.append("Whale + momentum onayı")

        # 8. Dump/Pump/Tuzak & Fakeout Kalkanı
        if params["dump_pump_shield"] and dump_pump_flag:
            score *= 0.18
            risk += 0.17
            anomaly = True
            signals.append("Dump/Pump anomaly shield: Skor ve güven düşürüldü!")
        # Fiyat hareketiyle whale zıt ise yine skor düşsün (fakeout penalty)
        if risk > params["max_anomaly_risk"] or anomaly:
            score *= 0.29
            confidence *= 0.63
            signals.append("WHALE ANOMALY SHIELD: Skor ve güven kırıldı!")

        # 9. Feedback/Auto-tune (son X işlemin başarı ortalamasına göre bonus)
        if hasattr(self, "history") and len(self.history) > params["history_boost_window"]:
            last_wins = [r for r in self.history[-params["history_boost_window"]:] if r.get("direction") == r.get("last_trade_result", "none") and r.get("score", 0) > 0.1]
            if len(last_wins) > 4:
                score += 0.09
                confidence += 0.05
                signals.append("Whale geçmiş başarısı boost")

        # Nihai karar
        direction = "long" if score > 0.45 else ("short" if score < -0.45 else "none")
        explanation = (
            f"WhaleAgent (v2): {', '.join(signals)} | Skor: {score:.2f}, Güven: {confidence:.2f}, Risk: {risk:.2f}"
        )
        self._base_output(
            score=score,
            confidence=confidence,
            risk=risk,
            direction=direction,
            type="whale",
            explanation=explanation,
            anomaly=anomaly,
        )