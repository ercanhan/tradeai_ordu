# core/meta_decision_engine.py

from core.strategy_manager import StrategyManager
from core.self_learning import update_meta_weights
from datetime import datetime

class MetaDecisionEngine:
    """
    Tüm ajanlardan gelen skor, risk ve feature’ları 
    dinamik ağırlıklarla birleştirip “nihai karar” ve strateji üreten 
    merkezi beyin.
    """

    def __init__(self):
        self.meta_weights = {}  # Agent ve feature ağırlıkları (feedback ile update edilir)

    def decide(self, symbol, agent_results):
        """
        Bir parite için tüm ajan skorlarını, riskleri, anomaly ve konsensusu tartarak
        yön (long/short/none), scalp/orta vade, pozisyon boyutu, risk ve detaylı açıklama üretir.
        """
        # 1. Tüm skorları ve feature’ları normalize edip dinamik ağırlıklandır
        total_weight = sum(a.get("weight", 1.0) for a in agent_results)
        weighted_scores = [a.get("score", 0) * a.get("weight", 1.0) for a in agent_results]
        risk_alerts = [a for a in agent_results if a.get("risk", 0) > 0.7]
        consensus = self._consensus_score(agent_results)
        edge_strength = sum(weighted_scores) / (total_weight or 1)
        explanations = [a.get("explanation", "") for a in agent_results if a.get("explanation")]
        anomalies = [a for a in agent_results if a.get("anomaly", False)]
        strategy_type = self._detect_strategy_type(agent_results)
        direction = self._decide_direction(agent_results, consensus, edge_strength)

        # Dump-pump veya anomaly riski varsa otomatik koruma
        if any(a.get("dump_pump", False) or a.get("anomaly", False) for a in agent_results):
            direction = "none"
            reason = "Yüksek dump/pump riski veya anomaly tespit edildi. İşlem açma!"
        else:
            reason = self._explanation_block(explanations, agent_results, consensus, edge_strength)

        # 2. Strateji önerisi (pozisyon büyüklüğü, stop/kar-al, scalp/orta vade ayrımı)
        strategy = StrategyManager.suggest_position(symbol, strategy_type, direction, agent_results, edge_strength)

        # 3. Risk filtrelemesi (pozisyon önerisi ve risk uyumu)
        safe, risk_explanation = StrategyManager.filter_risk(agent_results, edge_strength)

        final_decision = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "direction": direction,
            "strategy": strategy,
            "edge_strength": edge_strength,
            "consensus": consensus,
            "safe": safe,
            "reason": reason,
            "risk_explanation": risk_explanation,
            "details": agent_results,
            "anomalies": anomalies,
            "risk_alerts": risk_alerts
        }

        # Self-learning ağırlık güncellemesi
        update_meta_weights(final_decision)

        return final_decision

    def _detect_strategy_type(self, agent_results):
        """
        Agent çıktılarından, ağırlıklı olarak scalp/orta vade/tuzak algısı çıkartır.
        """
        types = [a.get("type", "unknown") for a in agent_results]
        scalp_count = types.count("scalp")
        midterm_count = types.count("midterm")
        if scalp_count > midterm_count:
            return "scalp"
        elif midterm_count > scalp_count:
            return "midterm"
        else:
            return "hybrid"

    def _decide_direction(self, agent_results, consensus, edge_strength):
        """
        Ajan skorları ve konsensus ile yön kararını (long/short/none) verir.
        """
        pos = sum(1 for a in agent_results if a.get("direction") == "long" and a.get("score", 0) > 0)
        neg = sum(1 for a in agent_results if a.get("direction") == "short" and a.get("score", 0) < 0)

        if pos > neg and edge_strength > 0.5 and consensus > 0.65:
            return "long"
        elif neg > pos and edge_strength < -0.5 and consensus > 0.65:
            return "short"
        else:
            return "none"

    def _consensus_score(self, agent_results):
        """
        Tüm ajanlar arasında pozitif/negatif onay derecesini ölçer.
        """
        total = len(agent_results)
        longers = sum(1 for a in agent_results if a.get("direction") == "long")
        shorters = sum(1 for a in agent_results if a.get("direction") == "short")
        return max(longers, shorters) / (total or 1)

    def _explanation_block(self, explanations, agent_results, consensus, edge_strength):
        """
        Açıklamaları ve nedenleri insan gibi özetler.
        """
        base = " | ".join(explanations[:3])  # En güçlü 3 nedeni öne çıkar
        base += f"\nEdge Strength: {edge_strength:.2f}, Consensus: {consensus:.2%}."

        for a in agent_results:
            if a.get("dump_pump", False):
                base += " | Dump/pump tehlikesi!"
            if a.get("spoofing", False):
                base += " | Orderbook manipülasyonu riski!"
            if a.get("whale_transfer", False):
                base += " | Whale hareketi!"

        return base
