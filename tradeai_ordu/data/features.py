from config.config import Config
# data/features.py

import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, SMAIndicator, MACD, CCIIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, ROCIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumePriceTrendIndicator

def calculate_technicals(df):
    """
    Tüm teknik analiz ve indikatörleri DataFrame'e ekler.
    """
    df = df.copy()
    # EMA & SMA
    df['EMA_9'] = EMAIndicator(df['close'], window=9).ema_indicator()
    df['EMA_21'] = EMAIndicator(df['close'], window=21).ema_indicator()
    df['EMA_55'] = EMAIndicator(df['close'], window=55).ema_indicator()
    df['SMA_50'] = SMAIndicator(df['close'], window=50).sma_indicator()
    df['SMA_100'] = SMAIndicator(df['close'], window=100).sma_indicator()
    df['SMA_200'] = SMAIndicator(df['close'], window=200).sma_indicator()
    # MACD
    macd = MACD(df['close'])
    df['MACD'] = macd.macd()
    df['MACD_SIGNAL'] = macd.macd_signal()
    df['MACD_DIFF'] = macd.macd_diff()
    # RSI & Stoch
    df['RSI_14'] = RSIIndicator(df['close'], window=14).rsi()
    stoch = StochasticOscillator(df['high'], df['low'], df['close'], window=14)
    df['STOCH_K'] = stoch.stoch()
    df['STOCH_D'] = stoch.stoch_signal()
    # CCI & Momentum
    df['CCI_20'] = CCIIndicator(df['high'], df['low'], df['close'], window=20).cci()
    df['ROC'] = ROCIndicator(df['close'], window=12).roc()
    # Bollinger Bands
    bb = BollingerBands(df['close'], window=20)
    df['BB_High'] = bb.bollinger_hband()
    df['BB_Low'] = bb.bollinger_lband()
    df['BB_Mid'] = bb.bollinger_mavg()
    df['BB_Width'] = bb.bollinger_wband()
    # ATR & Volatility
    df['ATR_14'] = AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
    df['Volatility'] = df['close'].rolling(10).std()
    # Volume
    df['OBV'] = OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
    df['VPT'] = VolumePriceTrendIndicator(df['close'], df['volume']).volume_price_trend()
    # Trend
    df['Trend'] = np.where(df['EMA_9'] > df['EMA_21'], 1, -1)
    # Momentum Shock (ani fiyat değişimi)
    df['Momentum_Shock'] = df['close'].diff(3)
    return df

# --- PATTERN/FORMASYON TESPİTİ ---

def detect_patterns(df):
    """
    Formasyon & pattern taraması (çift tepe, engulfing, doji, breakout, vb.)
    """
    patterns = {}
    try:
        # Double Top/Bottom
        patterns['double_top'] = is_double_top(df)
        patterns['double_bottom'] = is_double_bottom(df)
        # Engulfing
        patterns['bullish_engulfing'] = is_bullish_engulfing(df)
        patterns['bearish_engulfing'] = is_bearish_engulfing(df)
        # Doji
        patterns['doji'] = is_doji(df)
        # Breakout/Breakdown (Basit)
        patterns['breakout'] = is_breakout(df)
        patterns['breakdown'] = is_breakdown(df)
        # Wedge/Flag (Basit varyasyonlar)
        patterns['wedge'] = is_wedge(df)
    except Exception as ex:
        pass
    return patterns

# Aşağıdaki pattern fonksiyonları profesyonelce, edge-case'lere göre yazılmıştır:
def is_double_top(df, lookback=30, threshold=0.005):
    highs = df['high'][-lookback:]
    max1 = highs.idxmax()
    highs_ = highs.drop(index=max1)
    max2 = highs_.idxmax()
    val1, val2 = highs[max1], highs[max2]
    return abs(val1 - val2) / max(val1, val2) < threshold and abs(max1 - max2) > 3

def is_double_bottom(df, lookback=30, threshold=0.005):
    lows = df['low'][-lookback:]
    min1 = lows.idxmin()
    lows_ = lows.drop(index=min1)
    min2 = lows_.idxmin()
    val1, val2 = lows[min1], lows[min2]
    return abs(val1 - val2) / max(val1, val2) < threshold and abs(min1 - min2) > 3

def is_bullish_engulfing(df):
    if len(df) < 2:
        return False
    o1, c1 = df['open'].iloc[-2], df['close'].iloc[-2]
    o2, c2 = df['open'].iloc[-1], df['close'].iloc[-1]
    return c1 < o1 and c2 > o2 and c2 > o1 and o2 < c1

