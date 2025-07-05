from config.config import Config
# core/agent_brain.py

import asyncio
import numpy as np

class AgentBrain:
    """
    Tüm ajanları asenkron şekilde çalıştırır, skor/riskleri birleştirir,
    En uygun pariteleri, işlemleri ve açıklamaları seçer.
    Sistem auto-learn/feedback, log ve telegram/dashboard ile entegre çalışır!
    """

    def __init__(self, agent_classes, data_pipeline, n_best=5):
        self.agent_classes = agent_classes   # [ScalpAgent, MidtermAgent, ...]
        self.data_pipeline = data_pipeline   # Veri akışını sağlayan obje
        self.n_best = n_best                 # En iyi kaç sinyal/parite?
        self.results = []
        self.feedback_db = {}                # Feedback ve log için (Mongo/SQL/Flat)

    async def analyze_symbol(self, symbol, data):
        agents = [cls(data) for cls in self.agent_classes]
        agent_tasks = [asyncio.to_thread(a.analyze) for a in agents]
        await asyncio.gather(*agent_tasks)
        results = [a.result() for a in agents]
        return symbol, results

    async def run(self, symbols):
        all_results = []
        # Her parite için veriyi çek ve tüm ajanlara analiz ettir
        for symbol in symbols:
            data = await self.data_pipeline.get_symbol_data(symbol)
            symbol, results = await self.analyze_symbol(symbol, data)
            all_results.append((symbol, results))
        # Sonuçları ensemble ile en iyi N pariteyi belirle
        best_signals = self.rank_and_select(all_results)
        self.results = best_signals
        return best_signals

    def rank_and_select(self, all_results):
        """
        Ensemble scoring — tüm ajanların skor/risk/edge’lerini birleştir,
        Yalnızca konsensüs yüksek, risk düşük, anomaly shield’ı geçenleri öner!
        """
        scored = []
        for symbol, results in all_results:
            long_score = sum(r["score"] for r in results if r["direction"] == "long" and r["confidence"] > 0.4 and not r["anomaly"])
            short_score = sum(r["score"] for r in results if r["direction"] == "short" and r["confidence"] > 0.4 and not r["anomaly"])
            total_risk = np.mean([r["risk"] for r in results])
            n_confirm = sum(1 for r in results if r["direction"] in ["long", "short"] and abs(r["score"]) > 0.2 and not r["anomaly"])
            signal_type = "long" if long_score > abs(short_score) and long_score > 0.7 else "short" if short_score > abs(long_score) and short_score < -0.7 else "none"
            # Sadece konsensüs ve düşük riskli sinyalleri seç
            if signal_type != "none" and n_confirm >= 3 and total_risk < 0.3:
                explanation = " | ".join([f"{r['agent_name']}({r['direction']}:{r['score']:.2f})" for r in results if r["direction"] == signal_type])
                scored.append({
                    "symbol": symbol,
                    "score": long_score if signal_type == "long" else short_score,
                    "risk": total_risk,
                    "direction": signal_type,
                    "n_confirm": n_confirm,
                    "explanation": explanation,
                })
        # En yüksek skora ve konsensüse göre sırala
        scored.sort(key=lambda x: (x["n_confirm"], abs(x["score"]), -x["risk"]), reverse=True)
        return scored[:self.n_best]

    def save_feedback(self, symbol, feedback):
        # Her sinyal sonrası feedback/sonuç logu — auto-learn için!
        self.feedback_db.setdefault(symbol, []).append(feedback)