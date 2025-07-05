import asyncio
import json
import websockets
import pandas as pd

class BinanceWebSocketClient:
    def __init__(self, symbol, interval="15m"):
        self.symbol = symbol.lower()
        self.interval = interval
        self.ws_kline_url = f"wss://fstream.binance.com/ws/{self.symbol}@kline_{self.interval}"
        self.ws_depth_url = f"wss://fstream.binance.com/ws/{self.symbol}@depth5"
        self.latest_klines = []
        self.latest_orderbook = {"bids": [], "asks": []}
        self._kline_task = None
        self._depth_task = None
        self._running = False

    async def connect(self):
        if self._running:
            return
        self._running = True
        self._kline_task = asyncio.create_task(self._listen_kline())
        self._depth_task = asyncio.create_task(self._listen_depth())

    async def close(self):
        self._running = False
        if self._kline_task:
            self._kline_task.cancel()
            try:
                await self._kline_task
            except asyncio.CancelledError:
                pass
        if self._depth_task:
            self._depth_task.cancel()
            try:
                await self._depth_task
            except asyncio.CancelledError:
                pass

    async def _listen_kline(self):
        while self._running:
            try:
                async with websockets.connect(self.ws_kline_url) as ws:
                    async for message in ws:
                        data = json.loads(message)
                        k = data.get("k", {})
                        if k.get("x"):  # kline closed
                            candle = {
                                "open_time": k["t"],
                                "open": float(k["o"]),
                                "high": float(k["h"]),
                                "low": float(k["l"]),
                                "close": float(k["c"]),
                                "volume": float(k["v"]),
                                "close_time": k["T"],
                                "quote_asset_volume": float(k["q"]),
                                "number_of_trades": k["n"],
                                "taker_buy_base_asset_volume": float(k["V"]),
                                "taker_buy_quote_asset_volume": float(k["Q"]),
                            }
                            self.latest_klines.append(candle)
                            if len(self.latest_klines) > 200:
                                self.latest_klines.pop(0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[WebSocket][{self.symbol}] Kline connection error: {e}")
                await asyncio.sleep(5)

    async def _listen_depth(self):
        while self._running:
            try:
                async with websockets.connect(self.ws_depth_url) as ws:
                    async for message in ws:
                        data = json.loads(message)
                        self.latest_orderbook["bids"] = data.get("b", [])
                        self.latest_orderbook["asks"] = data.get("a", [])
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[WebSocket][{self.symbol}] Depth connection error: {e}")
                await asyncio.sleep(5)

    def get_latest_klines_df(self):
        if not self.latest_klines:
            return pd.DataFrame()
        return pd.DataFrame(self.latest_klines)

    def get_latest_orderbook(self):
        return self.latest_orderbook
