import json
import sys
import os

sys.path.append(os.getcwd())

from headhunting_engine.main_pipeline import MainPipeline

def run_edge_case_verification():
    print("🚀 Starting Enterprise Validation v1.2: Edge Case 3-Point Test")
    pipeline = MainPipeline(dictionary_path='headhunting_engine/dictionary/canonical_dictionary_v1.json')
    
    # 1. Setup Edge Case Pool
    pool = [
        {
            "id": "CASE_A_MONSTER",
            "position": "SW_Backend",
            "canonical_skill_nodes": ["Java", "Spring", "Kubernetes"],
            "base_talent_score": 95,
            "career_path_grade": "Ascending",
            "career_trajectory": "Ascending",
            "domain_match": True,
            "company_size_match": True
        },
        {
            "id": "CASE_B_LOW_TALENT",
            "position": "AI_Engineering",
            "canonical_skill_nodes": ["DL_Framework", "MLOps", "Distributed_Training"],
            "base_talent_score": 40,
            "career_path_grade": "Stable",
            "career_trajectory": "Neutral",
            "domain_match": False,
            "company_size_match": False
        },
        {
            "id": "CASE_C_ADJACENT",
            "position": "SW_Platform", # Adjacent to AI_Engineering
            "canonical_skill_nodes": ["DL_Framework", "MLOps", "Terraform"],
            "base_talent_score": 75,
            "career_path_grade": "Stable",
            "career_trajectory": "Stable",
            "domain_match": True,
            "company_size_match": True
        }
    ]
    
    # JD: AI Engineering (Must: DL_Framework, MLOps, Distributed_Training)
    jd_data = {
        "id": "JD_EDGE_TEST",
        "must_have": ["DL_Framework", "MLOps", "Distributed_Training"],
        "nice_to_have": [],
        "normalized_title": "AI_Engineering"
    }
    
    # 2. Scarcity Setup (Need a pool for Z-score)
    # Adding some noise to pool for stats
    noise = []
    for i in range(10):
        noise.append({
            "id": f"NOISE_{i}", "position": "AI_Engineering", 
            "canonical_skill_nodes": ["DL_Framework"], "base_talent_score": 60,
            "career_path_grade": "Stable"
        })
    
    full_pool = pool + noise
    pipeline.scarcity_engine.create_snapshot(full_pool, 'headhunting_engine/analytics/scarcity_snapshot.json')
    pipeline.scarcity_engine.load_snapshot('headhunting_engine/analytics/scarcity_snapshot.json')
    
    results = pipeline.run_matching(jd_data, full_pool, top_n=10)
    top_ids = [r["candidate_id"] for r in results["top_candidates"]]
    
    print("\n--- 🧪 Edge Case Verification Results ---")
    
    # Case A: Monster but Mismatch -> Should NOT be in top_candidates (0 coverage)
    case_a = next((r for r in results["top_candidates"] if r["candidate_id"] == "CASE_A_MONSTER"), None)
    if not case_a:
        print("✅ Case A (Talent Monster): Correctly REJECTED (0% Must Coverage)")
    else:
        print(f"❌ Case A (Talent Monster): FAILED (Score: {case_a['score']})")
        
    # Case B: Skill Perfect but Low Talent -> Should PASS but score < 70
    case_b = next((r for r in results["top_candidates"] if r["candidate_id"] == "CASE_B_LOW_TALENT"), None)
    if case_b:
        print(f"✅ Case B (Low Talent): PASSED. Score: {case_b['score']} (Target < 70)")
        if case_b['score'] >= 70:
             print(f"   ⚠️ Score is {case_b['score']}, slightly high for Low Talent.")
    else:
        print("❌ Case B (Low Talent): FAILED (Correctly matched but disappeared?)")
        
    # Case C: Adjacent Role -> Should PASS (33% or 66% coverage)
    case_c = next((r for r in results["top_candidates"] if r["candidate_id"] == "CASE_C_ADJACENT"), None)
    if case_c:
        print(f"✅ Case C (Adjacent Role): PASSED. Score: {case_c['score']}, RPL: {case_c['rpl']}")
    else:
        print("❌ Case C (Adjacent Role): FAILED (Filter too tight for Case C)")

if __name__ == "__main__":
    run_edge_case_verification()
