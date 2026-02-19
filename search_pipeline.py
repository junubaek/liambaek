from typing import List, Dict, Any, Tuple
from filters import HardFilter, MatrixFilter
from matrices import get_matrix_for_role

class SearchPipeline:
    def __init__(self, pinecone_client, open_ai_client):
        self.pc = pinecone_client
        self.ai = open_ai_client
        self.hard_filter = HardFilter()
        
    def run(self, jd_context: Dict[str, Any], query_text: str, top_k: int = 100, query_vector: List[float] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        logs = []
        logs.append(f"PIPELINE: Start (Query: {query_text[:50]}...)")
        
        # Verify Vector
        if not query_vector:
            logs.append("PIPELINE: Generating embedding internally...")
            query_vector = self.ai.embed_content(query_text)
            
        if not query_vector:
            logs.append("ERROR: Failed to generate embedding query.")
            return [], logs

        # Stage 1: Broad Retrieval
        raw_results = self.pc.query(query_vector, top_k=top_k) # Pass vector here
        candidates = self._convert_pinecone_results(raw_results)
        logs.append(f"PIPELINE: Stage 1 (Retrieval) -> {len(candidates)} candidates")
        
        if not candidates:
            return [], logs

        # Stage 2: Hard Filters
        candidates, hf_logs = self.hard_filter.apply(candidates, jd_context)
        logs.extend(hf_logs)
        
        if not candidates:
            return [], logs

        # Stage 3: Matrix Scoring
        matrix = get_matrix_for_role(jd_context)
        logs.append(f"PIPELINE: Selected Matrix -> {matrix.name}")
        
        matrix_filter = MatrixFilter(matrix)
        candidates, mf_logs = matrix_filter.apply(candidates, jd_context)
        logs.extend(mf_logs)
        
        # [v3.0] Stage 4: Strict Ranking (Composite Score)
        # Score = (Vector * 100) + Matrix - Penalty
        for cand in candidates:
            v_score = cand.get('vector_score', 0) * 100
            m_score = cand.get('matrix_score', 0)
            penalty = cand.get('filter_penalty', 0)
            
            final_score = v_score + m_score - penalty
            cand['final_score'] = final_score
            
            # Log significant penalties
            if penalty > 0:
                 logs.append(f"RANKING: {cand.get('id')} Final={final_score:.1f} (Vec={v_score:.1f} + Mat={m_score} - Pen={penalty})")

        # Sort by Final Score descending
        candidates.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        # Cutoff (optional, but let's keep top 50 for App to process)
        # candidates = candidates[:50] 
        
        # Stage 5: AI Rerank (Placeholder - Return top candidates to App)
        # In full refactor, AI Rerank would move here. For now, we return candidates to App.
        
        return candidates, logs

    def _convert_pinecone_results(self, res) -> List[Dict[str, Any]]:
        """Converts Pinecone response to internal candidate list format"""
        candidates = []
        if res and 'matches' in res:
            for m in res['matches']:
                candidates.append({
                    "id": m['id'],
                    "score": m['score'],
                    "data": m['metadata'],
                    "vector_score": m['score']
                })
        return candidates