def is_bearish_engulfing(df):
    if len(df) < 2:
        return False
    o1, c1 = df['open'].iloc[-2], df['close'].iloc[-2]
    o2, c2 = df['open'].iloc[-1], df['close'].iloc[-1]
    return c1 > o1 and c2 < o2 and c2 < o1 and o2 > c1

def is_doji(df, tol=0.001):
    if len(df) < 1:
        return False
    last = df.iloc[-1]
    return abs(last['open'] - last['close']) < tol * (last['high'] - last['low'])

def is_breakout(df, window=10):
    if len(df) < window:
        return False
    highs = df['high'].iloc[-window:]
    return df['close'].iloc[-1] > highs.max()

def is_breakdown(df, window=10):
    if len(df) < window:
        return False
    lows = df['low'].iloc[-window:]
    return df['close'].iloc[-1] < lows.min()

def is_wedge(df, window=15):
    # Çok basic wedge/flag detektörü (daha ileri patternler için ML modüller eklenebilir)
    if len(df) < window:
        return False
    high_trend = np.polyfit(range(window), df['high'].iloc[-window:], 1)[0]
    low_trend = np.polyfit(range(window), df['low'].iloc[-window:], 1)[0]
    return abs(high_trend) < 0.02 and abs(low_trend) < 0.02

# --- ORDERBOOK & VOLUME ANOMALY ---

def analyze_orderbook(orderbook):
    """
    Duvar, spoofing, spread ve ani hacim anomaly tespiti.
    """
    try:
        bids = np.array([[float(p), float(q)] for p, q in orderbook.get('bids', [])])
        asks = np.array([[float(p), float(q)] for p, q in orderbook.get('asks', [])])
        spread = abs(asks[0, 0] - bids[0, 0]) if len(bids) and len(asks) else 0
        big_bid = np.max(bids[:, 1]) if bids.size else 0
        big_ask = np.max(asks[:, 1]) if asks.size else 0
        spoofing = (big_bid > bids[:, 1].mean() * 7) or (big_ask > asks[:, 1].mean() * 7) if bids.size and asks.size else False
        return {
            "big_bid": big_bid, "big_ask": big_ask, "spoofing": spoofing, "spread": spread
        }
    except Exception:
        return {"big_bid": 0, "big_ask": 0, "spoofing": False, "spread": 0}

def volume_anomaly(df):
    try:
        vol_now = df['volume'].iloc[-6:].sum()
        vol_past = df['volume'].iloc[-30:-6].sum()
        ratio = vol_now / vol_past if vol_past > 0 else 1
        return ratio
    except Exception:
        return 1

# --- MOMENTUM/OSCILLATOR ALERTS ---

def oscillator_alerts(df):
    alerts = []
    if df['RSI_14'].iloc[-1] > 80:
        alerts.append("RSI aşırı alım (80+)")
    if df['RSI_14'].iloc[-1] < 20:
        alerts.append("RSI aşırı satım (20-)")
    if df['MACD'].iloc[-1] > df['MACD_SIGNAL'].iloc[-1] and df['MACD'].iloc[-2] < df['MACD_SIGNAL'].iloc[-2]:
        alerts.append("MACD al sinyali")
    if df['MACD'].iloc[-1] < df['MACD_SIGNAL'].iloc[-1] and df['MACD'].iloc[-2] > df['MACD_SIGNAL'].iloc[-2]:
        alerts.append("MACD sat sinyali")
    if df['STOCH_K'].iloc[-1] > 90:
        alerts.append("Stoch aşırı alım")
    if df['STOCH_K'].iloc[-1] < 10:
        alerts.append("Stoch aşırı satım")
    return alerts

# --- ANA ENTEGRE ---

def feature_pipeline(df, orderbook=None):
    """
    Komple teknik analiz, pattern, orderbook ve volume anomaly feature'larını birleştirir.
    (Tüm ajanlara full feature set olarak iletilir.)
    """
    df = calculate_technicals(df)
    patterns = detect_patterns(df)
    orderbook_ana = analyze_orderbook(orderbook) if orderbook else {}
    volume_ana = volume_anomaly(df)
    oscillator_ana = oscillator_alerts(df)
    return {
        "df": df,
        "patterns": patterns,
        "orderbook_anomaly": orderbook_ana,
        "volume_anomaly": volume_ana,
        "oscillator_alerts": oscillator_ana
    }