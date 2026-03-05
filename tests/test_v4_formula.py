import pytest
import json
import os
from app.engine.matcher import Scorer

def test_universal_matching_ga():
    scorer = Scorer()
    jd_ga = {
        "role_family": "GA_Operations",
        "functional_domains": ["RealEstate_Management"],
        "experience_patterns": ["Lease_Negotiation", "Office_Relocation_PM"],
        "seniority_required": 5,
        "leadership_level": "Team Lead"
    }
    
    # Candidate with perfect GA pattern match
    cand_ga = {
        "id": "cand_01",
        "name": "GA Expert",
        "experience_patterns": [
            {"pattern": "Lease_Negotiation", "depth": "Led"},
            {"pattern": "Office_Relocation_PM", "depth": "Architected"}
        ],
        "domains": ["RealEstate_Management"],
        "total_years_experience": 8,
        "current_leadership_level": "Team Lead",
        "career_path_grade": "S"
    }
    
    score, details = scorer.calculate_score(cand_ga["experience_patterns"], context_data=jd_ga)
    
    assert score > 90 # S-grade and matching patterns
    assert details["pattern_match"] == 100.0
    assert details["domain_fit"] == 100.0

def test_mismatch_role_prevention():
    scorer = Scorer()
    # JD for Software Engineer
    jd_sw = {
        "role_family": "Software_Engineering",
        "experience_patterns": ["Microservices_Migration"],
        "functional_domains": ["Backend_Infra"]
    }
    
    # Candidate for HR
    cand_hr = {
        "experience_patterns": [{"pattern": "Org_Restructuring_Execution", "depth": "Led"}],
        "domains": ["Labor_Relations"]
    }
    
    score, details = scorer.calculate_score(cand_hr["experience_patterns"], context_data=jd_sw)
    assert score < 30 # Should be very low due to total mismatch in patterns/domains

if __name__ == "__main__":
    test_universal_matching_ga()
    test_mismatch_role_prevention()
    print("✅ Logic Verification Tests Passed.")
