import json
from typing import List, Dict

class JDRiskEngine:
    def __init__(self, scarcity_engine):
        self.scarcity_engine = scarcity_engine

    def predict_risk(self, domains: List[str], patterns: List[str]) -> Dict:
        """
        [v4 Strategic] Difficulty & Success Probability.
        """
        # Scarcity integration
        avg_scarcity = 0.5
        if patterns:
            # Simplified for universal engine patterns
            avg_scarcity = 0.6 

        scarcity = avg_scarcity
        elite_density = 0.3
        pool_ratio = 0.1
        severity = 0.2

        # Difficulty = 0.35 * Scarcity + 0.25 * (1-EliteDensity) + 0.2 * (1-PoolRatio) + 0.2 * Severity
        difficulty = (scarcity * 0.35) + ((1.0 - elite_density) * 0.25) + ((1.0 - pool_ratio) * 0.20) + (severity * 0.20)
        difficulty = round(min(1.0, difficulty), 2)

        # SuccessProb = 0.4 * EliteDensity + 0.3 * (1-Scarcity) + 0.2 * PoolRatio + 0.1 * Conversion
        conversion_rate = 0.15
        success_prob = (elite_density * 0.4) + ((1.0 - scarcity) * 0.3) + (pool_ratio * 0.2) + (conversion_rate * 0.1)
        success_prob = round(success_prob, 2)

        return {
            "forecast": {
                "difficulty_score": difficulty,
                "success_probability": success_prob,
                "difficulty_level": "Hard" if difficulty > 0.6 else "Moderate"
            },
            "transparency_layer": {
                "scarcity_index": scarcity,
                "elite_density": elite_density,
                "pool_ratio": pool_ratio
            }
        }
