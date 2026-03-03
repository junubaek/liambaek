
import json
import os
from headhunting_engine.analytics.scarcity import ScarcityEngine

def calibrate_scarcity_v3():
    pool_path = "headhunting_engine/analytics/reparsed_pool_v1.3_elite.json"
    output_path = "headhunting_engine/analytics/scarcity_snapshot.json"
    
    print(f"🔄 Calibrating Scarcity v3 from {pool_path}...")
    
    with open(pool_path, 'r', encoding='utf-8') as f:
        pool = json.load(f)
        
    se = ScarcityEngine()
    
    # 1. Custom Snapshot Creation logic for v3
    stats = {}
    for cand in pool:
        role = cand.get("role_family", "General_Tech")
        for s in cand.get("skills_depth", []):
            name = s["name"]
            depth = s["depth"]
            
            if name not in stats:
                stats[name] = {
                    "count": 0,
                    "depth_distribution": {"Mentioned": 0, "Applied": 0, "Architected": 0},
                    "role_pool_size": 0,
                    "cluster": "General_Tech" # Placeholder
                }
            
            stats[name]["count"] += 1
            stats[name]["depth_distribution"][depth] = stats[name]["depth_distribution"].get(depth, 0) + 1

    # Add role_pool_size (simplified as those in the same role family)
    role_counts = {}
    for cand in pool:
        role = cand.get("role_family", "General_Tech")
        role_counts[role] = role_counts.get(role, 0) + 1

    # Map skills to clusters and role pool sizes
    # (Simplified for calibration)
    for name, s_data in stats.items():
        s_data["role_pool_size"] = len(pool) # Use total pool as denominator for global scarcity
        
    # 2. Save v3 Snapshot
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Scarcity Snapshot v3 calibrated at {output_path}")

if __name__ == "__main__":
    calibrate_scarcity_v3()
