# config/config.py

import os

class Config:
    """Tüm sistem için merkezi ayar, API key, Telegram, parametre ve threshold yönetimi"""

    # DATABASE & CACHE
    MONGODB_URI      = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME    = os.getenv("MONGO_DB_NAME", "tradeai_ordu")
    REDIS_URI        = os.getenv("REDIS_URI", "redis://localhost:6379/0")

    # EXCHANGE/BINANCE
    BINANCE_API_KEY    = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

    # TELEGRAM
    TELEGRAM_BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID", "")

    # GLOBAL SYSTEM PARAMS
    MAX_PARALLEL_SYMBOL  = int(os.getenv("MAX_PARALLEL_SYMBOL", "8"))
    ANALYSIS_INTERVAL    = int(os.getenv("ANALYSIS_INTERVAL", "60"))  # saniye
    AGENT_TIMEOUT_SEC    = int(os.getenv("AGENT_TIMEOUT_SEC", "25"))
    FEEDBACK_AUTOLEARN   = bool(int(os.getenv("FEEDBACK_AUTOLEARN", "1")))
    LOG_LEVEL            = os.getenv("LOG_LEVEL", "INFO")

    # STRATEGY & EDGE
    SCALP_TF             = os.getenv("SCALP_TF", "15m")
    MIDTERM_TF           = os.getenv("MIDTERM_TF", "1h")
    SIGNAL_N_BEST        = int(os.getenv("SIGNAL_N_BEST", "5"))

    # DATA/PIPELINE
    DATA_PARALLEL_LIMIT  = int(os.getenv("DATA_PARALLEL_LIMIT", "8"))

    # PATHS
    LOG_DIR              = os.getenv("LOG_DIR", "./logs")
    MODEL_DIR            = os.getenv("MODEL_DIR", "./models")

    @classmethod
    def as_dict(cls):
        return {k: getattr(cls, k) for k in dir(cls) if k.isupper()}
