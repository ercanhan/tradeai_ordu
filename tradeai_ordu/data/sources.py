# data/sources.py

import aiohttp
import pandas as pd

BINANCE_FAPI_BASE = "https://fapi.binance.com"

# Fonksiyonlar (aynı şekilde)

async def fetch_binance_klines(symbol: str, interval: str, limit: int = 150) -> pd.DataFrame:
    url = f"{BINANCE_FAPI_BASE}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=8) as resp:
            klines = await resp.json()
            columns = [
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'num_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ]
            df = pd.DataFrame(klines, columns=columns)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df

async def fetch_binance_orderbook(symbol: str, limit: int = 50) -> dict:
    url = f"{BINANCE_FAPI_BASE}/fapi/v1/depth?symbol={symbol}&limit={limit}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=8) as resp:
            return await resp.json()

async def fetch_binance_funding(symbol: str) -> list:
    url = f"{BINANCE_FAPI_BASE}/fapi/v1/fundingRate?symbol={symbol}&limit=10"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=8) as resp:
            return await resp.json()

async def fetch_binance_oi(symbol: str) -> list:
    url = f"{BINANCE_FAPI_BASE}/futures/data/openInterestHist?symbol={symbol}&period=5m&limit=24"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=8) as resp:
            return await resp.json()

# Placeholder fonksiyonlar (whale, news, social, onchain)

async def fetch_whale_alerts(symbol: str) -> list:
    return []

async def fetch_news_sentiment(symbol: str) -> dict:
    return {}

async def fetch_social_sentiment(symbol: str) -> dict:
    return {}

async def fetch_onchain_activity(symbol: str) -> dict:
    return {}

# BinanceAPI sınıfı (yeni ekleme)

class BinanceAPI:
    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key
        self.api_secret = api_secret

    async def get_usdt_futures_symbols(self):
        url = f"{BINANCE_FAPI_BASE}/fapi/v1/exchangeInfo"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()
                symbols = [s['symbol'] for s in data['symbols'] if s['contractType'] == 'PERPETUAL' and s['quoteAsset'] == 'USDT']
                return symbols

    async def get_klines(self, symbol, interval, limit=150):
        return await fetch_binance_klines(symbol, interval, limit)

    async def get_orderbook(self, symbol, limit=50):
        return await fetch_binance_orderbook(symbol, limit)

    async def get_funding_rates(self, symbol):
        return await fetch_binance_funding(symbol)

    async def get_open_interest(self, symbol):
        return await fetch_binance_oi(symbol)
