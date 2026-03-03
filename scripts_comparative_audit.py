import os
import json
import statistics
from collections import Counter

def run_comparative_audit():
    old_json_path = r"headhunting_engine\analytics\processed_pool_notion.json"
    new_json_path = r"headhunting_engine\analytics\reparsed_pool_v1.2.json"
    dictionary_path = r"headhunting_engine\dictionary\canonical_dictionary_v1.json"
    
    print("📊 Generating Phase 2.2 Comparative Audit Report...")
    
    def get_stats(path):
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            candidates = json.load(f)
        
        scores = [c.get("base_talent_score", 0) for c in candidates]
        skills_per_cand = [len(c.get("canonical_skill_nodes", [])) for c in candidates]
        positions = [c.get("position", "Unclassified") for c in candidates]
        
        all_skills = []
        for c in candidates:
            all_skills.extend(c.get("canonical_skill_nodes", []))
            
        return {
            "count": len(candidates),
            "avg_score": statistics.mean(scores) if scores else 0,
            "avg_skills": statistics.mean(skills_per_cand) if skills_per_cand else 0,
            "unique_positions": len(set(positions)),
            "total_skill_instances": len(all_skills),
            "top_skills": Counter(all_skills).most_common(5)
        }

    old_stats = get_stats(old_json_path)
    new_stats = get_stats(new_json_path)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "legacy_pool": old_stats,
        "reparsed_v1.2_pool": new_stats,
        "improvement_metrics": {
            "pool_growth": f"{(new_stats['count']/old_stats['count']*100)-100:.1f}%" if old_stats else "N/A",
            "skill_visibility_multiplier": f"{new_stats['avg_skills']/old_stats['avg_skills']:.1f}x" if old_stats and old_stats['avg_skills'] > 0 else "N/A"
        }
    }
    
    report_path = "headhunting_engine/analytics/comparative_audit_v2.2.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print(f"\n✅ Audit Complete. Legacy Avg Skills: {old_stats['avg_skills']:.2f} -> New Avg Skills: {new_stats['avg_skills']:.2f}")
    print(f"✅ New Pool Size: {new_stats['count']} (from raw assets)")
    print(f"📝 Full report: {report_path}")

import time
if __name__ == "__main__":
    run_comparative_audit()
