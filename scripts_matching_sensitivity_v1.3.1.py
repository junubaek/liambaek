
import json
import os
import math
from typing import List, Dict, Set

# Mock components for comparison
class ScorerV12:
    def calculate_score(self, cand_skills, must, nice):
        # Impression-like (simple ratio * multiplier)
        must_match = len(set([s["name"] for s in cand_skills]) & must)
        ratio = must_match / len(must) if must else 1.0
        return ratio * 100.0

class ScorerV131:
    def __init__(self):
        from headhunting_engine.matching.scorer import Scorer
        from headhunting_engine.matching.version_manager import VersionManager
        from headhunting_engine.matching.rpl import RPLEngine, DifficultyEngine
        self.scorer = Scorer(VersionManager("1.3.1"))
        self.rpl_engine = RPLEngine()
        self.diff_engine = DifficultyEngine()

    def run_match(self, candidate, must, nice):
        # Calculate matching score
        # Reparased pool already has basics/quant_signals
        final_score, details = self.scorer.calculate_score(
            candidate["skills_depth"], must, nice, 
            candidate
        )
        return final_score

def run_sensitivity_test():
    pool_path = "headhunting_engine/analytics/reparsed_pool_v1.2.json"
    if not os.path.exists(pool_path):
        print(f"❌ Pool not found at {pool_path}")
        return

    with open(pool_path, 'r', encoding='utf-8') as f:
        pool = json.load(f)

    test_jds = [
        {"name": "Backend", "must": {"Cloud_AWS", "Language_Python", "DB_SQL"}, "nice": {"Language_Java"}},
        {"name": "Embedded", "must": {"Embedded_C", "Infra_Linux", "Language_C_Plus_Plus"}, "nice": {"Language_C"}},
        {"name": "AI Engineering", "must": {"DL_Framework", "MLOps", "Distributed_Training"}, "nice": {"Language_Python"}}
    ]

    v131 = ScorerV131()
    v12 = ScorerV12()

    report = ["# 🎯 Matching Sensitivity Test (v1.3.1 Precision Hardening)"]
    
    for jd in test_jds:
        name = jd["name"]
        must = jd["must"]
        nice = jd["nice"]

        # Run v1.2 Match
        res_v12 = []
        for cand in pool:
            score = v12.calculate_score(cand["skills_depth"], must, nice)
            res_v12.append((cand["id"], score))
        res_v12.sort(key=lambda x: x[1], reverse=True)
        top10_v12 = [x[0] for x in res_v12[:10]]

        # Run v1.3.1 Match
        res_v131 = []
        scores_v131 = []
        for cand in pool:
            score = v131.run_match(cand, must, nice)
            res_v131.append((cand["id"], score))
            if score > 0: scores_v131.append(score)
        
        res_v131.sort(key=lambda x: x[1], reverse=True)
        top10_v131 = [x[0] for x in res_v131[:10]]

        # Analysis
        overlap = set(top10_v12) & set(top10_v131)
        overlap_rate = len(overlap) / 10 * 100

        rank_shifts = []
        for i, cid in enumerate(top10_v131):
            # Find its rank in v1.2
            try:
                v12_rank = next(idx for idx, x in enumerate(res_v12) if x[0] == cid)
                rank_shifts.append(abs(i - v12_rank))
            except:
                rank_shifts.append(10) # Out of top 10

        avg_shift = sum(rank_shifts) / len(rank_shifts) if rank_shifts else 0

        report.append(f"\n## JD: {name}")
        report.append(f"- **Top 10 Overlap**: {len(overlap)}/10 ({overlap_rate}%)")
        report.append(f"- **Avg Rank Shift**: {round(avg_shift, 2)}")
        
        status = "✅ Healthy" if 60 <= overlap_rate <= 80 and 2 <= avg_shift <= 6 else "⚠️ Skew Detected"
        if overlap_rate > 90: status = "⚠️ Too Stable (Hardening not felt)"
        elif overlap_rate < 50: status = "⚠️ High Volatility"
        
        report.append(f"- **Status**: {status}")

    # Save Report
    output_md = "headhunting_engine/analytics/matching_sensitivity_test.md"
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
    
    print(f"✅ Sensitivity Test Complete. Results saved to {output_md}")

if __name__ == "__main__":
    run_sensitivity_test()
