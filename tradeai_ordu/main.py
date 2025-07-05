import asyncio
from core.data_pipeline import DataPipeline
from core.agent_pool import AgentPool
from core.meta_decision_engine import MetaDecisionEngine
from core.strategy_manager import StrategyManager
from core.self_learning import update_agent_stats, get_agent_weights, update_meta_weights
from core.reporting import send_report, log_decision
from core.orchestrator import Orchestrator
from config.config import Config

async def main():
    # 1. Exchange API bağlantısı ve sembollerin çekilmesi
    from data.sources import BinanceAPI
    exchange = BinanceAPI(
        api_key=Config.BINANCE_API_KEY,
        api_secret=Config.BINANCE_API_SECRET
    )

    print(">> Binance USDT vadeli pariteleri çekiliyor...")
    symbols = await exchange.get_usdt_futures_symbols()
    print(f">> Toplam {len(symbols)} parite alındı.")

    # 2. Data pipeline (REST+WebSocket destekli), agent pool, karar motoru, strateji yöneticisi oluşturuluyor
    pipeline = DataPipeline(symbols)
    await pipeline.start_websockets()  # WebSocket clientları başlat

    agent_pool = AgentPool()
    decision_engine = MetaDecisionEngine()
    strategy_manager = StrategyManager()

    # 3. Orchestrator oluşturuluyor
    orchestrator = Orchestrator(
        symbols=symbols,
        pipeline=pipeline,
        agent_pool=agent_pool,
        decision_engine=decision_engine,
        strategy_manager=strategy_manager,
    )

    print(">> Sistem hazır. Sonsuz analiz döngüsü başlıyor...")

    try:
        while True:
            try:
                # 4. Tüm pariteler için tek seferde veri çek, analiz et, karar ver
                results = await orchestrator.run_once()

                # 5. Sonuçları raporla, logla, öğrenme modüllerini çalıştır
                for symbol, final_decision in results.items():
                    await send_report(final_decision)
                    log_decision(final_decision)
                    update_agent_stats(final_decision)
                    update_meta_weights(final_decision)

                # 6. Dinamik olarak ajan ağırlıklarını güncelle
                weights = get_agent_weights()

                print(f">> Döngü tamamlandı. {len(results)} parite işlendi.")

            except Exception as e:
                print(f"[ANA DÖNGÜ HATASI]: {e}")

            await asyncio.sleep(Config.ANALYSIS_INTERVAL)

    except asyncio.CancelledError:
        print(">> Sistem durduruldu, websocket bağlantıları kapanıyor...")

    finally:
        await pipeline.stop_websockets()
        print(">> WebSocket bağlantıları kapatıldı, program sonlandırıldı.")

if __name__ == "__main__":
    asyncio.run(main())
