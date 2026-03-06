from typing import Dict, List, Set, Tuple

class Scorer:
    """
    Calculates deterministic matching scores with full audit logging.
    - Career Trajectory (20%)
    - Context Fit (15%)
    """
    
    DEPTH_WEIGHTS = {
        "Owned": 1.00,
        "Led": 0.85,
        "Applied": 0.65,
        "Assisted": 0.40,
        "Mentioned": 0.20
    }

    # v6.2 Domain Affinity Matrix (2-Hop Weights)
    DOMAIN_AFFINITY = {
        ("AI_ML_RESEARCH", "AI_ENGINEERING"): 0.60,
        ("DATA_ENGINEERING", "AI_ENGINEERING"): 0.55,
        ("CHIP_DESIGN", "AI_ML_RESEARCH"): 0.50,
        ("SW_BACKEND", "INFRA_DEVOPS"): 0.55,
        ("SECURITY_ENGINEERING", "SW_BACKEND"): 0.45,
        ("STRATEGY_MA", "FINANCE_ACCOUNTING"): 0.55,
        ("SW_BACKEND", "SW_FRONTEND"): 0.35,
        ("HRM_HRD", "STRATEGY_MA"): 0.30,
        ("CHIP_DESIGN", "SW_BACKEND"): 0.20
    }

    def __init__(self, version_manager=None):
        self.version_manager = version_manager

    def get_hop_weight(self, domain_a: str, domain_b: str, hop: int) -> float:
        if hop == 0: return 1.0
        if hop == 1: return 0.75 # Default hop1
        
        # hop 2 dynamic lookup
        pair = tuple(sorted([domain_a, domain_b]))
        return self.DOMAIN_AFFINITY.get(pair, 0.40) # Fallback to 0.4 if not in matrix

    def calculate_score(self, candidate_data: Dict, jd_context: Dict) -> Tuple[float, Dict]:
        """
        [v6.2] Precision Matching Engine
        """
        # 1. Pattern Coverage (40%)
        jd_patterns = set(jd_context.get("experience_patterns", []))
        cand_patterns = {p["pattern"]: p.get("depth", "Mentioned") for p in candidate_data.get("patterns", [])}
        
        coverage_score = 0
        if jd_patterns:
            matched = [p for p in jd_patterns if p in cand_patterns]
            coverage_score = (len(matched) / len(jd_patterns)) * 100
        
        # 2. Depth & Impact (25%)
        # Weighted sum of depths for matched patterns
        depth_sum = 0
        if jd_patterns:
            for p in jd_patterns:
                depth = cand_patterns.get(p, "None")
                depth_sum += self.DEPTH_WEIGHTS.get(depth, 0.0)
            avg_depth = depth_sum / len(jd_patterns)
        else:
            avg_depth = 0
            
        # Impact Factor (v6.2)
        impact_multiplier = 1.0
        # If any matched pattern has a quantified impact, bonus
        if any(p.get("impact_type") == "Quantitative" for p in candidate_data.get("patterns", []) if p["pattern"] in jd_patterns):
            impact_multiplier = 1.1

        depth_impact_score = min(100, avg_depth * 100 * impact_multiplier)

        # 3. Career Trajectory (Trajectory Bonus - Independent Multiplier)
        trajectory_quality = candidate_data.get("career_path_quality", {})
        grade = trajectory_quality.get("trajectory_grade", "Neutral")
        path_score = trajectory_quality.get("career_path_score", 50)
        
        # Trajectory now acts as a bonus multiplier (up to 1.2x)
        # instead of a fixed 20% component.
        # 3. Career Trajectory (Trajectory Bonus - v6.2.2 Additive)
        trajectory_quality = candidate_data.get("career_path_quality", {})
        grade = trajectory_quality.get("trajectory_grade", "Neutral")
        
        # v6.2.2 Spec: Ascending +8 / Stable +3 / Neutral 0 / Volatile -3 / Declining -5
        trajectory_bonus = 0.0
        if grade == "Ascending": trajectory_bonus = 8.0
        elif grade == "Stable": trajectory_bonus = 3.0
        elif grade == "Volatile": trajectory_bonus = -3.0
        elif grade == "Declining": trajectory_bonus = -5.0

        # ... (Impact multiplier logic can be preserved or unified)
        # Final Aggregation (v6.2.2: (BaseMatch) + TrajectoryBonus)
        base_match = (
            coverage_score * 0.45 +
            depth_impact_score * 0.30 +
            context_score * 0.25
        )
        
        final_score = min(100.0, base_match + trajectory_bonus)

        return final_score, {
            "final_score": round(final_score, 2),
            "pattern_coverage": round(coverage_score, 2),
            "depth_impact": round(depth_impact_score, 2),
            "trajectory": round(trajectory_score, 2),
            "context_fit": round(context_score, 2)
        }
