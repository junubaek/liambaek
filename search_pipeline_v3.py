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
            
            # Wrapper: query(self, vector, top_k=10, filter_meta=None, namespace="ns1")
            # It internally sets includeMetadata=True
            
            # [V4.2] Dimensionality Check & Namespace Fix
            # The index is 768 dimensions (found via debug).
            # If query_vector is 1536, we MUST truncate or the query will fail.
            if len(query_vector) == 1536:
                # Simple truncation (works for OpenAI new embeddings)
                query_vector = query_vector[:768]
                print("LOG: Truncated query vector from 1536 to 768 dim.")

            print("=" * 60)
            print("[DEBUG] Pinecone Query")
            print(f"Query Vector (first 10): {query_vector[:10]}")
            print(f"Query Vector Dimension: {len(query_vector)}")
            print(f"Namespace: ns1")
            print("=" * 60)

            raw = None
            try:
                # [V4.2] Primary Namespace: "ns1"
                # Debugging revealed data is in "ns1" (8000+ vectors).
                raw = self.pc.query(
                    vector=query_vector,
                    top_k=top_k,
                    namespace="ns1"
                )
            except TypeError as e:
                 # Fallback for old/custom client
                 # Try without namespace for older clients
                 print(f"Pipeline V3 Warning (TypeError): {e}. Retrying without namespace.")
                 raw = self.pc.query(
                    vector=query_vector,
                    top_k=top_k
                )

            except Exception as e_inner:
                print(f"Pipeline V3 Warning (Namespace 'ns1'): {e_inner}")
                trace["warning"] = f"ns1 failed: {e_inner}"

            print("=" * 60)
            print("[DEBUG] Pinecone Response")
            if raw and "matches" in raw:
                print(f"Matches Found: {len(raw['matches'])}")
                if raw['matches']:
                    print(f"Top Score: {raw['matches'][0].get('score')}")
                    print(f"Top Match ID: {raw['matches'][0].get('id')}")
            else:
                print("Matches Found: 0 or Error")
            print("=" * 60)

            # Fallback 1: Try Default Namespace ("") if ns1 failed
            if not raw or not raw.get("matches"):
                 try:
                    print("LOG: Fallback to namespace ''")
                    raw = self.pc.query(
                        vector=query_vector,
                        top_k=top_k,
                        namespace=""
                    )
                 except Exception: pass
                 
            # Fallback 2: Try None (some libs treat None as default)
            if not raw or not raw.get("matches"):
                 try:
                    print("LOG: Fallback to namespace None")
                    raw = self.pc.query(
                        vector=query_vector,
                        top_k=top_k,
                        namespace=None
                    )
                 except Exception: pass

        except Exception as e:
            print(f"Pipeline V3 Error (Vector Search): {e}")
            trace["error"] = str(e) # Capture error for UI
            return [], trace

        if not raw:
            trace["error"] = "Pinecone Query returned None"
            return [], trace
            
        if "matches" not in raw:
            trace["error"] = f"Pinecone response missing 'matches': {raw.keys()}"
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
            try:
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
            except Exception as e:
                print(f"[Warning] Candidate processing failed: {e}")
                continue

        trace["stage3_scored"] = len(final_results)

        # ---------------------------
        # Stage 4: Sort
        # ---------------------------
        # Sort by RPL Score descending
        final_results.sort(key=lambda x: x["rpl_score"], reverse=True)
        
        trace["stage4_final"] = len(final_results)

        return final_results, trace
