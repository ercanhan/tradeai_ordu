from config.config import Config
import asyncio

from agents.scalp_agent import ScalpAgent
from agents.midterm_agent import MidtermAgent
from agents.pattern_agent import PatternAgent
from agents.momentum_agent import MomentumAgent
from agents.orderbook_agent import OrderbookAgent
from agents.volume_agent import VolumeAgent
from agents.whale_agent import WhaleAgent
from agents.dump_pump_agent import DumpPumpAgent
from agents.sentiment_agent import SentimentAgent
from agents.anomaly_discovery_agent import AnomalyDiscoveryAgent

from core.self_learning import get_agent_weights

class AgentPool:
    """
    Bütün ajanları aynı anda, feature-rich veriyle çalıştırıp;
    her biri için skor, edge, risk, confidence ve açıklama üreten paralel motor.
    """

    def __init__(self, agent_list=None):
        self.agent_classes = agent_list or [
            ScalpAgent,
            MidtermAgent,
            PatternAgent,
            MomentumAgent,
            OrderbookAgent,
            VolumeAgent,
            WhaleAgent,
            DumpPumpAgent,
            SentimentAgent,
            AnomalyDiscoveryAgent
        ]
        self.agent_weights = get_agent_weights()

    async def analyze_symbol(self, symbol_data):
        """
        Bir parite için tüm ajanları paralel olarak çalıştırır, skorları toplar.
        """
        # Her agent için async çağrı yapıyoruz
        tasks = [self._run_agent(agent_cls, symbol_data) for agent_cls in self.agent_classes]

        # asyncio.gather hata fırlatan agentleri durdurmaz, onları None ile yakalarız
        results = await asyncio.gather(*tasks, return_exceptions=True)

        filtered_results = []
        for res in results:
            if isinstance(res, Exception):
                # Burada loglama yapabiliriz
                print(f"[AgentPool] Agent hata fırlattı: {res}")
                continue
            if res is not None:
                filtered_results.append(res)

        return filtered_results

    async def _run_agent(self, agent_cls, data):
        try:
            weight = self.agent_weights.get(agent_cls.__name__, 1.0)
            agent = agent_cls(data)
            # Eğer agent analyze async değilse await hata verir
            # Bu durumda agent.analyze() async yap veya buradan sync çağır
            result = await agent.analyze()
            if result is None:
                return None
            result["weight"] = weight
            result["agent_name"] = agent_cls.__name__
            return result
        except Exception as ex:
            print(f"[AgentPool] {agent_cls.__name__} hatası: {ex}")
            return None

    async def analyze_batch(self, batch_symbol_data):
        """
        Çoklu parite datası için batch agent analizi.
        """
        all_results = {}
        # Tip kontrolü
        if not isinstance(batch_symbol_data, dict):
            raise ValueError("batch_symbol_data dict tipinde olmalı")

        for symbol, data in batch_symbol_data.items():
            all_results[symbol] = await self.analyze_symbol(data)
        return all_results
