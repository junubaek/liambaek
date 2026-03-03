import math
from typing import List, Dict

class DifficultyEngine:
    """
    [v1.1] Calculates JD Difficulty based on both Coverage and Scarcity.
    Integrated Formula: diff = (1 - avg_coverage) * 0.6 + jd_scarcity * 0.4
    """
    @classmethod
    def calculate_difficulty_score(cls, avg_coverage: float, jd_scarcity: float) -> float:
        return (1.0 - avg_coverage) * 0.6 + jd_scarcity * 0.4

    @classmethod
    def get_difficulty_factor(cls, score: float) -> float:
        """
        [v1.3.1] Map difficulty score to shift factor for Sigmoid RPL.
        """
        if score < 0.2: return 0.0      # Easy
        elif score < 0.4: return 0.3    # Moderate
        elif score < 0.6: return 0.6    # Hard
        else: return 1.0                # Very Hard

class RPLEngine:
    """
    [v1.3.1] Calculates Resume Passing Likelihood (RPL) using Difficulty-Shifted Sigmoid.
    """
    def calculate_rpl(self, score: float, mean_score: float, std_score: float, difficulty_score: float) -> float:
        """
        [v1.3.1] z = (score - mean) / std
        AdjustedRPL = Sigmoid(z - difficulty_factor)
        """
        z = (score - mean_score) / std_score if std_score != 0 else 0
        
        # Difficulty Factor from score
        diff_factor = DifficultyEngine.get_difficulty_factor(difficulty_score)
        
        # Shifted Sigmoid
        z_adj = z - diff_factor
        rpl = 1.0 / (1.0 + math.exp(-z_adj))
        
        return round(rpl, 4)
