
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
    [V6.0 Update]
    1. Keyword Sensitivity: Changed Max(Keyword, Semantic) to Weighted Average to ensure
       that missing verifiable keywords actually decreases the score.
    2. Legacy Compatibility: Use 'must', 'nice', 'domain' as fallbacks.
    """
    resume_str = str(resume_metadata).lower()
    
    # 1. Core Signals (Max 60) - Prioritize 'must' (user editable)
    core_signals = jd_analysis.get("must") or jd_analysis.get("core_signals") or []
    
    # Calculate Keyword Match Ratio
    hit_count = 0
    if core_signals:
        for req in core_signals:
            if str(req).lower() in resume_str:
                hit_count += 1
        keyword_match_rate = hit_count / len(core_signals)
    else:
        keyword_match_rate = 0.0
        
    # Normalize Vector Score (0.65 ~ 0.85 range)
    sem_score = max(0, (vector_score - 0.65) / 0.2)
    sem_score = min(sem_score, 1.0)
    
    # [V6.0] Weighted Core Rate: Keywords are 70%, Semantic is 30%
    # This ensures that even if vector similarity is high, missing keywords PULLS DOWN the score.
    if core_signals:
        final_core_rate = (keyword_match_rate * 0.7) + (sem_score * 0.3)
    else:
        # If no core signals (unlikely), rely on semantic
        final_core_rate = sem_score
    
    core_score = final_core_rate * 60
    
    # 2. Supporting Signals (Max 25) - Prioritize 'nice' (user editable)
    supporting_signals = jd_analysis.get("nice") or jd_analysis.get("supporting_signals") or []
    support_hits = 0
    if supporting_signals:
        for sig in supporting_signals:
            if str(sig).lower() in resume_str:
                support_hits += 1
        support_score = min(support_hits * 5, 25)
    else:
        support_score = 0
    
    # 3. Context Similarity (Max 10) - Prioritize 'domain' (user editable)
    context_signals = jd_analysis.get("domain") or jd_analysis.get("context_signals") or []
    context_hits = 0
    if context_signals:
        for sig in context_signals:
            if str(sig).lower() in resume_str:
                context_hits += 1
        context_score = min(context_hits * 3, 10)
    else:
        context_score = 0
    
    # 4. Refined Risk Penalty
    risk_penalty = 0 
    if core_signals and keyword_match_rate < 0.2:
        risk_penalty += 20 # Steeper penalty for very low keyword match

    # ... (Finance specialized bonus remains unchanged) ...
    jd_role = jd_analysis.get("canonical_role") or jd_analysis.get("role") or ""
    jd_role = str(jd_role).lower()
    
    if any(x in jd_role for x in ["finance", "fp&a", "재무", "회계", "accounting", "business analyst", "기획"]):
        finance_bonus = 0
        if any(x in resume_str for x in ["budget", "forecast", "p&l", "financial model", "예산", "손익"]):
            finance_bonus += 15
        if any(x in resume_str for x in ["excel", "sql", "data analysis", "bi", "데이터"]):
            finance_bonus += 10
        if any(x in resume_str for x in ["fp&a", "경영기획", "재무기획", "business analyst"]):
            finance_bonus += 10
        if "보험" in resume_str or "insurance" in resume_str or "fintech" in resume_str or "핀테크" in resume_str:
            finance_bonus += 5
            
        final_core_rate = min(1.0, final_core_rate + (finance_bonus / 100.0))
        core_score = final_core_rate * 60

    final_score = core_score + support_score + context_score - risk_penalty
    
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

