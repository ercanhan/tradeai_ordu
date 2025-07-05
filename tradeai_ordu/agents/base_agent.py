from config.config import Config
# agents/base_agent.py

import json
from core.self_learning import update_agent_stats

class BaseAgent:
    """
    Tüm AI ajanları için profesyonel, dinamik, self-improving, explainable base class.
    """
    # Tüm agent parametreleri ve hyperparameter'lar dinamik olarak ayarlanabilir
    default_params = {}

    def __init__(self, data, params=None):
        self.data = data                  # Pipeline'dan gelen full feature/data dict
        self.params = params or self.default_params.copy()
        self.result_data = {}
        self.history = []                 # Agent'ın geçmiş kararları (feedback için)

    def analyze(self):
        """
        Ana analiz fonksiyonu — child class override eder.
        """
        raise NotImplementedError

    def result(self):
        """
        Analiz sonrası rapor (full explainability ile birlikte).
        """
        out = self.result_data.copy()
        out["agent_name"] = self.__class__.__name__
        out["params"] = self.params
        return out

    def _base_output(self, **kwargs):
        """
        Standart output alanlarını birleştirip geçmiş/log kaydını otomatik tutar.
        """
        self.result_data.update(kwargs)
        # En temel alanlar:
        for key, val in {
            "agent_name": self.__class__.__name__,
            "score": 0,
            "confidence": 0.5,
            "risk": 0,
            "direction": "none",
            "type": "unknown",
            "explanation": "",
            "anomaly": False,
        }.items():
            if key not in self.result_data:
                self.result_data[key] = val
        # Karar geçmişi/log kaydı (feedback ve auto-learning için)
        self.history.append(self.result_data.copy())
        return self.result_data

    def feedback(self, trade_result=None):
        """
        Trade sonrası/karar sonrası kendini güncelleyen feedback fonksiyonu.
        """
        update_agent_stats({"details": [self.result()]}, trade_result=trade_result)
        # Dinamik olarak parametre güncelleyebilir (hyperparam opt/auto-tune)
        self.auto_tune(trade_result)
    
    def auto_tune(self, trade_result):
        """
        Agent kendi parametre/hyperparameter'larını optimize eder.
        """
        # Child class'larda kullanılabilir, burada iskelet olarak bırakıldı.
        pass

    def log_decision(self, log_path=None):
        """
        Kararları dosyaya/MongoDB'ye kaydetmek için (opsiyonel).
        """
        if not log_path:
            return
        with open(log_path, "a") as f:
            f.write(json.dumps(self.result(), ensure_ascii=False) + "\n")