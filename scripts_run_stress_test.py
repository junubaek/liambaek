import json
import random
import sys
import os
import statistics

sys.path.append(os.getcwd())

from headhunting_engine.main_pipeline import MainPipeline
from headhunting_engine.analytics.diagnostic_reporter import DiagnosticReporter

def generate_high_entropy_pool(size=1000, num_total_skills=100):
    all_skills = [f"__TEMP__Skill_{i:03d}" for i in range(num_total_skills)]
    
    # [v1.2] Create 10 Archetypes (clusters of 10 skills each)
    archetypes = [all_skills[i:i+10] for i in range(0, num_total_skills, 10)]
    
    pool = []
    for i in range(size):
        score = int(random.gauss(65, 15))
        score = max(0, min(100, score))
        
        # Pick a primary archetype
        arch = random.choice(archetypes)
        num_arch_skills = random.randint(3, 8)
        cand_skills = random.sample(arch, num_arch_skills)
        
        # Add 1-3 random background skills
        other_skills = list(set(all_skills) - set(arch))
        cand_skills += random.sample(other_skills, random.randint(1, 3))
        
        pool.append({
            "id": f"SYNTH_{i:04d}",
            "position": "AI_Engineering", # Must match jd_normalized.get("normalized_title")
            "canonical_skill_nodes": cand_skills,
            "base_talent_score": score,
            "career_path_grade": "Stable" if score < 85 else "Ascending",
            "career_trajectory": "Ascending" if score > 80 else "Stable",
            "domain_match": random.random() > 0.7,
            "company_size_match": random.random() > 0.5
        })
    return pool, all_skills

def run_complexity_test():
    print("🚀 Starting Enterprise Validation v1.2: JD Complexity Stress Test")
    pipeline = MainPipeline(dictionary_path='headhunting_engine/dictionary/canonical_dictionary_v1.json')
    pool, all_skills = generate_high_entropy_pool(1000)
    pipeline.scarcity_engine.create_snapshot(pool, 'headhunting_engine/analytics/scarcity_snapshot.json')
    pipeline.scarcity_engine.load_snapshot('headhunting_engine/analytics/scarcity_snapshot.json')
    
    reporter = DiagnosticReporter(pipeline.scarcity_engine)
    
    test_cases = [1, 2, 5, 7]
    stress_results = []
    
    # Set seed for reproducibility in JD selection across test runs
    random.seed(42)
    
    for count in test_cases:
        # JD is based on Archetype 0
        # Use bare names like "Skill_001". Normalizer will map to "__TEMP__Skill_001"
        arch_0_bare = [f"Skill_{i:03d}" for i in range(10)]
        jd_must = random.sample(arch_0_bare, min(count, 10))
        if count > 10:
             jd_must += [f"Skill_{i:03d}" for i in random.sample(range(10, 100), count - 10)]
             
        jd_data = {
            "id": f"JD_STRESS_{count}",
            "must_have": jd_must,
            "nice_to_have": [],
            "normalized_title": "AI_Engineering"
        }
        
        results = pipeline.run_matching(jd_data, pool, top_n=100)
        
        # Debugging
        if count == 1:
            jd_normalized = pipeline.jd_normalizer.normalize_jd(jd_data)
            print(f"DEBUG: Must Nodes Optimized: {jd_normalized['must_nodes']}")
            print(f"DEBUG: Skill Index Keys Sample: {list(pipeline.prefilter.skill_index.keys())[:5]}")
            print(f"DEBUG: Role Index Keys: {list(pipeline.prefilter.role_index.keys())}")
            
        stats = reporter.analyze_matching_run(results, pool)
        
        stress_results.append({
            "must_count": count,
            "pass_rate": stats["pass_rate_pct"],
            "avg_matching": stats["avg_matching_score"],
            "avg_rpl": stats["rpl_stats"]["avg_rpl"],
            "difficulty": results["audit_trail"]["difficulty"],
            "unrealistic": stats["market_reality"]["unrealistic_jd"]
        })
        
    print("\n--- 📊 JD Complexity Stress Test Results ---")
    print(f"{'Must Count':<12} | {'Pass Rate':<10} | {'Avg Match':<10} | {'Avg RPL':<8} | {'Difficulty':<10} | {'Unrealistic'}")
    print("-" * 85)
    for r in stress_results:
        u_flag = "⚠️ YES" if r['unrealistic'] else "✅ NO"
        print(f"{r['must_count']:<12} | {r['pass_rate']:<10}% | {r['avg_matching']:<10} | {r['avg_rpl']:<8} | {r['difficulty']:<10} | {u_flag}")

if __name__ == "__main__":
    run_complexity_test()
