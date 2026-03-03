from typing import Dict, List, Set, Tuple

class Scorer:
    """
    Calculates deterministic matching scores with full audit logging.
    Items:
    - Must Coverage (40%)
    - Nice Coverage (20%)
    - Base Talent Score (scaled to 20)
    - Context Fit (scaled to 10)
    """
    def calculate_base_talent_score(self, signals: Dict) -> Tuple[float, Dict]:
        """
        [v1.3.1] Precision Hardened Baseline + Deterministic Adjustment Model
        """
        if not signals: signals = {}
        score = 50.0 # Baseline
        details = {"base_score": 50.0, "penalties": {}, "bonuses": {}}
        
        def g(key, default=0):
            val = signals.get(key)
            return val if val is not None else default

        # 1. Penalties (v1.3.1)
        short_tenure_p = g("short_tenures_count", 0) * 5
        if short_tenure_p > 0:
            score -= short_tenure_p
            details["penalties"]["short_tenures"] = -short_tenure_p
            
        # Low Impact Penalty
        exp = g("total_years_experience", 0)
        impact = g("quantified_impact_count", 0)
        if (exp >= 3 and exp < 10 and impact <= 1) or (exp >= 10 and impact <= 2):
            score -= 5
            details["penalties"]["low_impact"] = -5
            
        if signals.get("unexplained_gap"):
            score -= 5
            details["penalties"]["unexplained_gap"] = -5
            
        # Depth Inflation Penalty (Mentioned ratio > 70%)
        if g("mention_ratio", 0) > 0.7:
            score -= 5
            details["penalties"]["depth_inflation"] = -5
            
        # Career Drift Penalty
        if signals.get("domain_change") and short_tenure_p > 0:
            score -= 5
            details["penalties"]["career_drift"] = -5
        
        # 2. Bonuses
        if signals.get("big_tech_experience"):
            score += 8
            details["bonuses"]["big_tech"] = 8
        if signals.get("architecture_ownership"):
            score += 10
            details["bonuses"]["architecture"] = 10
        if impact >= 3:
            score += 7
            details["bonuses"]["high_impact"] = 7
        if signals.get("responsibility_increase"):
            score += 5
            details["bonuses"]["resp_increase"] = 5
        if signals.get("tier_improvement"):
            score += 5
            details["bonuses"]["tier_up"] = 5
        if signals.get("scope_expansion"): # v1.3.1 New
            score += 5
            details["bonuses"]["scope_expansion"] = 5

        final_score = max(30.0, min(90.0, score)) # Deterministic Clamp
        details["final_raw_score"] = final_score
        return final_score, details

    def calculate_trajectory(self, signals: Dict) -> str:
        """
        [v1.3.1] Tightened Trajectory Logic
        - Ascending: ALL required (Resp++, Scope++, 2yr tenure, Tier stable/up)
        - Volatile: ANY 2 (Short tenures, lateral move, domain drift)
        """
        resp_up = signals.get("responsibility_increase", False)
        scope_up = signals.get("scope_expansion", False)
        tier_up = signals.get("tier_improvement", False)
        short_tenures = signals.get("short_tenures_count", 0)
        long_tenure = short_tenures == 0 # Proxy for 2yr tenure
        
        # Ascending (v1.3.1.2 Adjusted: Majority signal + Long Tenure)
        pos_signal_count = sum([resp_up, scope_up, tier_up])
        if long_tenure and pos_signal_count >= 2:
            return "Ascending"
        
        # Volatile (Wait, user said "Next 2 or more: short tenure, lateral, drift")
        vol_score = 0
        if short_tenures >= 2: vol_score += 1
        if signals.get("lateral_move"): vol_score += 1 # If we extract it later
        if signals.get("domain_change"): vol_score += 1
        
        if vol_score >= 2:
            return "Volatile"
            
        if resp_up or scope_up or tier_up:
            return "Stable"
            
        return "Neutral"

    def dynamic_threshold(self, total_must: int) -> float:
        """
        [v1.1] Implementation of dynamic hard filter thresholds.
        """
        if total_must <= 1:
            return 0.0
        elif total_must == 2:
            return 0.5
        elif total_must == 3:
            return 0.6
        else:
            return 0.7

    def __init__(self, version_manager):
        self.version_manager = version_manager

    def calculate_score(self, candidate_skills: List[Dict], must_nodes: Set[str], nice_nodes: Set[str], context_data: Dict, canonical_ids: Set[str] = None) -> Tuple[float, Dict]:
        """
        Returns (final_score, calculation_log)
        [v1.3] Depth-Weighted Scoring: Mentioned (0.3), Applied (0.7), Architected (1.0).
        """
        depth_weights = {"Mentioned": 0.3, "Applied": 0.7, "Architected": 1.0}
        
        # 1. Map Candidate Skills with Depth
        norm_skill_map = {}
        for item in candidate_skills:
            name = item.get("name")
            depth = item.get("depth", "Mentioned")
            weight = depth_weights.get(depth, 0.3)
            
            # If item is already normalized or name is in canonical_ids, use it
            if canonical_ids and name in canonical_ids:
                norm_skill_map[name] = weight
            else:
                norm_skill_map[name] = weight

        # 2. Must Coverage (Weighted)
        must_total = len(must_nodes)
        if must_total == 0:
            must_coverage_score = 1.0
        else:
            weighted_match_sum = 0.0
            for node in must_nodes:
                if node in norm_skill_map:
                    weighted_match_sum += norm_skill_map[node]
            must_coverage_score = weighted_match_sum / must_total
            
        # Hard Filter (Simple ratio for threshold check)
        matched_keys = set(norm_skill_map.keys()) & must_nodes
        simple_match_ratio = len(matched_keys) / must_total if must_total > 0 else 1.0
        threshold = self.dynamic_threshold(must_total)
        
        if simple_match_ratio < threshold:
            return 0.0, {"status": "FAILED_HARD_FILTER", "ratio": simple_match_ratio, "threshold": threshold}

        # 3. Nice Coverage (Weighted)
        nice_total = len(nice_nodes)
        nice_coverage_score = 1.0
        if nice_total > 0:
            weighted_nice_sum = 0.0
            for node in nice_nodes:
                if node in norm_skill_map:
                    weighted_nice_sum += norm_skill_map[node]
            nice_coverage_score = weighted_nice_sum / nice_total

        # 4. Final Aggregation (v1.3)
        core_match_score = (must_coverage_score * 40.0 + nice_coverage_score * 20.0) / 60.0
        
        talent_score_raw = context_data.get("base_talent_score", 50)
        
        domain_match = 5.0 if context_data.get("domain_match") else 0.0
        size_match = 5.0 if context_data.get("company_size_match") else 0.0
        
        trajectory = context_data.get("career_trajectory", "Neutral")
        trajectory_score = 1.0
        if trajectory == "Ascending": trajectory_score = 5.0
        elif trajectory == "Stable": trajectory_score = 3.0
        
        quality_factor = ((talent_score_raw / 100.0) * 20.0 + domain_match + size_match + trajectory_score) / 30.0
        final_score = core_match_score * (60.0 + (quality_factor ** 1.5) * 40.0)
        
        return final_score, {
            "final_score": round(final_score, 2),
            "must_coverage_weighted": round(must_coverage_score, 2),
            "quality_factor": round(quality_factor, 4),
            "talent_score_raw": talent_score_raw,
            "dynamic_threshold_used": threshold
        }
