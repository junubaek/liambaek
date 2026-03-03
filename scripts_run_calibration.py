import json
import random
import sys
import os
import statistics

# Add current dir to path for imports
sys.path.append(os.getcwd())

from headhunting_engine.main_pipeline import MainPipeline
from headhunting_engine.analytics.diagnostic_reporter import DiagnosticReporter

def generate_synthetic_pool(size=1000):
    """
    Generates a high-entropy mock candidate pool (50 skills).
    """
    roles = ["SW_Backend", "AI_Engineering", "DATA_Science", "DATA_Engineering", "SW_Platform"]
    all_skills = [f"__TEMP__Skill_{i:02d}" for i in range(50)]
    
    pool = []
    for i in range(size):
        score = int(random.gauss(65, 15))
        score = max(0, min(100, score))
        
        num_skills = random.randint(5, 15)
        cand_skills = random.sample(all_skills, num_skills)
        
        pool.append({
            "id": f"SYNTH_{i:04d}",
            "position": random.choice(roles),
            "canonical_skill_nodes": cand_skills,
            "base_talent_score": score,
            "career_path_grade": "Stable" if score < 75 else "Ascending",
            "domain_match": random.random() > 0.7,
            "company_size_match": random.random() > 0.5,
            "career_trajectory": "Ascending" if score > 80 else "Stable"
        })
    return pool

def run_statistical_validation():
    print("🚀 Initializing AI Headhunting Engine Statistical Validation...")
    
    pipeline = MainPipeline(
        dictionary_path='headhunting_engine/dictionary/canonical_dictionary_v1.json'
    )
    
    # 1. Generate Pool (1000 candidates)
    pool = generate_synthetic_pool(1000)
    
    # 2. Scarcity Snapshot
    pipeline.scarcity_engine.create_snapshot(pool, 'headhunting_engine/analytics/scarcity_snapshot.json')
    pipeline.scarcity_engine.load_snapshot('headhunting_engine/analytics/scarcity_snapshot.json')
    
    # 3. Diagnostic Report
    reporter = DiagnosticReporter(pipeline.scarcity_engine)
    pool_stats = reporter.analyze_candidate_pool(pool)
    
    # 4. Run Matching for high-demand JD (3 Must Skills -> Threshold 0.6)
    jd_data = {
        "id": "JD_CALIBRATION_001",
        "must_have": ["Skill_01", "Skill_02", "Skill_03"],
        "nice_to_have": ["Skill_04", "Skill_05"],
        "normalized_title": "AI_Engineering"
    }
    
    results = pipeline.run_matching(jd_data, pool, top_n=100, debug=True) 
    matching_stats = reporter.analyze_matching_run(results, pool)
    failure_cases = reporter.identify_failure_cases(results, pool)
    
    # 5. Output Data Points
    print("\n--- 1️⃣ Candidate Pool Distribution (N=1000) ---")
    print(json.dumps(pool_stats, indent=2))
    
    print("\n--- 2️⃣ Matching Score & RPL Distribution (JD: AI_Engineering) ---")
    print(json.dumps(matching_stats, indent=2))
    
    print("\n--- 3️⃣ Must Coverage Histogram ---")
    print(json.dumps(matching_stats["must_coverage_histogram"], indent=2))
    
    print("\n--- 6️⃣ Failure Case Analysis ---")
    print(json.dumps(failure_cases, indent=2))
    
    print("\n--- 5️⃣ Scarcity Snapshot ---")
    print(json.dumps(reporter.get_scarcity_snapshot(), indent=2))
    
    print("\n--- 🧪 Calibration Analysis ---")
    avg_match = matching_stats["avg_matching_score"]
    avg_base = pool_stats["avg_base_score"]
    
    if avg_match > avg_base + 10:
        print("⚠️ Warning: Score Inflation detected. Matching average significantly higher than pool average.")
    else:
        print("✅ Healthy Baseline: Score distributions align with pool expectations.")

if __name__ == "__main__":
    run_statistical_validation()
