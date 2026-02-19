import streamlit as st
from resume_scoring import calculate_rpl, calculate_pass_probability
from explanation_engine import generate_explanation

class SearchPipelineV3:
    def __init__(self, pinecone_client):
        self.pc = pinecone_client

    def run(self, jd_analysis, query_vector, top_k=300):
        """
        Executes the screening-oriented search pipeline.
        Returns: (final_results, trace_log)
        """
        trace = {
            "stage1_retrieved": 0,
            "stage2_survivors": 0,
            "stage3_scored": 0,
            "stage4_final": 0
        }

        # ---------------------------
        # Stage 1: Broad Recall
        # ---------------------------
        try:
            # Assume 'pc' is the Pinecone index object or wrapper
            # If wrapper, use self.pc.query. If raw index, use self.pc.query
            # Based on app.py usage, it seems 'pinecone' var is used directly.
            # We'll assume the caller passes the 'index' object as pinecone_client
            
            # Ensure query_vector is list
            if hasattr(query_vector, "tolist"):
                query_vector = query_vector.tolist()
            
            raw = self.pc.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
                namespace=""
            )
        except Exception as e:
            print(f"Pipeline V3 Error (Vector Search): {e}")
            return [], trace

        if not raw or "matches" not in raw:
            return [], trace

        candidates = raw["matches"]
        trace["stage1_retrieved"] = len(candidates)
        
        # ---------------------------
        # Stage 2: Explicit Disqualifier ONLY
        # ---------------------------
        disqualifiers = jd_analysis.get("explicit_disqualifiers", [])
        
        filtered = []
        for c in candidates:
            resume_text = str(c.get("metadata", {}))
            
            # Simple substring check for disqualifiers
            is_disqualified = False
            for d in disqualifiers:
                if d.lower() in resume_text.lower():
                    is_disqualified = True
                    break
            
            if is_disqualified:
                continue  # ❗ Explicitly disqualified
                
            filtered.append(c)
            
        trace["stage2_survivors"] = len(filtered)

        # ---------------------------------------
        # Stage 3: RPL Scoring (Resume Pass Likelihood) & Explanation
        # ---------------------------------------
        final_results = []
        for candidate in filtered:
            data = candidate.get("metadata", {})
            cand_id = candidate.get("id")
            
            # [V3.4] Hybrid Scoring: Pass vector_score for semantic baseline
            vec_score = candidate.get('score', 0) # Use 'score' from Pinecone match as vector_score
            rpl_score = calculate_rpl(jd_analysis, data, vector_score=vec_score)
            pass_prob = calculate_pass_probability(rpl_score)
            
            # Prepare candidate dict for final results
            processed_candidate = {
                "id": cand_id,
                "data": data,
                "rpl_score": rpl_score,
                "pass_probability": pass_prob, # [New]
                "vector_score": vec_score,
                "explanation": None, # Initialize explanation as None
                "ai_eval_score": rpl_score # Map to existing UI field for compatibility
            }
            
            # [Step 4] Explanation Generation (Only for high potential or random sample)
            # Generating explanation for ALL 300 candidates is too slow.
            # Generate only if RPL > 40 (Screening Candidate) or we need to fill the list.
            if rpl_score >= 40:
                explanation = generate_explanation(jd_analysis, data, rpl_score) # Pass rpl_score to explanation
                processed_candidate['explanation'] = explanation
                final_results.append(processed_candidate)
            elif len(final_results) < 50: # Ensure we have at least some results even if low score
                explanation = generate_explanation(jd_analysis, data, rpl_score) # Pass rpl_score to explanation
                processed_candidate['explanation'] = explanation
                final_results.append(processed_candidate)

        trace["stage3_scored"] = len(final_results)

        # ---------------------------
        # Stage 4: Sort
        # ---------------------------
        # Sort by RPL Score descending
        final_results.sort(key=lambda x: x["rpl_score"], reverse=True)
        
        trace["stage4_final"] = len(final_results)

        return final_results, trace
