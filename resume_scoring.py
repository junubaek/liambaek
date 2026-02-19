
def match_ratio(required_list, resume_text):
    if not required_list:
        return 1.0
    
    resume_lower = str(resume_text).lower()
    hit_count = 0
    
    for req in required_list:
        # Simple substring match for now. Could be regex or fuzzy later.
        if req.lower() in resume_lower:
            hit_count += 1
            
    return hit_count / len(required_list)

def count_overlap(signal_list, resume_text):
    if not signal_list:
        return 0
        
    resume_lower = str(resume_text).lower()
    hit_count = 0
    
    for sig in signal_list:
        if sig.lower() in resume_lower:
            hit_count += 1
            
    return hit_count


def calculate_rpl(jd_analysis, resume_metadata, vector_score=0.0):
    """
    Calculates Resume Pass Likelihood (RPL) Score (0-100).
    Formula: Max(Core Match, Vector Score) * Weight + Supporting + Context
    
    [V3.4] Hybrid Scoring Update:
    - Pure keyword matching is too strict.
    - We now mix 'Vector Semantic Score' with 'Keyword Match Score'.
    - If Keyword Match is low but Vector Score is high (semantics), we trust Vector more.
    """
    resume_str = str(resume_metadata).lower()
    
    # 1. Core Signals (Max 60)
    core_signals = jd_analysis.get("core_signals", [])
    
    # Calculate Keyword Match Ratio
    hit_count = 0
    if core_signals:
        for req in core_signals:
            # [Relaxed] Substring match is okay, but we should handle partials better?
            # For now, stick to substring but trust vector score for "synonyms"
            if req.lower() in resume_str:
                hit_count += 1
        keyword_match_rate = hit_count / len(core_signals)
    else:
        keyword_match_rate = 0.0
        
    # [Hybrid Logic]
    # Vector Score is typically 0.7 ~ 0.85 for good matches.
    # Map Vector Score 0.75 -> 60 points (Full Core Score equivalent)
    # Map Vector Score 0.65 -> 30 points
    
    # Normalize Vector Score (0.65 ~ 0.85 range maps to 0.0 ~ 1.0 effectiveness)
    sem_score = max(0, (vector_score - 0.65) / 0.2) # 0.85 becomes 1.0
    sem_score = min(sem_score, 1.0)
    
    # Final Core Rate = Max(Keyword, Semantic)
    # If candidate says "Financial Planning" (Vector high) but misses "FP&A" (Keyword low), we use Vector.
    final_core_rate = max(keyword_match_rate, sem_score)
    
    core_score = final_core_rate * 60
    
    # 2. Supporting Signals (Max 25)
    # Keyword overlap is safer here as these are "Nice to haves"
    supporting_signals = jd_analysis.get("supporting_signals", [])
    support_hits = 0
    if supporting_signals:
        for sig in supporting_signals:
            if sig.lower() in resume_str:
                support_hits += 1
    support_score = min(support_hits * 5, 25)
    
    # 3. Context Similarity (Max 10)
    context_signals = jd_analysis.get("context_signals", [])
    context_hits = 0
    if context_signals:
        for sig in context_signals:
            if sig.lower() in resume_str:
                context_hits += 1
    context_score = min(context_hits * 3, 10)
    
    # 4. Refined Risk Penalty
    risk_penalty = 0 
    
    # [V4.0] FP&A / Finance Specialized Scoring (Bonus Matrix)
    # The user specifically requested this to fix "Zero Results" for Junior FP&A roles.
    # We check if the JD is for a Finance role, and if so, apply heuristic bonuses.
    jd_role = jd_analysis.get("canonical_role", "").lower()
    if any(x in jd_role for x in ["finance", "fp&a", "재무", "회계", "accounting", "business analyst", "기획"]):
        finance_bonus = 0
        # Keywords that imply competence but might be missing from "Must"
        if any(x in resume_str for x in ["budget", "forecast", "p&l", "financial model", "예산", "손익"]):
            finance_bonus += 15
        if any(x in resume_str for x in ["excel", "sql", "data analysis", "bi", "데이터"]):
            finance_bonus += 10
        if any(x in resume_str for x in ["fp&a", "경영기획", "재무기획", "business analyst"]):
            finance_bonus += 10
        if "보험" in resume_str or "insurance" in resume_str or "fintech" in resume_str or "핀테크" in resume_str:
            finance_bonus += 5
            
        # Apply bonus (Max 30 boost/cushion)
        final_core_rate = min(1.0, final_core_rate + (finance_bonus / 100.0))
        # Recalculate core score with boost
        core_score = final_core_rate * 60

    final_score = core_score + support_score + context_score + risk_penalty
    
    return max(10, min(100, int(final_score)))


def calculate_pass_probability(rpl_score):
    """
    Converts RPL Score (0-100) to a Probability Percentage.
    Based on User's requested tiers.
    """
    if rpl_score < 30:
        return 10
    elif rpl_score < 45:
        return 30
    elif rpl_score < 60:
        return 55
    elif rpl_score < 75:
        return 75
    else:
        return 90

