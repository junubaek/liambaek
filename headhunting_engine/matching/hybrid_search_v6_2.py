import os
import sys
import json
import sqlite3
import hashlib
from typing import List, Dict, Any, Tuple

# Path Setup
sys.path.append(os.getcwd())
from headhunting_engine.matching.scorer import Scorer
from headhunting_engine.jd_parser.jd_parser_v3 import JDParserV3
import json
from connectors.pinecone_api import PineconeClient
from connectors.openai_api import OpenAIClient
from connectors.gemini_api import GeminiClient

class HybridSearchV62:
    """
    v6.2-VS Hybrid Search Implementation
    Pipeline: Pre-Filter -> Ontology Score (80%) -> Semantic Booster (20%)
    """
    def __init__(self, db_path: str, pinecone_client, openai_client, ontology_path: str, gemini_client=None):
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
        
        self.db_path = db_path
        self.pinecone = pinecone_client
        self.openai = openai_client
        self.scorer = Scorer()
        
        # [v6.2-VS] User preference: Use Gemini for JD analysis if available
        analysis_client = gemini_client if gemini_client else openai_client
        self.jd_parser = JDParserV3(analysis_client, ontology_path)
        
        pc_host = secrets.get("PINECONE_HOST", "").rstrip("/")
        if not pc_host.startswith("https://"): pc_host = f"https://{pc_host}"
        
        self.pc = PineconeClient(secrets["PINECONE_API_KEY"], pc_host)
        self.oa = OpenAIClient(secrets["OPENAI_API_KEY"])
        self.scorer = Scorer()
        self.db_path = 'headhunting_engine/data/analytics.db'
        self.namespace = "v6.2-vs"

    def _get_ascii_id(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]

    def run(self, jd_text: str, filters: Dict[str, Any] = None, top_k: int = 50) -> List[Dict[str, Any]]:
        print(f"🔍 Starting Hybrid Search v6.2-VS (JD: {len(jd_text)} chars)...")
        
        # 1. Pre-Filter (SQLite Hard Gate)
        # For simplicity in this implementation, we fetch filtered candidates from SQLite
        # In a real high-scale scenario, this would use indexed columns.
        candidates = self._fetch_filtered_candidates(filters)
        print(f"  Step 1: Pre-filtered {len(candidates)} candidates from local DB.")
        
        if not candidates: return []

        # 2. Ontology Scoring (Deterministic - 80% Weight)
    def run(self, jd_text: str, top_k: int = 10) -> List[Dict]:
        """
        [v6.2.3 Hardened] Executes the 3-Step Funnel:
        1. Pre-filter by Sector/Hard Constraints (SQLite)
        2. Ontology Scoring + 0-Coverage Exclusion (80%)
        3. Semantic Booster (20%)
        """
        # STEP 1: Extract JD Signals via Gemini
        jd_context = self.jd_parser.parse_jd(jd_text)
        
        # [v6.2.3] Hard Gate: Fetch only relevant candidates from DB
        candidates = self._pre_filter(jd_context)
        
        # STEP 2 & 3: Ontology Scoring 
        scored_candidates = []
        unique_ids = set()
        
        for cand in candidates:
            if cand['id'] in unique_ids: continue # [v6.2.3] Deduplication
            
            cand_details = self._get_candidate_matching_data(cand['id'])
            if not cand_details: continue
            
            final_ontology_score, breakdown = self.scorer.calculate_score(cand_details, jd_context)
            
            # [v6.2.3] HARD GATE: Drop 0-coverage candidates immediately
            if breakdown.get("pattern_coverage", 0) <= 0:
                continue
            
            unique_ids.add(cand['id'])
            scored_candidates.append({
                "id": cand['id'],
                "name": cand['name'],
                "ontology_score": final_ontology_score,
                "coverage": breakdown.get("pattern_coverage", 0),
                "details": cand_details
            })
        
        if not scored_candidates: return []
        
        # Sort and take top 50 for Vector Boosting
        scored_candidates.sort(key=lambda x: x['ontology_score'], reverse=True)
        candidates_to_boost = scored_candidates[:50]
        
        # [v6.2.3] Step 4: Semantic Booster
        jd_vector = self.oa.embed_content(jd_text)
        
        final_results = []
        for cand in candidates_to_boost:
            vector_id = self._get_vector_id(cand['name'])
            semantic_score = self._get_semantic_score(vector_id, jd_vector)
            
            # 80/20 Blend
            final_score = (cand['ontology_score'] * 0.8) + (semantic_score * 100 * 0.2)
            
            final_results.append({
                "id": cand['id'],
                "name": cand['name'],
                "final_score": round(min(100.0, final_score), 2),
                "ontology_score": round(cand['ontology_score'], 2),
                "semantic_score": round(semantic_score * 100, 2),
                "coverage": round(cand.get("coverage", 0), 2)
            })
            
        final_results.sort(key=lambda x: x['final_score'], reverse=True)
        return final_results[:top_k]

    def _pre_filter(self, jd_context: Dict) -> List[Dict]:
        """
        [v6.2.4 Fixed] Rigorous Hard Filtering via SQLite.
        """
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Target Sectors
        target_sectors = [jd_context["primary_sector"]] + jd_context.get("secondary_sectors", [])
        
        # 2. Strict Sector + Distinct Query
        # Using correct table 'candidate_snapshots' and column 'data_json'
        query = "SELECT DISTINCT id, name FROM candidate_snapshots WHERE 1=1"
        params = []
        
        if target_sectors:
            sector_clauses = []
            for s in target_sectors:
                # Search inside data_json for primary_sector
                sector_clauses.append("data_json LIKE ?")
                params.append(f'%"primary_sector": "{s}"%')
            query += f" AND ({' OR '.join(sector_clauses)})"
        
        query += " LIMIT 500"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [{"id": row[0], "name": row[1]} for row in rows]

    def _get_candidate_matching_data(self, cand_id: int) -> Dict:
        """
        [v6.2.4 Fixed] Fetches data_json from candidate_snapshots.
        """
        import sqlite3
        import json
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT data_json FROM candidate_snapshots WHERE id = ?", (cand_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return json.loads(row[0])
        return {}

if __name__ == "__main__":
    # Initialize clients and paths
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    
    pc_host = secrets.get("PINECONE_HOST", "").rstrip("/")
    if not pc_host.startswith("https://"): pc_host = f"https://{pc_host}"
    
    pinecone_client = PineconeClient(secrets["PINECONE_API_KEY"], pc_host)
    openai_client = OpenAIClient(secrets["OPENAI_API_KEY"])
    gemini_client = GeminiClient(secrets["GEMINI_API_KEY"])
    db_path = 'headhunting_engine/data/analytics.db'
    ontology_path = 'headhunting_engine/data/ontology.json' 

    searcher = HybridSearchV62(db_path, pinecone_client, openai_client, ontology_path, gemini_client=gemini_client)
    # Test run
    results = searcher.run("Senior Backend Engineer with AWS and Python experience")
    for i, r in enumerate(results[:5]):
        print(f"{i+1}. {r['name']} - Score: {r['final_score']} (Ontology: {r['ontology_score']})")
