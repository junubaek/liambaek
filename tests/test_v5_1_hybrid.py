import json
import os
import sys
import sqlite3

# Ensure app is importable
sys.path.append(os.getcwd())

from app.connectors.openai_api import OpenAIClient
from app.utils.jd_parser_v3 import JDParserV3
from app.utils.resume_parser import ResumeParser
from app.utils.candidate_extractor import CandidatePatternExtractor
from app.engine.matcher import Scorer
from headhunting_engine.data_core import AnalyticsDB

def test_v5_1_intelligence():
    print("🚀 Starting Phase 5.1 Candidate Intelligence Integration Test...")
    
    # 1. Setup
    db = AnalyticsDB()
    extractor = CandidatePatternExtractor()
    scorer = Scorer()
    
    candidate_id = "test_cand_001"
    tenant_id = "test_tenant"
    
    # 2. Simulate Resume Parsing Output (v5.2 format)
    mock_resume_data = {
        "basics": {"name": "Kim Pattern", "total_years_experience": 10},
        "experience_patterns": [
            {"pattern": "Office_Relocation_PM", "depth": "Architected", "quant_signal": True},
            {"pattern": "Lease_Negotiation", "depth": "Led", "quant_signal": False}
        ]
    }
    
    # 3. Step 1: Pattern Extraction & Indexing
    print("\n--- [Step 1] Pattern Extraction & Indexing ---")
    indexable_patterns = extractor.extract_indexable_patterns(mock_resume_data)
    db.save_candidate_patterns(candidate_id, indexable_patterns, tenant_id=tenant_id)
    print(f"✅ Indexed {len(indexable_patterns)} patterns for {candidate_id}")
    
    # Verify DB entry
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pattern, depth FROM candidate_patterns WHERE candidate_id = ?", (candidate_id,))
        rows = cursor.fetchall()
        print(f"   DB Verification: {rows}")
        assert len(rows) == 2

    # 4. Step 2: Hybrid Search (Scoring)
    print("\n--- [Step 2] Hybrid Search (Scoring) ---")
    jd_context = {
        "experience_patterns": ["Office_Relocation_PM", "Vendor_Management"],
        "functional_domains": ["GA_Operations"],
        "semantic_similarity": 0.85 # Mocked from Qdrant
    }
    
    # The hybrid matcher expects pattern scores + semantic similarity
    # In a real UI/API call, the matcher would query the DB first.
    # For this test, we pass the extracted patterns directly to Scorer.calculate_score
    score, breakdown = scorer.calculate_score(indexable_patterns, jd_context)
    
    print(f"✅ Final Hybrid Match Score: {score}")
    print(f"✅ Breakdown: {breakdown}")
    
    # Verification:
    # Pattern Match: (1.3[Office_Relocation] + 0[Vendor]) / 2 = 0.65 -> 65.0
    # Hybrid: (65.0 * 0.6) + (0.85 * 100 * 0.4) = 39.0 + 34.0 = 73.0
    print(f"   Expectation: ~73.0 (Pattern 39.0 + Semantic 34.0)")
    
    if 70 <= score <= 75:
        print("\n🎉 Phase 5.1 Intelligence Test PASSED!")
    else:
        print(f"\n❌ Phase 5.1 Intelligence Test FAILED (Score: {score})")

if __name__ == "__main__":
    test_v5_1_intelligence()
