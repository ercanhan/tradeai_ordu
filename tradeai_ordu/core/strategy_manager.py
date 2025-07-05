# core/strategy_manager.py

import numpy as np

class StrategyManager:
    """
    Pozisyon, risk, stop/kar-al ve tüm strateji yönetimini sağlayan ana motor.
    """

    @staticmethod
    def suggest_position(symbol, strategy_type, direction, agent_results, edge_strength):
        """
        Meta karar sonrası pozisyon büyüklüğü, stop loss, kar al, 
        strateji türü ve açıklamaları üretir.
        """
        atr = StrategyManager._median([a.get("features", {}).get("atr", np.nan) for a in agent_results])
        volatility = StrategyManager._median([a.get("features", {}).get("volatility", np.nan) for a in agent_results])
        pattern_bonus = sum(1 for a in agent_results if "pattern" in a and a["pattern"])
        confidence = np.mean([a.get("confidence", 0.5) for a in agent_results])

        base_risk = 0.015  # Maksimum işlem riski (%1.5)
        position_size = min(1.0, max(0.2, abs(edge_strength) * confidence * (1 + 0.2 * pattern_bonus)))

        # Dump-pump, anomaly varsa pozisyon küçült
        if any(a.get("dump_pump", False) or a.get("anomaly", False) for a in agent_results):
            position_size *= 0.25

        # Volatilite çok yüksekse pozisyon küçült
        if volatility and volatility > 3 * atr:
            position_size *= 0.5

        # Stop loss ve kar al noktaları ATR bazında
        stop_loss = atr * 2 if atr and not np.isnan(atr) else 0.007
        take_profit = stop_loss * (2.2 if strategy_type == "scalp" else 3.0)

        # Yön yoksa pozisyon kapalı
        if direction == "none":
            position_size = 0

        explanation = (
            f"Pozisyon büyüklüğü: {position_size:.2f} | "
            f"Stop: {stop_loss:.4f} | TP: {take_profit:.4f} | "
            f"Edge: {edge_strength:.2f} | Risk: {base_risk:.2%}"
        )

        if strategy_type == "scalp":
            explanation += " | Hızlı kar, düşük pozisyon."
        elif strategy_type == "midterm":
            explanation += " | Orta vade, yüksek potansiyel."

        return {
            "symbol": symbol,
            "strategy": strategy_type,
            "direction": direction,
            "size": position_size,
            "stop": stop_loss,
            "take_profit": take_profit,
            "explanation": explanation,
        }

    @staticmethod
    def filter_risk(agent_results, edge_strength):
        """
        Dump/pump, spoofing, anomaly vb. riskleri kontrol eder,
        pozisyon açılıp açılamayacağına karar verir ve açıklama üretir.
        """
        safe = True
        explanation = ""

        if any(
            a.get("dump_pump", False) or 
            a.get("spoofing", False) or 
            a.get("anomaly", False)
            for a in agent_results
        ):
            safe = False
            explanation += "Dump/pump veya orderbook manipülasyon riski var! | "

        if abs(edge_strength) < 0.2:
            safe = False
            explanation += "Edge zayıf. | "

        if not safe:
            explanation += "Pozisyon açmak önerilmez."

        return safe, explanation

    @staticmethod
    def _median(values):
        """
        None ve NaN değerleri filtreleyip medyan hesaplar.
        """
        filtered = [v for v in values if v is not None and not np.isnan(v)]
        return np.median(filtered) if filtered else np.nan
