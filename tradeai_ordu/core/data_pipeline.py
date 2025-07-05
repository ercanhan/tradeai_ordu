import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from config.config import Config
from data.features import calculate_technicals, detect_patterns
from data.sources import (
    fetch_binance_klines, fetch_binance_orderbook, fetch_binance_funding, fetch_binance_oi,
    fetch_whale_alerts, fetch_news_sentiment, fetch_social_sentiment, fetch_onchain_activity
)
from core.binance_ws_client import BinanceWebSocketClient

class DataPipeline:
    def __init__(self, symbols, interval="15m"):
        self.symbols = symbols
        self.interval = interval
        self.semaphore = asyncio.Semaphore(Config.DATA_PARALLEL_LIMIT or 10)
        self.ws_clients = {s: BinanceWebSocketClient(s, interval) for s in symbols}

    async def start_websockets(self, delay=1.5):
        """
        Websocket bağlantılarını aralıklı açar, Binance rate limitini aşmaz.
        """
        for symbol, client in self.ws_clients.items():
            await client.connect()
            print(f"[WebSocket] {symbol} bağlantısı kuruldu.")
            await asyncio.sleep(delay)

    async def stop_websockets(self):
        await asyncio.gather(*(client.close() for client in self.ws_clients.values()))

    async def fetch_symbol_data(self, symbol):
        async with self.semaphore:
            try:
                ws_client = self.ws_clients.get(symbol)
                df = ws_client.get_latest_klines_df() if ws_client else pd.DataFrame()
                orderbook = ws_client.get_latest_orderbook() if ws_client else {"bids": [], "asks": []}

                if df.empty:
                    klines = await fetch_binance_klines(symbol, self.interval, limit=150)
                    df = pd.DataFrame(klines)

                if not orderbook["bids"]:
                    orderbook = await fetch_binance_orderbook(symbol, limit=50)

                df = calculate_technicals(df)
                patterns = detect_patterns(df)

                funding = await fetch_binance_funding(symbol)
                oi = await fetch_binance_oi(symbol)
                whale_events = await fetch_whale_alerts(symbol)
                news_sentiment = await fetch_news_sentiment(symbol)
                social_sentiment = await fetch_social_sentiment(symbol)
                onchain = await fetch_onchain_activity(symbol)

                orderbook_anomaly = self._analyze_orderbook(orderbook)
                volume_anomaly = self._analyze_volume(df)
                time_features = self._time_features(df)

                data = {
                    "symbol": symbol,
                    "interval": self.interval,
                    "timestamp": datetime.utcnow().isoformat(),
                    "klines_df": df,
                    "patterns": patterns,
                    "orderbook": orderbook,
                    "orderbook_anomaly": orderbook_anomaly,
                    "funding": funding,
                    "oi": oi,
                    "volume_anomaly": volume_anomaly,
                    "whale_events": whale_events,
                    "news_sentiment": news_sentiment,
                    "social_sentiment": social_sentiment,
                    "onchain": onchain,
                    "time_features": time_features
                }
                return data
            except Exception as ex:
                print(f"[DataPipeline] {symbol} veri çekim hatası: {ex}")
                return None

    async def batch_fetch(self):
        results = await asyncio.gather(*(self.fetch_symbol_data(s) for s in self.symbols))
        return [r for r in results if r is not None]

    def _analyze_orderbook(self, ob):
        try:
            bids = np.array([[float(p), float(q)] for p, q in ob.get('bids', [])])
            asks = np.array([[float(p), float(q)] for p, q in ob.get('asks', [])])
            if bids.size == 0 or asks.size == 0:
                return {"big_bid": 0, "big_ask": 0, "spoofing": False, "spread": 0}
            spread = abs(asks[0, 0] - bids[0, 0])
            big_bid = np.max(bids[:, 1])
            big_ask = np.max(asks[:, 1])
            spoofing = (big_bid > bids[:, 1].mean() * 7) or (big_ask > asks[:, 1].mean() * 7)
            return {
                "big_bid": big_bid,
                "big_ask": big_ask,
                "spoofing": spoofing,
                "spread": spread
            }
        except Exception:
            return {"big_bid": 0, "big_ask": 0, "spoofing": False, "spread": 0}

    def _analyze_volume(self, df):
        try:
            vol_now = df["volume"].iloc[-6:].sum()
            vol_past = df["volume"].iloc[-30:-6].sum()
            return vol_now / vol_past if vol_past > 0 else 1
        except Exception:
            return 1

    def _time_features(self, df):
        features = {}
        try:
            features["atr"] = df["ATR_14"].iloc[-1] if "ATR_14" in df else np.nan
            features["volatility"] = df["close"].rolling(10).std().iloc[-1]
            features["momentum"] = df["close"].iloc[-1] - df["close"].iloc[-11]
            features["spread_last"] = df["high"].iloc[-1] - df["low"].iloc[-1]
        except Exception:
            features = {"atr": np.nan, "volatility": np.nan, "momentum": 0, "spread_last": 0}
        return features
