import json
import sys
import os
import statistics

# Add current directory to path for imports
sys.path.append(os.getcwd())

from connectors.notion_api import HeadhunterDB
from headhunting_engine.main_pipeline import MainPipeline
from headhunting_engine.analytics.diagnostic_reporter import DiagnosticReporter
from headhunting_engine.normalization.resume_normalizer import ResumeNormalizer

def run_real_data_validation(limit=200):
    print(f"🚀 Starting Enterprise Validation v1.2: Real Data Test (Limit: {limit})")
    
    # 1. Initialize DB and Pipeline
    db = HeadhunterDB()
    pipeline = MainPipeline(dictionary_path='headhunting_engine/dictionary/canonical_dictionary_v1.json')
    normalizer = ResumeNormalizer(dictionary_path='headhunting_engine/dictionary/canonical_dictionary_v1.json')
    
    # Check for cache
    cache_path = 'headhunting_engine/analytics/processed_pool_notion.json'
    if os.path.exists(cache_path):
        print(f"📦 Loading candidates from cache: {cache_path}")
        with open(cache_path, 'r', encoding='utf-8') as f:
            processed_pool = json.load(f)
    else:
        # Fetch and process
        print(f"📡 Fetching {limit} candidates from Notion...")
        raw_candidates = db.fetch_candidates(limit=limit)
        
        processed_pool = []
        print(f"🧠 Normalizing skills for {len(raw_candidates)} candidates...")
        
        for i, cand in enumerate(raw_candidates):
            page_id = cand['id']
            text = db.fetch_candidate_details(page_id)
            norm_result = normalizer.normalize(text)
            
            talent_score = cand.get('base_talent_score', 65)
            if talent_score is None: talent_score = 60
            
            processed_pool.append({
                "id": cand['id'],
                "name": cand.get('이름', 'Unknown'),
                "position": cand.get('포지션', 'Generalist'),
                "canonical_skill_nodes": norm_result['canonical_skill_nodes'],
                "base_talent_score": talent_score,
                "career_path_grade": cand.get('career_path_grade', 'Stable'),
                "career_trajectory": cand.get('career_trajectory', 'Stable'),
                "domain_match": True,
                "company_size_match": True
            })
            if (i + 1) % 50 == 0:
                print(f"  Processed {i+1}/{len(raw_candidates)}...")
        
        # Save cache
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(processed_pool, f, indent=2, ensure_ascii=False)

    # 3. Setup Scarcity
    print("📊 Generating Scarcity Snapshot from real data...")
    pipeline.scarcity_engine.create_snapshot(processed_pool, 'headhunting_engine/analytics/real_scarcity_snapshot.json')
    pipeline.scarcity_engine.load_snapshot('headhunting_engine/analytics/real_scarcity_snapshot.json')
    
    # 4. Run Matching against a standard JD
    # Let's use "Python Specialist" (Single Must)
    jd_data = {
        "id": "JD_REAL_TEST_PYTHON",
        "must_have": ["Language_Python"],
        "nice_to_have": ["DL_Framework", "MLOps"],
        "normalized_title": "Python_Specialist"
    }
    
    print(f"🎯 Running matching for JD: {jd_data['normalized_title']}...")
    # Enable search_mode=True for broad discovery
    results = pipeline.run_matching(jd_data, processed_pool, top_n=20, search_mode=True)
    
    # 5. Diagnostic Reporting
    reporter = DiagnosticReporter(pipeline.scarcity_engine)
    stats = reporter.analyze_matching_run(results, processed_pool)
    
    print("\n--- 📈 Real Data Validation Results (v1.2) ---")
    print(f"Total Candidates: {stats['pool_size']}")
    print(f"Hard Filter Passed: {stats['hard_filter_passed']} ({stats['pass_rate_pct']}%)")
    print(f"Avg Matching Score: {stats['avg_matching_score']}")
    print(f"Top Score: {stats['top_score']}")
    print(f"Avg RPL: {stats['rpl_stats']['avg_rpl']}")
    print(f"JD Scarcity Index: {stats['jd_scarcity']}")
    print(f"Unrealistic JD Flag: {stats['market_reality']['unrealistic_jd']}")
    
    # Save results for final report
    with open('real_data_validation_v1.2.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
        
    print(f"\n✅ Results saved to real_data_validation_v1.2.json")

if __name__ == "__main__":
    run_real_data_validation(limit=200)
