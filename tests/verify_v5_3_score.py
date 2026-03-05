import json
import os
import sys

# Ensure app is importable
sys.path.append(os.getcwd())

from app.engine.matcher import Scorer

def verify_v5_3_scoring():
    print("🧪 Verifying Phase 5.3: 6-Factor Universal Matching Formula...")
    
    scorer = Scorer()
    
    # 1. Mock JD Context (Strategic Finance Manager)
    jd_context = {
        "role_family": "FINANCE_STRATEGY",
        "experience_patterns": ["FP&A_Modeling", "KPI_Framework_Design"],
        "seniority_required": 5,
        "leadership_level": "IC",
        "semantic_similarity": 0.8,
        "career_path_grade": "S",
        "experience_years": 8,
        "role_cluster": "FINANCE_STRATEGY",
        "current_leadership_level": "IC"
    }
    
    # 2. Mock Candidate Experience (from Index)
    # We simulate what would be retrieved from candidate_patterns
    cand_index_patterns = [
        {"pattern": "FP&A_Modeling", "depth": 1.3}, # Architected
        {"pattern": "KPI_Framework_Design", "depth": 1.0} # Led
    ]
    
    # Matching Factor Check
    score, breakdown = scorer.calculate_score(cand_index_patterns, jd_context)
    
    print("\n--- [Breakdown] ---")
    print(json.dumps(breakdown, indent=2))
    
    # Expectations:
    # Domain: FINANCE_STRATEGY matches -> 100 * 0.25 = 25
    # Pattern: (1.3 + 1.0)/2 = 1.15. (1.15 * 0.6) + (0.8 * 0.4) = 0.69 + 0.32 = 1.01 -> 101 * 0.35 = 35.35
    # Impact: 70 * 0.15 = 10.5
    # Seniority: 100 * 0.10 = 10
    # Lead: 100 * 0.10 = 10
    # Culture: 80 * 0.05 = 4
    # Base = 25 + 35.35 + 10.5 + 10 + 10 + 4 = 94.85
    # EM (S) = 94.85 * 1.10 = 104.33
    
    print(f"\nFinal Score: {score}")
    
    if 90 < score < 110:
        print("\n🎉 Phase 5.3 Scoring Verification SUCCESS!")
    else:
        print("\n❌ Phase 5.3 Scoring Verification FAILED. Check weights.")

if __name__ == "__main__":
    verify_v5_3_scoring()
