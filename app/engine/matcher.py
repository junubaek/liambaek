from typing import Dict, List, Tuple
import sqlite3
import json

class Scorer:
    """
    [v6.2] Precision Matching Engine - Web Backend Version
    """
    DEPTH_WEIGHTS = {
        "Owned": 1.00,
        "Led": 0.85,
        "Applied": 0.65,
        "Assisted": 0.40,
        "Mentioned": 0.20
    }

    def calculate_score(self, candidate_skills: List[Dict], context_data: Dict, candidate_id: str = None) -> Tuple[float, Dict]:
        # 1. Pattern Coverage (45%)
        jd_patterns = set(context_data.get("experience_patterns", []))
        
        cand_patterns = {}
        # If candidate_id is provided, fetch from analytics.db
        if candidate_id:
            try:
                import sqlite3
                with sqlite3.connect("headhunting_engine/data/analytics.db", timeout=5) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT pattern, depth FROM candidate_patterns WHERE candidate_id = ?", (candidate_id,))
                    rows = cursor.fetchall()
                    if rows:
                        cand_patterns = {r[0]: r[1] for r in rows}
            except Exception as e:
                print(f"Index Fetch Warning: {e}")

        # Fallback to skills list if DB fetch failed or not provided
        if not cand_patterns:
            for item in candidate_skills:
                name = item.get("name") or item.get("pattern")
                depth = item.get("depth", "Mentioned")
                cand_patterns[name] = depth

        coverage_score = 0
        if jd_patterns:
            matched = [p for p in jd_patterns if p in cand_patterns]
            coverage_score = (len(matched) / len(jd_patterns)) * 100
        
        # 2. Depth & Impact (30%)
        depth_sum = 0
        if jd_patterns:
            for p in jd_patterns:
                depth = cand_patterns.get(p, "None")
                depth_sum += self.DEPTH_WEIGHTS.get(depth, 0.0)
            avg_depth = depth_sum / len(jd_patterns)
        else:
            avg_depth = 0
            
        depth_impact_score = min(100, avg_depth * 100)

        # 3. Context Fit (25%)
        # Primary sector match
        cand_sector = context_data.get("primary_sector") or context_data.get("sector")
        target_sector = context_data.get("sector")
        context_score = 100 if cand_sector == target_sector else 50
        
        # 4. Trajectory Bonus (v6.2.2 Additive)
        trajectory_bonus = 0.0
        grade = context_data.get("trajectory_grade", "Neutral")
        if grade == "Ascending": trajectory_bonus = 8.0
        elif grade == "Stable": trajectory_bonus = 3.0
        elif grade == "Volatile": trajectory_bonus = -3.0
        elif grade == "Declining": trajectory_bonus = -5.0

        # Final Aggregation (v6.2.2 Weights: 45/30/25 + TrajectoryBonus)
        if coverage_score <= 0:
            return 0.0, {
                "final_score": 0.0,
                "pattern_coverage": 0.0,
                "depth_impact": 0.0,
                "context_fit": 0.0
            }

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
            "context_fit": round(context_score, 2)
        }
