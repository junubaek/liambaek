
def decide_search_strategy(jd_confidence: float) -> dict:
    """
    Decides search strategy (Precision vs Recall) based on JD confidence.
    """
    # High Confidence -> Precision Mode
    # Use stricter filters, fewer results but higher quality
    if jd_confidence >= 0.7:
        return {
            "mode": "precision",
            "description": "High confidence JD. Using strict search.",
            "score_cutoff": 60,   
            "top_k": 300,          # [v3.0] Wide Funnel: 300
            "rerank_top_n": 50,   
            "match_weights": {
                 "vector": 0.5,
                 "skills": 0.3,   
                 "domain": 0.2
            }
        }
    
    # Low Confidence -> Recall Mode
    # Use broader search to avoid 0 results
    else:
        return {
            "mode": "recall",
            "description": "Ambiguous JD. Expanding search scope.",
            "score_cutoff": 30,   
            "top_k": 300,          # [v3.0] Wide Funnel: 300
            "rerank_top_n": 100,    
            "match_weights": {
                 "vector": 0.7,   
                 "skills": 0.15,
                 "domain": 0.15
            }
        }
