
import json
import os
from typing import Dict, List

class DriftDetector:
    def __init__(self, baseline_path: str):
        if os.path.exists(baseline_path):
            with open(baseline_path, 'r', encoding='utf-8') as f:
                self.baseline = json.load(f)
        else:
            self.baseline = None
            print(f"⚠️ Warning: Baseline not found at {baseline_path}")

        self.reset_batch()

    def reset_batch(self):
        self.batch_stats = {
            "n_candidates": 0,
            "skill_depths": {"Mentioned": 0, "Applied": 0, "Architected": 0, "Total": 0},
            "trajectories": {"Ascending": 0, "Stable": 0, "Neutral": 0, "Volatile": 0}
        }

    def add_sample(self, candidate: Dict):
        self.batch_stats["n_candidates"] += 1
        for s in candidate.get("skills_depth", []):
            depth = s.get("depth", "Mentioned")
            self.batch_stats["skill_depths"][depth] += 1
            self.batch_stats["skill_depths"]["Total"] += 1
        
        traj = candidate.get("career_trajectory", "Neutral")
        self.batch_stats["trajectories"][traj] += 1

    def check_drift(self) -> Dict:
        """
        [v2] Compares batch_stats with baseline including Scarcity & Matching.
        """
        if not self.baseline or self.batch_stats["n_candidates"] == 0:
            return {"status": "NO_BASELINE"}

        results = {"status": "HEALTHY", "alerts": []}
        
        # 1. Skill Depth Drift
        total_skills = self.batch_stats["skill_depths"]["Total"]
        if total_skills > 0:
            curr_applied = (self.batch_stats["skill_depths"]["Applied"] / total_skills) * 100
            base_applied = self.baseline.get("skill_depth_pct", {}).get("Applied", 45)
            if curr_applied > base_applied + 10:
                results["status"] = "DRIFT_DETECTED"
                results["alerts"].append(f"Depth Drift: Applied {round(curr_applied, 1)}% vs Base {base_applied}%")
                
        # 2. Scarcity Drift (New in v2)
        # Identify top scarcity skills in Batch
        batch_rare = []
        for node, count in self.batch_stats["skill_depths"].items():
            if node in ["Mentioned", "Applied", "Architected", "Total"]: continue
            if count == 1: # Rare in this batch
                batch_rare.append(node)
        
        # 3. Trajectory Drift
        curr_asc = (self.batch_stats["trajectories"]["Ascending"] / self.batch_stats["n_candidates"]) * 100
        base_asc = self.baseline.get("trajectory_pct", {}).get("Ascending", 5)
        if curr_asc > base_asc + 8:
            results["status"] = "DRIFT_DETECTED"
            results["alerts"].append(f"Trajectory Drift: Ascending {round(curr_asc, 1)}% vs Base {base_asc}%")

        if results["status"] == "DRIFT_DETECTED":
            print(f"🚨 [DRIFT ALERT] {results['alerts']}")
            
        return results

    def check_matching_drift(self, current_top_10: List[str], golden_top_10: List[str]) -> bool:
        """
        [v2] Compares top 10 overlap for stability.
        """
        overlap = set(current_top_10) & set(golden_top_10)
        overlap_rate = len(overlap) / 10
        if overlap_rate < 0.5:
            print(f"⚠️ [MATCHING DRIFT] Overlap dropped to {overlap_rate*100}%")
            return True
        return False
