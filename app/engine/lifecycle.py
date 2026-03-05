from typing import Dict

class LifecycleEngine:
    def __init__(self, db=None):
        self.db = db
        self.DEFAULT_CONVERSION = 0.09 # 9% standard

    def predict_revenue_probability(self, success_prob: float, role_family: str = None) -> Dict:
        revenue_prob = success_prob * self.DEFAULT_CONVERSION
        return {
            "revenue_probability": round(revenue_prob, 4),
            "revenue_percentage": round(revenue_prob * 100, 2),
            "is_high_yield": revenue_prob > 0.05
        }
