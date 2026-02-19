
def get_matched_items(required_list, resume_text):
    if not required_list:
        return []
    resume_lower = str(resume_text).lower()
    return [req for req in required_list if req.lower() in resume_lower]

def generate_explanation(jd_analysis, resume_metadata, rpl_score):
    """
    Generates a human-readable explanation for why this candidate was recommended.
    """
    resume_str = str(resume_metadata)
    
    matched_core = get_matched_items(jd_analysis.get("core_signals", []), resume_str)
    matched_support = get_matched_items(jd_analysis.get("supporting_signals", []), resume_str)
    checkpoints = jd_analysis.get("interview_checkpoints", [])
    
    # Determine Status
    if rpl_score >= 70:
        conclusion = "서류 전형을 무난히 통과할 것으로 예상되는 **강력 추천** 인재입니다."
    elif rpl_score >= 55:
        conclusion = "핵심 역량은 보유하고 있으나, 일부 검증이 필요한 **면접 추천** 인재입니다."
    else:
        conclusion = "일부 요건이 미비하나, 맥락적으로 검토해볼 가치가 있습니다."
        
    explanation = "이 후보자를 추천한 평가는 다음과 같습니다.\n\n"
    
    # 1. Core
    if matched_core:
        explanation += f"**1️⃣ 핵심 요건 충족**\n"
        explanation += f"- 이력서에서 **{', '.join(matched_core[:3])}** 등의 핵심 역량이 확인되었습니다.\n\n"
    else:
        explanation += f"**1️⃣ 핵심 요건 부족**\n"
        explanation += f"- 주요 요구 역량이 이력서에 명시되지 않았습니다.\n\n"
        
    # 2. Support
    if matched_support:
        explanation += f"**2️⃣ 가점 요소 (우대사항)**\n"
        explanation += f"- **{', '.join(matched_support[:3])}** 경험이 있어 실무 적응이 빠를 것으로 보입니다.\n\n"
        
    # 3. Checkpoints
    if checkpoints:
        explanation += f"**3️⃣ 면접 검증 포인트**\n"
        explanation += f"- **{', '.join(checkpoints[:3])}** 관련 경험은 면접에서 심층 확인이 필요합니다.\n\n"
        
    explanation += f"👉 **종합 의견**: {conclusion}"
    
    return explanation
