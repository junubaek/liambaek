import json
import sys
import os
sys.path.append(os.getcwd())
from headhunting_engine.matching.scorer import Scorer

def test_v6_2_scoring():
    print("🧪 Testing Scorer v6.2...")
    scorer = Scorer()
    
    # 1. Test Data: Ascending Candidate with "Owned" depth
    candidate_data = {
        "candidate_profile": {
            "primary_sector": "SEMICONDUCTOR",
            "cross_sector_flag": True
        },
        "patterns": [
            {"pattern": "RTL_Design", "depth": "Owned", "impact_type": "Quantitative"},
            {"pattern": "NPU_Design", "depth": "Led", "impact_type": "Quantitative"}
        ],
        "career_path_quality": {
            "trajectory_grade": "Ascending",
            "career_path_score": 90
        }
    }
    
    jd_context = {
        "sector": "SEMICONDUCTOR",
        "experience_patterns": ["RTL_Design", "NPU_Design"],
        "cross_sector_requested": True
    }
    
    score, details = scorer.calculate_score(candidate_data, jd_context)
    
    print(f"Final Score: {score}")
    print(f"Details: {json.dumps(details, indent=2)}")
    
    # Assertions
    assert details["pattern_coverage"] == 100.0
    assert details["context_fit"] == 120.0 # 100 base + 20 cross-sector bonus
    assert details["trajectory"] == 100.0 # 90 * 1.2 = 108 -> clamped to 100
    
    # 2. Test Data: Volatile Candidate
    candidate_volatile = {
        "candidate_profile": {"primary_sector": "TECH_SW"},
        "patterns": [{"pattern": "MSA_Architecture", "depth": "Assisted"}],
        "career_path_quality": {
            "trajectory_grade": "Volatile",
            "career_path_score": 40
        }
    }
    
    jd_sw = {
        "sector": "TECH_SW",
        "experience_patterns": ["MSA_Architecture"]
    }
    
    score_v, details_v = scorer.calculate_score(candidate_volatile, jd_sw)
    print(f"\nVolatile Candidate Score: {score_v}")
    print(f"Trajectory: {details_v['trajectory']}")
    assert details_v["trajectory"] == 20.0 # 40 * 0.5
    
    print("\n✅ Scorer v6.2 Verification Passed!")

if __name__ == "__main__":
    test_v6_2_scoring()
