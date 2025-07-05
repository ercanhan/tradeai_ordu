# core/orchestrator.py

import asyncio
from core.data_pipeline import DataPipeline
from core.agent_pool import AgentPool
from core.meta_decision_engine import MetaDecisionEngine
from core.strategy_manager import StrategyManager
from core.self_learning import update_agent_stats, get_agent_weights, update_meta_weights
from core.reporting import send_report, log_decision

class Orchestrator:
    """
    Tüm AI Trading Ordu pipeline’ını yönetir.
    (Veri toplama -> ajan analizi -> meta karar -> strateji -> self-learning -> raporlama)
    """

    def __init__(self, symbols, interval="15m",
                 pipeline=None, agent_pool=None,
                 decision_engine=None, strategy_manager=None):
        self.symbols = symbols
        self.interval = interval
        self.data_pipeline = pipeline if pipeline is not None else DataPipeline(symbols, interval)
        self.agent_pool = agent_pool if agent_pool is not None else AgentPool()
        self.meta_engine = decision_engine if decision_engine is not None else MetaDecisionEngine()
        self.strategy_manager = strategy_manager if strategy_manager is not None else StrategyManager()

    async def run_once(self):
        """
        Tek bir döngüde tüm pipeline’ı çalıştırır.
        """
        print(">> Veri çekiliyor...")
        batch_data_list = await self.data_pipeline.batch_fetch()
        batch_data = {d["symbol"]: d for d in batch_data_list if d is not None}

        print(">> Ajan analizleri başlatıldı...")
        agent_results = {}
        for symbol, data in batch_data.items():
            results = await self.agent_pool.analyze_symbol(data)
            agent_results[symbol] = results

        print(">> Nihai karar ve strateji belirleniyor...")
        all_decisions = {}
        for symbol, results in agent_results.items():
            final_decision = self.meta_engine.decide(symbol, results)

            strategy_type = final_decision["strategy"].get("strategy", "hybrid")
            direction = final_decision.get("direction", "none")
            edge_strength = final_decision.get("edge_strength", 0.0)
            safe, risk_explanation = self.strategy_manager.filter_risk(results, edge_strength)

            position_info = self.strategy_manager.suggest_position(symbol, strategy_type, direction, results, edge_strength)
            final_decision["strategy"] = position_info
            final_decision["safe"] = safe
            final_decision["risk_explanation"] = risk_explanation

            all_decisions[symbol] = final_decision

        best_scalp = self._select_best(all_decisions, "scalp", n=5)
        best_midterm = self._select_best(all_decisions, "midterm", n=5)

        for dec in best_scalp + best_midterm:
            await send_report(dec)
            log_decision(dec)
            update_agent_stats(dec)
            update_meta_weights(dec)

        print(f">> {len(best_scalp) + len(best_midterm)} karar bildirildi.")

    async def run_forever(self, delay_sec=60):
        while True:
            try:
                await self.run_once()
            except Exception as ex:
                print(f"[Orchestrator] Kritik hata: {ex}")
            await asyncio.sleep(delay_sec)

    def _select_best(self, all_decisions, strategy_type, n=5):
        filtered = [
            dec for dec in all_decisions.values()
            if dec["strategy"]["strategy"] == strategy_type and dec["direction"] != "none" and dec["safe"]
        ]
        best = sorted(filtered, key=lambda d: abs(d["edge_strength"]), reverse=True)[:n]
        return best
