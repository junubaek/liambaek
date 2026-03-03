import json
import random
import sys
import os

sys.path.append(os.getcwd())

from headhunting_engine.main_pipeline import MainPipeline
from headhunting_engine.analytics.diagnostic_reporter import DiagnosticReporter

def generate_targeted_pool(size=1000):
    all_skills = [f"Skill_{i:03d}" for i in range(50)]
    pool = []
    # 30% Specialists (have Skills 00-05)
    # 70% Generalists (random)
    for i in range(size):
        score = random.randint(50, 90)
        
        if i < 300:
            cand_skills = random.sample(all_skills[:10], 5) + random.sample(all_skills[10:], 5)
        else:
            cand_skills = random.sample(all_skills[10:], 10)
            
        pool.append({
            "id": f"SYNTH_{i:04d}",
            "position": "AI_Engineering",
            "canonical_skill_nodes": cand_skills, # Bare names like "Skill_001"
            "base_talent_score": score,
            "career_path_grade": "Stable",
            "career_trajectory": "Stable",
            "domain_match": True,
            "company_size_match": True
        })
    return pool

def run_difficulty_matrix():
    print("🚀 Starting Enterprise Validation v1.2: Difficulty Matrix Validation")
    pipeline = MainPipeline(dictionary_path='headhunting_engine/dictionary/canonical_dictionary_v1.json')
    pool = generate_targeted_pool(1000)
    
    canonical_ids = set(pipeline.resume_normalizer.dict_data.get("canonical_skill_nodes", {}).keys())
    pipeline.scarcity_engine.create_snapshot(pool, 'headhunting_engine/analytics/scarcity_snapshot.json', canonical_ids=canonical_ids)
    pipeline.scarcity_engine.load_snapshot('headhunting_engine/analytics/scarcity_snapshot.json')
    reporter = DiagnosticReporter(pipeline.scarcity_engine)
    
    # Define JD scenarios to force different difficulties
    scenarios = [
        {"name": "Easy", "must": ["Skill_010", "Skill_011"]}, # Generalist skills
        {"name": "Moderate", "must": ["Skill_000", "Skill_010", "Skill_020"]}, 
        {"name": "Hard", "must": ["Skill_000", "Skill_001", "Skill_002"]}, # Specialist skills
        {"name": "Very Hard", "must": ["Skill_000", "Skill_001", "Skill_002", "Skill_003", "Skill_004"]}
    ]
    
    matrix = []
    for sc in scenarios:
        jd_data = {"id": f"JD_{sc['name']}", "must_have": sc["must"], "nice_to_have": [], "normalized_title": "AI_Engineering"}
        results = pipeline.run_matching(jd_data, pool, search_mode=True)
        stats = reporter.analyze_matching_run(results, pool)
        
        matrix.append({
            "label": sc["name"],
            "calc_difficulty": results["audit_trail"]["difficulty"],
            "avg_coverage": round(results["audit_trail"].get("avg_coverage", 0), 2), # Note: need to ensure avg_coverage is in audit
            "pass_rate": stats["pass_rate_pct"],
            "avg_rpl": stats["rpl_stats"]["avg_rpl"]
        })
        
    print("\n--- 📊 Difficulty Matrix Results ---")
    print(f"{'Scenario':<12} | {'Labeled As':<12} | {'Pass Rate':<10} | {'Avg RPL':<8}")
    print("-" * 55)
    for m in matrix:
        print(f"{m['label']:<12} | {m['calc_difficulty']:<12} | {m['pass_rate']:<10}% | {m['avg_rpl']:<8}")

if __name__ == "__main__":
    run_difficulty_matrix()
