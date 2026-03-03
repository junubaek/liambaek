import json
import os
from typing import List, Dict

# Simulation of v1.2 Scorer
class ScorerV12:
    def calculate_score(self, cand_nodes: set, must_nodes: set, nice_nodes: set, context: dict):
        # Must Coverage
        must_total = len(must_nodes)
        must_matches = cand_nodes & must_nodes
        must_ratio = len(must_matches) / must_total if must_total > 0 else 1.0
        
        # Nice Coverage
        nice_total = len(nice_nodes)
        nice_matches = cand_nodes & nice_nodes
        nice_ratio = len(nice_matches) / nice_total if nice_total > 0 else 1.0
        
        core_match = (must_ratio * 40.0 + nice_ratio * 20.0) / 60.0
        
        # Talent Score (v1.2 was impression based, often high)
        talent_raw = context.get("raw_base_talent_score", 65.0) # Using raw as proxy
        quality_factor = ((talent_raw / 100.0) * 20.0 + 5 + 5 + 3) / 30.0 # Assumed matches
        
        final_score = core_match * (60.0 + (quality_factor ** 1.5) * 40.0)
        return final_score

def run_matching_sim():
    pool_path = "headhunting_engine/analytics/reparsed_pool_v1.2.json"
    if not os.path.exists(pool_path):
        print("❌ Pool not found.")
        return

    with open(pool_path, 'r', encoding='utf-8') as f:
        pool = json.load(f)

    # Test JD: Backend Engineer with Python, AWS, Docker
    jd_must = {"python", "aws", "docker"}
    jd_nice = {"fastapi", "kubernetes", "redis"}

    from headhunting_engine.matching.scorer import Scorer
    from headhunting_engine.matching.version_manager import VersionManager
    
    # Mocking version manager for v1.3
    class MockVM:
        def get_metadata(self): return {}
    
    scorer_v13 = Scorer(MockVM())
    scorer_v12 = ScorerV12()

    results_v12 = []
    results_v13 = []

    for c in pool:
        # V1.2 Simulation
        cand_nodes = set(c.get("canonical_skill_nodes", []))
        score_v12 = scorer_v12.calculate_score(cand_nodes, jd_must, jd_nice, c)
        results_v12.append({"name": c["name"], "score": score_v12})

        # V1.3 Calculation
        cand_skills = c.get("skills_depth", [])
        score_v13, _ = scorer_v13.calculate_score(cand_skills, jd_must, jd_nice, c)
        results_v13.append({"name": c["name"], "score": score_v13})

    # Sort and Compare
    top_12 = sorted(results_v12, key=lambda x: x["score"], reverse=True)[:10]
    top_13 = sorted(results_v13, key=lambda x: x["score"], reverse=True)[:10]

    names_12 = [x["name"] for x in top_12]
    names_13 = [x["name"] for x in top_13]

    overlap = set(names_12) & set(names_13)
    overlap_pct = len(overlap) / 10 * 100

    report = f"""# 🔄 Mini Matching Simulation: v1.2 vs v1.3
JD: Backend (Must: {jd_must}, Nice: {jd_nice})

## 1. Top 10 Comparison
| Rank | v1.2 (Impression-like) | v1.3 (Quant-Deterministic) | Match? |
| :--- | :--- | :--- | :--- |
"""
    for i in range(10):
        n12 = names_12[i] if i < len(names_12) else "-"
        n13 = names_13[i] if i < len(names_13) else "-"
        match = "✅" if n12 == n13 else "❌"
        # Check if n13 is in names_12 at all
        if n12 != n13 and n13 in names_12:
            match = "⚠️ (Rank Shift)"
        report += f"| {i+1} | {n12} | {n13} | {match} |\n"

    report += f"\n## 2. Overlap Stats\n- **Overlap Rate**: {overlap_pct}%\n"
    report += f"- **Top 10 Overlap**: {len(overlap)}/10 candidates overlap\n"
    
    if overlap_pct < 50:
        report += "\n> [!IMPORTANT]\n> v1.3에서 결과가 크게 변했습니다. 이는 기술 숙련도(Depth)와 정문화된 가점/감점(Penalty)이 변별력을 가졌음을 의미합니다.\n"
    else:
        report += "\n> [!NOTE]\n> 결과가 비교적 안정적입니다. 기존 강점 후보자가 정량 평가에서도 살아남았음을 시사합니다.\n"

    with open("headhunting_engine/analytics/matching_sim_v1.3_report.md", 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("✅ Matching Simulation Complete.")

if __name__ == "__main__":
    run_matching_sim()
