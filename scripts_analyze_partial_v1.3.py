
import json
import os

def analyze_partial():
    partial_path = "headhunting_engine/analytics/reparsed_pool_v1.2.json.partial"
    baseline_path = "headhunting_engine/analytics/v1.3.1_gold_baseline.json"
    
    if not os.path.exists(partial_path):
        print("❌ Partial file not found.")
        return

    with open(partial_path, 'r', encoding='utf-8') as f:
        pool = json.load(f)
    
    with open(baseline_path, 'r', encoding='utf-8') as f:
        baseline = json.load(f)

    n = len(pool)
    skill_depths = {"Mentioned": 0, "Applied": 0, "Architected": 0, "Total": 0}
    trajectories = {"Ascending": 0, "Stable": 0, "Neutral": 0, "Volatile": 0}
    
    for c in pool:
        for s in c.get("skills_depth", []):
            depth = s.get("depth", "Mentioned")
            skill_depths[depth] += 1
            skill_depths["Total"] += 1
        
        traj = c.get("career_trajectory", "Neutral")
        trajectories[traj] += 1

    applied_pct = round(skill_depths["Applied"] / skill_depths["Total"] * 100, 1) if skill_depths["Total"] > 0 else 0
    asc_pct = round(trajectories["Ascending"] / n * 100, 1) if n > 0 else 0

    print(f"📊 [Partial Analysis (N={n})]")
    print(f"- Applied Depth: {applied_pct}% (Baseline: {baseline['skill_depth_pct']['Applied']}%)")
    print(f"- Ascending Traj: {asc_pct}% (Baseline: {baseline['trajectory_pct']['Ascending']}%)")
    
    if abs(applied_pct - baseline['skill_depth_pct']['Applied']) < 10:
        print("✅ Healthy Consistency (No Depth Drift)")
    else:
        print("⚠️ Significant Drift Detected in Depth!")

if __name__ == "__main__":
    analyze_partial()
