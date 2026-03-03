
import json
import statistics

def generate_baseline():
    pool_path = "headhunting_engine/analytics/reparsed_pool_v1.2.json"
    with open(pool_path, 'r', encoding='utf-8') as f:
        pool = json.load(f)

    total_candidates = len(pool)
    skill_depths = {"Mentioned": 0, "Applied": 0, "Architected": 0, "Total": 0}
    trajectories = {"Ascending": 0, "Stable": 0, "Neutral": 0, "Volatile": 0}
    
    for c in pool:
        for s in c.get("skills_depth", []):
            depth = s.get("depth", "Mentioned")
            skill_depths[depth] += 1
            skill_depths["Total"] += 1
        
        traj = c.get("career_trajectory", "Neutral")
        trajectories[traj] = trajectories.get(traj, 0) + 1

    baseline = {
        "n_candidates": total_candidates,
        "skill_depth_pct": {
            k: round(skill_depths[k] / skill_depths["Total"] * 100, 2) 
            for k in ["Mentioned", "Applied", "Architected"]
            if skill_depths["Total"] > 0
        },
        "trajectory_pct": {
            k: round(trajectories.get(k, 0) / total_candidates * 100, 2)
            for k in ["Ascending", "Stable", "Neutral", "Volatile"]
        }
    }

    with open("headhunting_engine/analytics/v1.3.1_gold_baseline.json", 'w', encoding='utf-8') as f:
        json.dump(baseline, f, indent=2, ensure_ascii=False)
    
    print("✅ Gold Baseline generated.")

if __name__ == "__main__":
    generate_baseline()
