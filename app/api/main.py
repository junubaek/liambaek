from fastapi import FastAPI, Depends, HTTPException
from typing import Dict, List
from app.engine.matcher import Scorer
from headhunting_engine.matching.hybrid_search_v6_2 import HybridSearchV62
from connectors.pinecone_api import PineconeClient
from connectors.openai_api import OpenAIClient
from connectors.gemini_api import GeminiClient
import json
import os

app = FastAPI(title="AI Headhunting Engine v6.2-D (Deterministic)")

# Initialize global clients for performance
with open("secrets.json", "r") as f:
    SECRETS = json.load(f)

PC_HOST = SECRETS.get("PINECONE_HOST", "").rstrip("/")
if not PC_HOST.startswith("https://"): PC_HOST = f"https://{PC_HOST}"

PINECONE = PineconeClient(SECRETS["PINECONE_API_KEY"], PC_HOST)
OPENAI = OpenAIClient(SECRETS["OPENAI_API_KEY"])
GEMINI = GeminiClient(SECRETS["GEMINI_API_KEY"])
ONTOLOGY_PATH = 'headhunting_engine/universal_ontology.json'
DB_PATH = 'headhunting_engine/data/analytics.db'

HYBRID_ENGINE = HybridSearchV62(DB_PATH, PINECONE, OPENAI, ONTOLOGY_PATH, gemini_client=GEMINI)

@app.get("/")
def read_root():
    return {"status": "AI Talent Intelligence OS v6.2-D (Deterministic) Active"}

@app.post("/match/hybrid")
def hybrid_match(jd_text: str, top_k: int = 10):
    """
    [v6.2-VS] Production Hybrid Search Endpoint.
    """
    try:
        results = HYBRID_ENGINE.run(jd_text, top_k=top_k)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/match", response_model=Dict)
def match_candidate(jd_data: Dict, candidate_data: Dict):
    # Legacy endpoint updated to v6.2 logic
    scorer = Scorer()
    score, breakdown = scorer.calculate_score(
        candidate_data.get("patterns", []),
        context_data=jd_data,
        candidate_id=candidate_data.get("id")
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
