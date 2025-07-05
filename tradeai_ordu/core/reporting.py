# core/reporting.py

import requests
from config.config import Config
import json
from datetime import datetime
import os

def format_report(final_decision):
    """
    Meta decision + strateji önerisi breakdown'unu insan gibi okunur şekilde raporlar.
    """
    symbol = final_decision.get("symbol", "-")
    direction = final_decision.get("direction", "-")
    strategy = final_decision.get("strategy", {})
    edge_strength = final_decision.get("edge_strength", 0.0)
    safe = final_decision.get("safe", False)
    reason = final_decision.get("reason", "-")
    risk_explanation = final_decision.get("risk_explanation", "")
    strat = strategy if isinstance(strategy, dict) else {}

    summary = "**[AI ORDU SİNYALİ]**\n"
    summary += f"Parite: {symbol}\n"
    summary += f"Yön: {direction.upper()} | Strateji: {strat.get('strategy', '-').upper()} | "
    summary += f"Pozisyon Boyutu: {strat.get('size', 0):.2f}\n"
    summary += f"Stop: {strat.get('stop', 0):.4f} | Kar-Al: {strat.get('take_profit', 0):.4f}\n"
    summary += f"Edge Gücü: {edge_strength:.2f} | Güvenli mi: {'✅' if safe else '❌'}\n\n"
    summary += f"Sebep/Özet:\n{reason}\n"
    if risk_explanation:
        summary += f"\nRisk: {risk_explanation}\n"

    # Agent breakdown
    summary += "\n--- Agent Analizleri ---\n"
    for agent in final_decision.get("details", [])[:7]:  # İlk 7 ajanı göster
        name = agent.get("agent_name", "Agent")
        score = agent.get("score", 0)
        explanation = agent.get("explanation", "")
        summary += f"▶️ {name}: {score:+.2f} | {explanation}\n"

    return summary

def send_report(final_decision):
    """
    Raporu Telegram'a yollar, panel/log için de döner.
    """
    msg = format_report(final_decision)
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": Config.TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=data, timeout=8)
        if response.status_code != 200:
            print(f"[Reporting] Telegram error: {response.text}")
    except Exception as ex:
        print(f"[Reporting] Telegram hatası: {ex}")
    return msg

def log_decision(final_decision, log_path="logs/decisions.log"):
    """
    Kararı log dosyasına JSON satırı olarak ekler.
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        **final_decision
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

# Kullanım örneği:
# msg = send_report(final_decision)
# log_decision(final_decision)
