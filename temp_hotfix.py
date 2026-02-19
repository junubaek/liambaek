
def _safety_filter_hotfix(data: dict) -> dict:
    """
    [HOTFIX] Duplicate of JDAnalyzerV2._apply_safety_filter
    Forces removal of banned terms in app.py side in case of caching issues.
    """
    # 1. Hidden Signals (Ban Adjectives/Abstract Concepts)
    banned_hidden = [
        "스타트업 마인드", "Startup Mindset", "열정", "Passion", 
        "커뮤니케이션", "Communication", "적극적", "Proactive",
        "책임감", "Ownership", "성장", "Growth", "문제 해결 능력",
        "유연한 사고", "Flexible", "긍정적", "협업", "Teamwork"
    ]
    
    if "hidden_signals" in data:
        cleaned = []
        for signal in data["hidden_signals"]:
            is_banned = False
            sig_norm = signal.lower().replace(" ", "")
            for ban in banned_hidden:
                ban_norm = ban.lower().replace(" ", "")
                if ban_norm in sig_norm: 
                    is_banned = True
                    break
            if not is_banned:
                cleaned.append(signal)
        data["hidden_signals"] = cleaned
        
    # 2. Negative Signals (Ban "No X Experience" inferred from Preferences)
    if "negative_signals" in data:
        cleaned_neg = []
        for signal in data["negative_signals"]:
            # Heuristic: Drop "No [Industry] Experience" signals as they are usually hallucinations from Preferences
            if "경험" in signal and ("없음" in signal or "없는" in signal) and "신입" not in signal:
                    continue
            if "협업" in signal or "Teamwork" in signal or "소통" in signal:
                    continue
            cleaned_neg.append(signal)
        data["negative_signals"] = cleaned_neg
    
    return data
