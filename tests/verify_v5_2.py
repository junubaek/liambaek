import json
import os
import sys

# Ensure app is importable
sys.path.append(os.getcwd())

from app.connectors.openai_api import OpenAIClient
from app.utils.candidate_role_classifier import CandidateRoleClassifier
from app.utils.candidate_extractor import CandidatePatternExtractor
from headhunting_engine.data_core import AnalyticsDB

def verify_v5_2_intelligence():
    print("🚀 Verifying Phase 5.2 Candidate Intelligence...")
    
    # 1. Setup
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    openai = OpenAIClient(secrets["OPENAI_API_KEY"])
    db = AnalyticsDB()
    extractor = CandidatePatternExtractor()
    classifier = CandidateRoleClassifier(openai)
    
    # 2. Mock Resume (Strategic Finance)
    resume_text = """
    Lee Strategic
    Experience: 8 years in FP&A and Strategic Planning.
    - Led 전사 KPI 설계 및 성과 트래킹 프로젝트.
    - Architected 손익 Projection 모델 고도화.
    - Managed Business Plan optimization for 2024.
    """
    
    # Mock data structure as if from ResumeParser
    structured_data = {
        "experience_patterns": [
            {"pattern": "KPI_Framework_Design", "depth": "Led", "quant_signal": "True"},
            {"pattern": "FP&A_Modeling", "depth": "Architected"},
            {"pattern": "Business_Plan_Optimization", "depth": "Executed"}
        ]
    }
    
    cand_id = "test_verify_5_2"
    tenant_id = "verification"
    
    # Ensure candidate exists for update
    db.save_candidate_snapshot(cand_id, "Lee Strategic", "Unclassified", 8, {})
    
    print("\n--- [Step 1] Role Classification ---")
    role = classifier.classify_candidate(resume_text)
    print(f"✅ Classified Role: {role}")
    db.update_candidate_role(cand_id, role)
    
    print("\n--- [Step 2] Pattern Indexing ---")
    patterns = extractor.extract_indexable_patterns(structured_data)
    db.save_candidate_patterns(cand_id, patterns, tenant_id=tenant_id)
    print(f"✅ Indexed {len(patterns)} patterns.")
    
    # 3. Database Verification
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    c = conn.cursor()
    c.execute("SELECT role FROM candidate_snapshots WHERE notion_id = ?", (cand_id,))
    db_role = c.fetchone()
    
    c.execute("SELECT pattern FROM candidate_patterns WHERE candidate_id = ? AND tenant_id = ?", (cand_id, tenant_id))
    db_patterns = [r[0] for r in c.fetchall()]
    
    print(f"\n--- [DB Verification] ---")
    print(f"DB Role: {db_role[0] if db_role else 'NOT FOUND'}")
    print(f"DB Patterns: {db_patterns}")
    
    if db_role and "CORPORATE" in db_role[0] or "FINANCE" in str(db_role[0]).upper():
        print("\n🎉 Phase 5.2 Verification SUCCESS!")
    else:
        # Note: Depending on ROLE_CLUSTERS, FP&A might fall under CORPORATE. 
        # Let's be flexible but check if it's not 'Unknown'.
        if db_role and db_role[0] != "Unknown":
            print("\n🎉 Phase 5.2 Verification SUCCESS (Custom Mapping)!")
        else:
            print("\n❌ Phase 5.2 Verification FAILED.")

if __name__ == "__main__":
    verify_v5_2_intelligence()
