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
        Executes the 3-Step Funnel:
        1. Pre-filter by Hard Constraints
        2. Ontology Scoring (80%)
        3. Semantic Booster (20%)
        """
        # STEP 1: Extract JD Signals via Gemini (Cross-Sector Support)
        jd_context = self.jd_parser.parse_jd(jd_text)
        
        # [v6.2-VS+] Cross-Sector Matching Logic
        # The jd_context now contains primary_sector, secondary_sectors, etc.
        candidates = self._pre_filter(jd_context)
        
        # STEP 3: Ontology Scoring (80%)
        scored_candidates = []
        for cand in candidates:
            # We assume candidates in DB already have 'parsed_data' (patterns, sectors)
            # If not, we would need to join or fetch from another table
            # For this implementation, we use a helper to get candidate details
            cand_details = self._get_candidate_matching_data(cand['id'])
            if not cand_details: continue
            
            ontology_score = self.scorer.calculate_score(cand_details, jd_context)
            scored_candidates.append({
                "id": cand['id'],
                "name": cand['name'],
                "ontology_score": ontology_score
            })
        
        # Sort by ontology score to get candidates for semantic boosting
        scored_candidates.sort(key=lambda x: x['ontology_score'], reverse=True)
        # Take top 50 for vector boosting to save costs/latency
        candidates_to_boost = scored_candidates[:50]
        
        # STEP 4: Semantic Booster (20%)
        # JD Embedding
        jd_vector = self.openai.embed_content(jd_text)
        
        final_results = []
        for cand in candidates_to_boost:
            # Fetch vector similarity from Pinecone
            # IDs in Pinecone are SHA-256 hashes of names
            vector_id = self._get_vector_id(cand['name'])
            
            # Since Pinecone 'fetch' doesn't give similarity score to a query, 
            # we use 'query' with a filter for the specific ID to get the score.
            semantic_score = self._get_semantic_score(vector_id, jd_vector)
            
            # Final Blend: 80% Ontology + 20% Semantic
            final_score = (cand['ontology_score'] * 0.8) + (semantic_score * 0.2)
            
            final_results.append({
                "id": cand['id'],
                "name": cand['name'],
                "final_score": round(final_score, 2),
                "ontology_score": round(cand['ontology_score'], 2),
                "semantic_score": round(semantic_score * 100, 2), # Scale to 0-100 for display
                "details": cand_details
            })
            
        final_results.sort(key=lambda x: x['final_score'], reverse=True)
        return final_results[:top_k]

    def _get_vector_id(self, name: str) -> str:
        import hashlib
        return hashlib.sha256(name.encode('utf-8')).hexdigest()

    def _get_semantic_score(self, vector_id: str, jd_vector: List[float]) -> float:
        """
        Calculates cosine similarity between JD vector and Candidate vector.
        """
        try:
            # In production, querying with filter is more efficient than fetching and calculating manually
            resp = self.pinecone.query(
                namespace="v6.2-vs",
                vector=jd_vector,
                filter={"name": {"$eq": vector_id}}, # This assumes we stored the hashed name as metadata or ID
                top_k=1,
                include_values=False
            )
            if resp and resp['matches']:
                return resp['matches'][0]['score']
        except Exception as e:
            print(f"⚠️ Semantic score error for {vector_id}: {e}")
        return 0.5 # Neutral fallback

    def _pre_filter(self, jd_context: Dict) -> List[Dict]:
        """
        Hard Filtering (SQLite) - Location, Degree, etc.
        """
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Simplified filtering for PoC
        # In reality, this would be a complex SQL query based on jd_context['hard_constraints']
        query = "SELECT id, name FROM candidates LIMIT 500" 
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        return [{"id": row[0], "name": row[1]} for row in rows]

    def _get_candidate_matching_data(self, cand_id: int) -> Dict:
        """
        Fetches parsed candidate data for scoring.
        """
        import sqlite3
        import json
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT parsed_data FROM candidates WHERE id = ?", (cand_id,))
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
