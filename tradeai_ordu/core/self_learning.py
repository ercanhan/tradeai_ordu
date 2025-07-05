# core/self_learning.py

import json
import os
from collections import defaultdict

# Stat dosya yolları
AGENT_STATS_PATH = "logs/agent_stats.json"
META_WEIGHTS_PATH = "logs/meta_weights.json"
AUTOEDGE_PATH = "logs/autoedge_patterns.json"

def load_stats(path):
    """
    JSON formatında kayıtlı istatistikleri yükler.
    Dosya yoksa default yapıyı döner.
    """
    if not os.path.exists(path):
        return defaultdict(lambda: {"success": 0, "fail": 0, "params": {}})
    with open(path, "r") as f:
        return defaultdict(lambda: {"success": 0, "fail": 0, "params": {}}, json.load(f))

def save_stats(path, stats):
    """
    İstatistikleri JSON dosyasına yazar.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(stats, f, indent=2)

def update_agent_stats(final_decision, trade_result=None):
    """
    Trade sonucu veya sinyal bazlı olarak agent başarı/fail sayısını günceller.
    final_decision içindeki her agent'ın skor ve parametrelerini değerlendirir.
    """
    stats = load_stats(AGENT_STATS_PATH)

    for agent in final_decision.get("details", []):
        name = agent.get("agent_name", "UnknownAgent")

        if trade_result:
            win = trade_result.get("win", False)
            score = agent.get("score", 0)
            if win and score > 0:
                stats[name]["success"] += 1
            elif not win and score < 0:
                stats[name]["fail"] += 1
        else:
            # Sinyal bazlı (backtest veya canlı)
            score = agent.get("score", 0)
            if score > 0:
                stats[name]["success"] += 1
            elif score < 0:
                stats[name]["fail"] += 1

        # Parametre güncellemesi
        params = agent.get("params", {})
        if params:
            stats[name]["params"].update(params)

    save_stats(AGENT_STATS_PATH, stats)

def get_agent_weights():
    """
    Agent başarı/fail oranına göre dinamik ağırlık hesaplar.
    Başarısız agent ağırlığı 0.1'in altına düşmez.
    Başarılı agent ağırlığı 3'ü geçmez.
    """
    stats = load_stats(AGENT_STATS_PATH)
    weights = {}

    for name, s in stats.items():
        total = s["success"] + s["fail"]
        if total == 0:
            weights[name] = 1.0
        else:
            w = s["success"] / total
            weights[name] = max(0.1, min(w, 3.0))

    return weights

def update_meta_weights(final_decision):
    """
    Meta kararların başarı durumuna göre ağırlıklarını optimize eder.
    Safe kararların ağırlığı artar, riskli kararların azalır.
    """
    weights = load_stats(META_WEIGHTS_PATH)

    symbol = final_decision.get("symbol", "ALL")
    direction = final_decision.get("direction", "none")
    safe = final_decision.get("safe", False)

    key = f"{symbol}_{direction}"

    if safe:
        weights[key] = weights.get(key, 1.0) + 0.05
    else:
        weights[key] = max(0.1, weights.get(key, 1.0) - 0.05)

    save_stats(META_WEIGHTS_PATH, weights)

def autoedge_discovery(new_pattern):
    """
    Yeni edge veya anomaly patternlerini kaydeder.
    """
    edges = load_stats(AUTOEDGE_PATH)
    pname = new_pattern.get("name") or f"pattern_{len(edges)}"
    edges[pname] = new_pattern
    save_stats(AUTOEDGE_PATH, edges)

def get_autoedges():
    """
    Öğrenilmiş tüm edge/pattern/anomaly setlerini döner.
    """
    return load_stats(AUTOEDGE_PATH)

# Örnek kullanım:
# update_agent_stats(final_decision, trade_result={"profit": 0.012, "win": True})
# weights = get_agent_weights()
# update_meta_weights(final_decision)
# autoedge_discovery({"name": "EMA+VolumeShock", ...})
