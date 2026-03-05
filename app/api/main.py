from fastapi import FastAPI, Depends, HTTPException
from typing import Dict, List
from app.engine.matcher import Scorer
from app.engine.risk_engine import JDRiskEngine
from app.engine.scarcity import ScarcityEngine

app = FastAPI(title="AI Headhunting Engine v5")
auth = AuthManager(secret_key="PHASE_5_SECURE_KEY")

@app.get("/")
def read_root():
    return {"status": "Universal Engine v5 Active"}

@app.post("/match", response_model=Dict)
def match_candidate(jd_data: Dict, candidate_data: Dict, token: str = Depends(auth.verify_token)):
    if not token:
        raise HTTPException(status_code=401, detail="Invalid Security Token")
    
    scorer = Scorer()
    score, breakdown = scorer.calculate_score(
        candidate_data.get("experience_patterns", []),
        context_data=jd_data
    )
    return {"candidate_id": candidate_data.get("id"), "score": score, "breakdown": breakdown}

@app.get("/analytics/risk")
def get_jd_risk(jd_id: str, domains: str = "GA_OPERATIONS", patterns: str = "", token: str = Depends(auth.verify_token)):
    if not token:
        raise HTTPException(status_code=401, detail="Invalid Security Token")
    
    scarcity = ScarcityEngine()
    risk_engine = JDRiskEngine(scarcity)
    
    domain_list = [d.strip() for d in domains.split(",")]
    pattern_list = [p.strip() for p in patterns.split(",")] if patterns else []
    
    # Analyze risk based on requested domains and patterns
    risk = risk_engine.predict_risk(domain_list, pattern_list)
    return {"jd_id": jd_id, "risk": risk}
