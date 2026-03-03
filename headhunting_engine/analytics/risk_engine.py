
import json
import math
from typing import List, Dict, Set

class JDRiskEngine:
    def __init__(self, scarcity_engine, pool_v13_path: str):
        self.scarcity_engine = scarcity_engine
        with open(pool_v13_path, 'r', encoding='utf-8') as f:
            self.pool = json.load(f)

    def predict_risk(self, must: List[str], nice: List[str] = None, seniority: str = "Middle") -> Dict:
        """
        [v4.2.1] Consistent Mathematical Validation & White-box Engine
        Difficulty = (1 - Avg_Must_Coverage_Relevant)*0.4 + Scarcity_Index*0.3 + (1 - Elite_Density)*0.3
        Success Rate = Elite_Density
        """
        if not must: return {"error": "Must-have skills required"}
        
        # 1. Relevant Pool Definition (Unity Foundation)
        # Relevant Pool = Candidates with Must Coverage >= 0.5 AND Base Talent >= 40
        relevant_pool = []
        coverage_ratios = []
        for c in self.pool:
            cand_skills = {s["name"] for s in c.get("skills_depth", [])}
            matched = [node for node in must if node in cand_skills]
            ratio = len(matched) / len(must)
            if ratio >= 0.5 and c.get("base_talent_score", 50) >= 40:
                relevant_pool.append(c)
                coverage_ratios.append(ratio)
        
        n_relevant = len(relevant_pool)
        if n_relevant == 0:
            return {
                "forecast": {"difficulty_level": "Impossible (Extreme Risk)", "difficulty_score": 1.0, "success_probability": 0.0, "expected_sourcing_weeks": 12, "salary_pressure_index": "Critical"},
                "transparency_layer": {"relevant_pool_size": 0, "elite_matched_count": 0, "avg_must_coverage": 0, "scarcity_index": 1.0, "elite_density": 0, "consistency_alerts": ["❌ [CRITICAL] No relevant candidates in pool."]}
            }

        avg_coverage_relevant = sum(coverage_ratios) / n_relevant
        
        # 2. Scarcity Index (v3 Depth-Weighted)
        avg_scarcity = self.scarcity_engine.calculate_jd_scarcity(must)
        
        # 3. Elite Density (Standard matching filter)
        # Low coverage threshold (0.5) to account for small 'must' sets in specialized roles
        elite_matched = []
        for c in relevant_pool:
            if c.get("career_path_grade") in ["S", "A"]:
                cand_skills = {s["name"] for s in c.get("skills_depth", [])}
                matched = [node for node in must if node in cand_skills]
                if len(matched) / len(must) >= 0.5:
                    elite_matched.append(c)
        
        elite_density = len(elite_matched) / n_relevant
        
        # 4. Difficulty Formula (v4.2.1 Unified)
        diff_val = ((1.0 - avg_coverage_relevant) * 0.4) + (avg_scarcity * 0.3) + ((1.0 - elite_density) * 0.3)
        diff_val = max(0.0, min(1.0, diff_val))
        
        # Mapping to Labels (Standardized)
        if diff_val > 0.75: level = "Very Hard (Critical Risk)"
        elif diff_val > 0.55: level = "Hard"
        elif diff_val > 0.35: level = "Moderate-Hard"
        else: level = "Easy"

        # 5. Success Rate (v4.2.1 Unified)
        success_rate = elite_density
        
        # 6. Consistency Guard
        alerts = []
        if success_rate > 0.5 and diff_val > 0.75:
            alerts.append("❌ [CONSISTENCY ERROR] Success Rate > 50% but Difficulty > 0.75 detected.")
        if n_relevant < 5 and success_rate > 0.6:
            alerts.append("⚠️ [SIGNAL BIAS] Small relevant pool size may inflate success rate.")

        # 7. Sourcing Weeks
        base_weeks_map = {"Junior": 3, "Middle": 5, "Senior": 7}
        base_weeks = base_weeks_map.get(seniority, 5)
        sourcing_weeks = int(base_weeks * (1 + avg_scarcity))

        return {
            "forecast": {
                "difficulty_level": level,
                "difficulty_score": round(diff_val, 4),
                "success_probability": round(success_rate, 2),
                "expected_sourcing_weeks": sourcing_weeks,
                "salary_pressure_index": "High" if avg_scarcity > 0.6 else "Moderate"
            },
            "transparency_layer": {
                "relevant_pool_size": n_relevant,
                "elite_matched_count": len(elite_matched),
                "elite_density": round(elite_density, 4),
                "avg_must_coverage": round(avg_coverage_relevant, 4),
                "scarcity_index": round(avg_scarcity, 4),
                "consistency_alerts": alerts
            }
        }
