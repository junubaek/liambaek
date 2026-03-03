import json
import statistics
import os
from typing import List, Dict

def run_market_fitness_audit(pool_path: str, output_path: str):
    if not os.path.exists(pool_path):
        print(f"❌ Error: Pool file not found at {pool_path}")
        return

    with open(pool_path, 'r', encoding='utf-8') as f:
        pool = json.load(f)

    if not pool:
        print("❌ Error: Pool is empty.")
        return

    # 1. Score Analysis (Raw vs Normalized)
    raw_scores = [c.get("raw_base_talent_score", 50.0) for c in pool]
    norm_scores = [c.get("normalized_talent_score", 50.0) for c in pool]
    
    audit_results = {
        "score_stats": {
            "raw": {
                "mean": round(statistics.mean(raw_scores), 2),
                "std": round(statistics.stdev(raw_scores), 2) if len(raw_scores) > 1 else 0,
                "min": min(raw_scores),
                "max": max(raw_scores)
            },
            "normalized": {
                "mean": round(statistics.mean(norm_scores), 2),
                "std": round(statistics.stdev(norm_scores), 2) if len(norm_scores) > 1 else 0
            }
        },
        "extreme_candidates": {
            "top_5_percent_raw": [],
            "bottom_10_percent_raw": []
        },
        "skill_depth_distribution": {
            "Mentioned": 0,
            "Applied": 0,
            "Architected": 0,
            "Total": 0
        },
        "penalty_frequency": {
            "short_tenures": 0,
            "no_quantified_impact": 0,
            "unexplained_gap": 0,
            "low_impact": 0,
            "depth_inflation": 0,
            "career_drift": 0,
            "total_penalties_applied": 0
        },
        "trajectory_distribution": {},
        "grade_distribution": {}
    }

    # Extreme Candidates
    pool_sorted = sorted(pool, key=lambda x: x.get("raw_base_talent_score", 0), reverse=True)
    n = len(pool_sorted)
    top_5_n = max(1, int(n * 0.05))
    bot_10_n = max(1, int(n * 0.10))
    
    audit_results["extreme_candidates"]["top_5_percent_raw"] = [
        {"name": c["name"], "score": c["raw_base_talent_score"], "position": c["position"]}
        for c in pool_sorted[:top_5_n]
    ]
    audit_results["extreme_candidates"]["bottom_10_percent_raw"] = [
        {"name": c["name"], "score": c["raw_base_talent_score"], "position": c["position"]}
        for c in pool_sorted[-bot_10_n:]
    ]

    # Skill Depth Distribution
    for c in pool:
        skills = c.get("skills_depth", [])
        for s in skills:
            depth = s.get("depth", "Mentioned")
            audit_results["skill_depth_distribution"][depth] = audit_results["skill_depth_distribution"].get(depth, 0) + 1
            audit_results["skill_depth_distribution"]["Total"] += 1

    # Penalty Frequency
    for c in pool:
        details = c.get("talent_score_details", {})
        penalties = details.get("penalties", {})
        if penalties:
            audit_results["penalty_frequency"]["total_penalties_applied"] += len(penalties)
            for p_type in penalties:
                audit_results["penalty_frequency"][p_type] = audit_results["penalty_frequency"].get(p_type, 0) + 1

    # Trajectory & Grade
    for c in pool:
        traj = c.get("career_trajectory", "Neutral")
        audit_results["trajectory_distribution"][traj] = audit_results["trajectory_distribution"].get(traj, 0) + 1
        
        grade = c.get("career_path_grade", "N")
        audit_results["grade_distribution"][grade] = audit_results["grade_distribution"].get(grade, 0) + 1

    # Calculate Percentages
    n_candidates = len(pool)
    total_skills = audit_results["skill_depth_distribution"]["Total"]
    
    if total_skills > 0:
        for k in ["Mentioned", "Applied", "Architected"]:
            audit_results["skill_depth_distribution"][f"{k}_pct"] = round(audit_results["skill_depth_distribution"][k] / total_skills * 100, 1)

    for k in ["short_tenures", "no_quantified_impact", "unexplained_gap", "low_impact", "depth_inflation", "career_drift"]:
        audit_results["penalty_frequency"][f"{k}_pct"] = round(audit_results["penalty_frequency"].get(k, 0) / n_candidates * 100, 1)

    audit_results["penalty_frequency"]["avg_penalties_per_cand"] = round(audit_results["penalty_frequency"]["total_penalties_applied"] / n_candidates, 2)

    for k in list(audit_results["trajectory_distribution"].keys()):
        audit_results["trajectory_distribution"][f"{k}_pct"] = round(audit_results["trajectory_distribution"][k] / n_candidates * 100, 1)

    # Save Results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(audit_results, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Audit Complete. Results saved to {output_path}")
    
    # Generate Markdown Summary
    report_md = f"""# 📊 Market Fitness Audit Report (v1.3)
Generated: {n_candidates} candidates

## 1. Score Analysis
| Metric | Raw Score (Pre-Normal) | Target / Note |
| :--- | :--- | :--- |
| **Mean** | {audit_results['score_stats']['raw']['mean']} | {audit_results['score_stats']['normalized']['mean']} (Norm) |
| **StdDev** | {audit_results['score_stats']['raw']['std']} | {audit_results['score_stats']['normalized']['std']} (Norm) |
| **Max** | {audit_results['score_stats']['raw']['max']} | |
| **Min** | {audit_results['score_stats']['raw']['min']} | |

## 2. Skill Depth Distribution
| Depth | Count | Percentage | Target |
| :--- | :--- | :--- | :--- |
| Mentioned | {audit_results['skill_depth_distribution']['Mentioned']} | {audit_results['skill_depth_distribution']['Mentioned_pct']}% | ≥ 40% |
| Applied | {audit_results['skill_depth_distribution']['Applied']} | {audit_results['skill_depth_distribution']['Applied_pct']}% | |
| Architected | {audit_results['skill_depth_distribution']['Architected']} | {audit_results['skill_depth_distribution']['Architected_pct']}% | ≤ 15% |

## 3. Penalty Frequency
| Penalty Type | Frequency | Percentage | Target |
| :--- | :--- | :--- | :--- |
| Short Tenures | {audit_results['penalty_frequency'].get('short_tenures', 0)} | {audit_results['penalty_frequency'].get('short_tenures_pct', 0)}% | |
| No Quant Impact | {audit_results['penalty_frequency'].get('no_quantified_impact', 0)} | {audit_results['penalty_frequency'].get('no_quantified_impact_pct', 0)}% | |
| Low Impact | {audit_results['penalty_frequency'].get('low_impact', 0)} | {audit_results['penalty_frequency'].get('low_impact_pct', 0)}% | |
| Depth Inflation | {audit_results['penalty_frequency'].get('depth_inflation', 0)} | {audit_results['penalty_frequency'].get('depth_inflation_pct', 0)}% | |
| Career Drift | {audit_results['penalty_frequency'].get('career_drift', 0)} | {audit_results['penalty_frequency'].get('career_drift_pct', 0)}% | |
| Unexplained Gap | {audit_results['penalty_frequency'].get('unexplained_gap', 0)} | {audit_results['penalty_frequency'].get('unexplained_gap_pct', 0)}% | |
| **Avg Penalties** | **{audit_results['penalty_frequency']['avg_penalties_per_cand']}** | | **-5 ~ -8 pts equivalent** |

## 4. Career Trajectory Distribution
| Trajectory | Count | Percentage | Target |
| :--- | :--- | :--- | :--- |
| Ascending | {audit_results['trajectory_distribution'].get('Ascending', 0)} | {audit_results['trajectory_distribution'].get('Ascending_pct', 0)}% | 10~20% |
| Stable | {audit_results['trajectory_distribution'].get('Stable', 0)} | {audit_results['trajectory_distribution'].get('Stable_pct', 0)}% | 30~40% |
| Neutral | {audit_results['trajectory_distribution'].get('Neutral', 0)} | {audit_results['trajectory_distribution'].get('Neutral_pct', 0)}% | 20~30% |
| Volatile | {audit_results['trajectory_distribution'].get('Volatile', 0)} | {audit_results['trajectory_distribution'].get('Volatile_pct', 0)}% | 10~20% |

## 5. Extreme Cases Analysis
### Top 5% Raw Candidates
{chr(10).join([f"- {c['name']} ({c['score']}): {c['position']}" for c in audit_results['extreme_candidates']['top_5_percent_raw']])}

### Bottom 10% Raw Candidates
{chr(10).join([f"- {c['name']} ({c['score']}): {c['position']}" for c in audit_results['extreme_candidates']['bottom_10_percent_raw']])}
"""
    with open("headhunting_engine/analytics/market_fitness_report_v1.3.md", 'w', encoding='utf-8') as f:
        f.write(report_md)

if __name__ == "__main__":
    POOL_PATH = "headhunting_engine/analytics/reparsed_pool_v1.2.json"
    OUTPUT_PATH = "headhunting_engine/analytics/market_fitness_audit_v1.3.json"
    run_market_fitness_audit(POOL_PATH, OUTPUT_PATH)
