
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
    
    # 4. Risk Penalty (Softened)
    # Only penalize if we are sure it's a risk.
    # For now, remove risk penalty to avoid false negatives in Panic Mode.
    risk_penalty = 0 
    
    final_score = core_score + support_score + context_score + risk_penalty
    
    return max(10, min(100, int(final_score)))

