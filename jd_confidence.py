
def estimate_jd_confidence(jd_structured: dict) -> float:
    """
    Returns confidence score between 0.0 ~ 1.0 based on JD clarity.
    """
    if not jd_structured:
        return 0.0

    score = 1.0
    reasons = []

    # 1. Must-have Skills Count
    must = jd_structured.get("explicit_skills", [])
    if len(must) < 2:
        penalty = 0.25
        score -= penalty
        reasons.append(f"Lack of explicit skills (-{penalty})")
    
    # 2. Role Clarity
    # If role is generic ("Engineer", "Developer") -> lower confidence
    role_candidates = jd_structured.get("title_candidates", [])
    if not role_candidates:
        penalty = 0.20
        score -= penalty
        reasons.append(f"No clear role title (-{penalty})")
    else:
        # Check for generic roles
        generic_keywords = ["engineer", "developer", "programmer", "staff", "intern"]
        # If any candidate is VERY generic and short
        if any(r.lower() in generic_keywords for r in role_candidates):
            penalty = 0.15
            score -= penalty
            reasons.append(f"Generic role title (-{penalty})")

    # 3. Domain Specificity
    domain = jd_structured.get("domain_clues", [])
    if not domain:
        penalty = 0.15
        score -= penalty
        reasons.append(f"No domain context (-{penalty})")

    # 4. Experience / Seniority
    seniority = jd_structured.get("seniority_clues", [])
    if not seniority:
        penalty = 0.15
        score -= penalty
        reasons.append(f"No seniority/experience level (-{penalty})")

    final_score = max(0.0, min(1.0, score))
    
    # Attach debug info to the dict (optional, for UI)
    jd_structured["_confidence_debug"] = {
        "score": final_score,
        "reasons": reasons
    }
    
    return final_score
