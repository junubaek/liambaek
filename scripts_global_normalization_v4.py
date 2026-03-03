
import json
import os
import numpy as np
from typing import List, Dict

def run_global_normalization():
    pool_path = "headhunting_engine/analytics/reparsed_pool_v1.2.json.partial"
    if not os.path.exists(pool_path):
        pool_path = "headhunting_engine/analytics/reparsed_pool_v1.2.json"
    
    if not os.path.exists(pool_path):
        print("❌ Error: Pool file not found.")
        return

    print(f"🔄 Loading pool from {pool_path}...")
    with open(pool_path, 'r', encoding='utf-8') as f:
        pool = json.load(f)

    n = len(pool)
    print(f"📊 Processing {n} candidates for Global Normalization...")

    # 1. Collect Scores
    raw_scores = [c.get("base_talent_score", 50) for c in pool]
    mean_val = np.mean(raw_scores)
    std_val = np.std(raw_scores)

    print(f"📈 Raw Statistics: Mean={round(mean_val, 2)}, Std={round(std_val, 2)}")

    # 2. Calculate Z-scores and Sort
    for c in pool:
        raw = c.get("base_talent_score", 50)
        z = (raw - mean_val) / std_val if std_val > 0 else 0
        c["global_z_score"] = round(z, 4)

    # Sort by Z-score descending
    pool.sort(key=lambda x: x["global_z_score"], reverse=True)

    # 3. Apply Quotas
    # S: 5%, A: 15% (Cumulative 20%), B: 40% (60%), C: 25% (85%), D: 15% (100%)
    quotas = {
        "S": int(n * 0.05),
        "A": int(n * 0.15),
        "B": int(n * 0.40),
        "C": int(n * 0.25),
        "D": n # Rest
    }

    current = 0
    assigned = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    
    for i, c in enumerate(pool):
        if i < quotas["S"]:
            grade = "S"
        elif i < quotas["S"] + quotas["A"]:
            grade = "A"
        elif i < quotas["S"] + quotas["A"] + quotas["B"]:
            grade = "B"
        elif i < quotas["S"] + quotas["A"] + quotas["B"] + quotas["C"]:
            grade = "C"
        else:
            grade = "D"
        
        c["career_path_grade"] = grade
        assigned[grade] += 1

    print(f"✅ Quota Applied: {assigned}")

    # 4. Save Updated Pool
    output_path = "headhunting_engine/analytics/reparsed_pool_v1.3_elite.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(pool, f, indent=2, ensure_ascii=False)

    # 5. Generate Elite Snapshot
    snapshot = {
        "total_n": n,
        "raw_mean": round(mean_val, 2),
        "raw_std": round(std_val, 2),
        "elite_layer": {
            "S_count": assigned["S"],
            "A_count": assigned["A"],
            "top_candidates": [{"name": c["name"], "z": c["global_z_score"], "raw": c["base_talent_score"]} for c in pool[:20]]
        },
        "assigned_distribution": assigned
    }

    with open("headhunting_engine/analytics/elite_snapshot.json", 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"🏆 Elite Snapshot generated at headhunting_engine/analytics/elite_snapshot.json")

if __name__ == "__main__":
    run_global_normalization()
