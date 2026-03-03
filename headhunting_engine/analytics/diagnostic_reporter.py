import json
from typing import List, Dict
import statistics

class DiagnosticReporter:
    """
    Generates system-wide statistical insights for the Headhunting Engine.
    Used for calibration, inflation detection, and audit validation.
    """
    def __init__(self, scarcity_engine=None):
        self.scarcity_engine = scarcity_engine

    def analyze_candidate_pool(self, candidates: List[Dict]) -> Dict:
        """
        1. Pool Distribution Analysis
        """
        base_scores = [c.get("base_talent_score", 0) for c in candidates]
        
        grades = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
        for s in base_scores:
            if s >= 90: grades["S"] += 1
            elif s >= 80: grades["A"] += 1
            elif s >= 70: grades["B"] += 1
            elif s >= 60: grades["C"] += 1
            else: grades["D"] += 1
            
        return {
            "total_candidates": len(candidates),
            "avg_base_score": round(statistics.mean(base_scores), 2) if base_scores else 0,
            "median_base_score": round(statistics.median(base_scores), 2) if base_scores else 0,
            "grade_distribution": grades
        }

    def analyze_matching_run(self, run_results: Dict, candidates: List[Dict]) -> Dict:
        """
        2. Matching Score & RPL Distribution (JD specific)
        """
        top_candidates = run_results.get("top_candidates", [])
        audit = run_results.get("audit_trail", {})
        
        scores = [r["score"] for r in top_candidates if r["score"] > 0]
        rpls = [r.get("rpl", 0) for r in top_candidates if r["score"] > 0]
        
        # 3. Must Coverage Histogram (Calculated from all candidates passed prefilter)
        # Assuming we have access to all_scored_results in run_results for debug
        all_scored = run_results.get("debug_all_scored", [])
        histogram = {"0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
        
        for res in all_scored:
            cov = res.get("must_coverage", 0)
            if cov < 0.2: histogram["0-0.2"] += 1
            elif cov < 0.4: histogram["0.2-0.4"] += 1
            elif cov < 0.6: histogram["0.4-0.6"] += 1
            elif cov < 0.8: histogram["0.6-0.8"] += 1
            else: histogram["0.8-1.0"] += 1
            
        # [v1.2] Market Reality Index (Unrealistic JD Flag)
        pass_rate = len(scores) / (audit.get("pool_size", 1)) * 100
        unrealistic_flag = False
        if run_results.get("scarcity_index", 0) > 0.75 and pass_rate < 5.0:
            unrealistic_flag = True

        return {
            "pool_size": audit.get("pool_size", 0),
            "prefilter_passed": audit.get("prefilter_passed", 0),
            "hard_filter_passed": audit.get("hard_filter_passed", 0),
            "pass_rate_pct": round(pass_rate, 2),
            "avg_matching_score": round(statistics.mean(scores), 2) if scores else 0,
            "top_score": max(scores) if scores else 0,
            "must_coverage_histogram": histogram,
            "rpl_stats": {
                "avg_rpl": round(statistics.mean(rpls), 2) if rpls else 0,
                "median_rpl": round(statistics.median(rpls), 2) if rpls else 0,
                "above_0.7": len([r for r in rpls if r >= 0.7]),
                "above_0.8": len([r for r in rpls if r >= 0.8])
            },
            "jd_scarcity": run_results.get("scarcity_index", 0),
            "market_reality": {
                "unrealistic_jd": unrealistic_flag,
                "reason": "Extreme scarcity + Low pass rate" if unrealistic_flag else "Normal"
            }
        }

    def identify_failure_cases(self, run_results: Dict, candidates: List[Dict]) -> Dict:
        """
        6. Failure Case Analysis
        - Must Coverage 0.4 - 0.6 (Critical rejection)
        - High Base Score but Hard Filter Fail
        - High Scarcity + Low RPL
        """
        all_scored = run_results.get("debug_all_scored", [])
        candidate_map = {c["id"]: c for c in candidates}
        
        failures = {
            "hard_filter_rejection": [], # Cov 0.4-0.6
            "high_talent_low_match": [], # Base Score > 80, Match < 40
            "extreme_scarcity_low_rpl": [] # Scarcity > 0.8, RPL < 0.3
        }
        
        for res in all_scored:
            c_id = res["candidate_id"]
            cand = candidate_map.get(c_id, {})
            cov = res.get("must_coverage", 0)
            score = res.get("score", 0)
            
            # Case 1: Rejection boundary
            if 0.4 <= cov < 0.6:
                failures["hard_filter_rejection"].append({"id": c_id, "coverage": cov})
            
            # Case 2: Talent/Match mismatch
            if cand.get("base_talent_score", 0) > 80 and score < 40:
                failures["high_talent_low_match"].append({"id": c_id, "base_score": cand["base_talent_score"], "match_score": score})
                
        # Filter out empty categories for cleaner reporting
        return {k: v[:3] for k, v in failures.items() if v}
    def get_scarcity_snapshot(self) -> Dict:
        """
        5. Scarcity Snapshot
        """
        if not self.scarcity_engine:
            return {}
            
        freqs = self.scarcity_engine.skill_frequency
        sorted_freqs = sorted(freqs.items(), key=lambda x: x[1])
        
        return {
            "top_10_most_scarce_skills": [
                {"skill": k, "frequency": round(v, 4)} for k, v in sorted_freqs[:10]
            ],
            "top_10_most_common_skills": [
                {"skill": k, "frequency": round(v, 4)} for k, v in sorted_freqs[-10:][::-1]
            ]
        }
