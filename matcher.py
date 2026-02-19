
import json
import argparse
from connectors.gemini_api import GeminiClient
from connectors.pinecone_api import PineconeClient
from connectors.openai_api import OpenAIClient
from feedback_loop import FeedbackLoop
from feedback_weight import calculate_feedback_weight
from jd_confidence import estimate_jd_confidence
from search_strategy import decide_search_strategy
from classification_rules import get_role_cluster

# --- SCORING WEIGHTS (Configurable) ---
# --- SCORING WEIGHTS (Configurable) ---
WEIGHTS = {
    "VECTOR_RELEVANCE": 0.60,  # Semantic Match
    "QUANT_TIER": 0.10,        # Balanced to sum ~1.0
    "QUANT_SKILL": 0.20,       # Increased as requested
    "QUANT_EXP": 0.10
}

def extract_jd_semantics(openai_client, jd_text):
    """
    Extracts structured semantic information from the Job Description
    to build a high-quality query for the Embedding Model.
    """
    prompt = f"""
    Analyze the following Job Description and extract key information for a Headhunter Search Query.
    
    [JOB DESCRIPTION]
    {jd_text[:3000]}
    
    [INSTRUCTIONS]
    Extract the following fields concisely:
    - Primary Role (e.g. Backend Engineer, Product Designer)
    - Seniority Level (e.g. Junior, Senior, Lead, 10+ years)
    - Min Years of Experience (Integer, e.g. 3, 5, 7. If unsure/open, use 0)
    - Domain / Industry (e.g. Fintech, eCommerce, Semiconductor)
    - Must-Have Skills (Comma separated, only the most critical)
    - Nice-to-Have Skills (Comma separated)
    - Search Queries (Generate 3 distinct search queries for vector search:
        1. Direct technical query
        2. Functional/Role-based query
        3. Domain/Industry-focused query)
    
    Output in STRICT JSON format with keys: 
    "primary_role", "seniority", "min_years", "domain", "must_skills", "nice_skills", "search_queries"
    """
    try:
        resp = openai_client.get_chat_completion("You are a smart JSON extractor.", prompt)
        clean = resp.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        return data
    except:
        return {}

def calculate_final_score(vector_score, metadata):
    # ... (Keep existing implementation)
    tier_score = float(metadata.get('company_tier_score', 0))
    skill_score = float(metadata.get('skill_score', 0))
    exp_score = float(metadata.get('experience_bonus', 0))
    
    norm_tier = min(1.0, tier_score / 10.0)
    norm_skill = min(1.0, skill_score / 15.0)
    norm_exp = min(1.0, exp_score / 20.0)
    
    # 2. Weighted Sum
    final_score = (
        (vector_score * WEIGHTS["VECTOR_RELEVANCE"]) +
        (norm_tier * WEIGHTS["QUANT_TIER"]) +
        (norm_skill * WEIGHTS["QUANT_SKILL"]) +
        (norm_exp * WEIGHTS["QUANT_EXP"])
    )
    
    return final_score * 100

def deduplicate_results(results_list):
    """Simple deduplication by ID, keeping the highest score."""
    seen = {}
    final_list = []
    # results_list is a list of lists of matches
    for batch in results_list:
        for match in batch:
            mid = match['id']
            if mid not in seen:
                seen[mid] = match
                final_list.append(match)
            else:
                # Specify strategy: keep max score?
                if match['score'] > seen[mid]['score']:
                    seen[mid] = match
                    # Update in final_list (inefficient list scan, but fine for small N)
                    for i, item in enumerate(final_list):
                        if item['id'] == mid:
                            final_list[i] = match
                            break
    return final_list

def search_candidates(jd_text, limit=5):
    # 1. Load Secrets
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
        
    # 2. Init Clients
    pc_host = secrets.get("PINECONE_HOST", "")
    if not pc_host.startswith("https://"):
        pc_host = f"https://{pc_host}"

    pinecone = PineconeClient(secrets["PINECONE_API_KEY"], pc_host)
    openai = OpenAIClient(secrets["OPENAI_API_KEY"])
    
    print(f"Analyzing JD (Length: {len(jd_text)} chars)...")
    
    # 2.1 Extract Semantics & Hard Filters
    print("  -> Extracting semantic requirements & filters...")
    semantic_data = extract_jd_semantics(openai, jd_text)
    
    # --- [PHASE 3] JD Confidence & Strategy ---
    # 1. Calculate Confidence
    jd_struct_for_conf = {
        "explicit_skills": semantic_data.get('must_skills', []),
        "title_candidates": [semantic_data.get('primary_role', '')],
        "domain_clues": [semantic_data.get('domain', '')],
        "seniority_clues": [semantic_data.get('seniority', '')]
    }
    confidence_score = estimate_jd_confidence(jd_struct_for_conf)
    print(f"  -> JD Confidence Score: {confidence_score:.2f}")
    
    # 2. Decide Strategy
    strategy = decide_search_strategy(confidence_score)
    print(f"  -> Search Strategy: {strategy['mode'].upper()} ({strategy['description']})")
    
    # 3. Role Cluster Filtering
    role_cluster = get_role_cluster(semantic_data.get('primary_role', 'Unclassified'))
    print(f"  -> Target Role Cluster: {role_cluster}")
    
    # HARD FILTER: Min Years
    min_years = int(semantic_data.get('min_years', 0))
    filter_meta = {}
    if min_years > 0:
        print(f"  -> Applying Hard Filter: Min {min_years} Years Experience")
        # [Phase 2] Use robust extracted metadata first, fallback to basic
        # Use $or to catch either new 'total_years' or old field if exists
        filter_meta['total_years'] = {"$gte": min_years}

    # CLUSTER FILTER (Optional - Strategy Dependent)
    if role_cluster != "Unclassified":
         # Check if we should apply this hard filter? 
         # Let's apply it, but allow fallback if 0 results (TODO)
         filter_meta['role_cluster'] = {"$eq": role_cluster}
         print(f"  -> Applying Cluster Filter: {role_cluster}")

    # 3. Ensemble Search (Multi-Query)
    queries = semantic_data.get('search_queries', [jd_text])
    if isinstance(queries, str): queries = [queries] # handle error case
    
    # Ensure we use the Semantic Constructed Query as one of them if not present
    constructed_query = f"Role: {semantic_data.get('primary_role')} Skills: {semantic_data.get('must_skills')}"
    queries.append(constructed_query)
    
    # Deduplicate queries just in case
    queries = list(set(queries))
    
    # Use Strategy Parameters
    top_k_param = strategy['top_k']
    print(f"  -> Running Ensemble Search (Top-K: {top_k_param}) with {len(queries)} strategies...")
    
    all_matches = []
    
    for q_idx, query_text in enumerate(queries):
        # Embed
        q_vec = openai.embed_content(query_text)
        if not q_vec: continue
        
        # Search with Filter
        try:
            res = pinecone.query(q_vec, top_k=top_k_param, filter_meta=filter_meta)
            if res and 'matches' in res:
                all_matches.append(res['matches'])
        except Exception as e:
            print(f"    [!] Search failed for query '{query_text[:20]}...': {e}")
            
    # Deduplicate Ensemble Results
    unique_matches = deduplicate_results(all_matches)
    print(f"  -> Ensemble retrieved {len(unique_matches)} unique candidates.")
    
    if not unique_matches:
        print("No matches found given the criteria.")
        return

    # 4. Apply Feedback Loop (Vector Boosting)
    # Load Feedback Log
    feedback_adjustments = {}
    try:
        with open("feedback_log.json", "r", encoding="utf-8") as f:
            fb_data = json.load(f)
            # Pre-calculate adjustments
            for item in fb_data:
                cand_name = item.get("candidate")
                # decay weight
                base_w = 1.0 if item.get("type") == "positive" else -1.0
                decayed_w = calculate_feedback_weight(base_w, item.get("timestamp"))
                
                # Aggregate (sum up if multiple feedbacks)
                if cand_name:
                    feedback_adjustments[cand_name] = feedback_adjustments.get(cand_name, 0) + decayed_w
    except:
        pass # No feedback file or error
        
    print(f"  -> Applied Feedback Adjustment for {len(feedback_adjustments)} candidates.")

            
    # 5. Hybrid Re-ranking
    ranked_candidates = []
    for match in unique_matches:
        vec_score = match['score'] # Cosine Similarity
        meta = match['metadata']
        
        hybrid_score = calculate_final_score(vec_score, meta)
        
        # Apply Feedback Adjustment
        # Boost/Penalty: +1.0 weight -> +10 score (approx)
        name = meta.get('name', 'Unknown')
        adj = feedback_adjustments.get(name, 0)
        
        # Logarithmic or Linear scaling? Linear for now.
        # If decayed weight is 0.5 (half-life), score boost is +5.
        if adj != 0:
            boost = adj * 10.0
            hybrid_score += boost
             # Ensure bounds
            hybrid_score = max(0, min(100, hybrid_score))
        
        ranked_candidates.append({
            "name": meta.get('name', 'Unknown'),
            "final_score": hybrid_score,
            "vector_score": vec_score,
            "quant_scores": {
                "tier": meta.get('company_tier_score', 0),
                "skill": meta.get('skill_score', 0)
            },
            "summary": str(meta.get('position', '')) + " / " + ", ".join(meta.get('domain', []) if isinstance(meta.get('domain'), list) else [str(meta.get('domain', ''))]),
            "id": match['id']
        })

    # Sort by Final Score
    ranked_candidates.sort(key=lambda x: x['final_score'], reverse=True)
    
    # 6. Output Results
    print(f"\n{'RANK':<5} | {'SCORE':<6} | {'NAME':<20} | {'VEC_SIM':<7} | {'TIER':<5} | {'INFO'}")
    print("-" * 80)
    for i, cand in enumerate(ranked_candidates[:strategy['rerank_top_n']]): # Use dynamic limit
        print(f"{i+1:<5} | {cand['final_score']:<.1f}   | {cand['name']:<20} | {cand['vector_score']:.3f}   | {cand['quant_scores']['tier']:<5} | {cand['summary']}")
        
    return ranked_candidates # Return for app.py use

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Resume Matcher")
    parser.add_argument("--jd", type=str, help="Job Description Text (quoted)", required=False)
    parser.add_argument("--file", type=str, help="Path to JD text file", required=False)
    
    args = parser.parse_args()
    
    jd_content = ""
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                jd_content = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            exit(1)
    elif args.jd:
        jd_content = args.jd
    else:
        # Default Mock JD if no input
        pass
        # print("No input provided. Using Default Mock JD (Ethernet Firmware).")
        # jd_content = """
        # Position: Ethernet Firmware Engineer
        # Required: 5+ years experience, Layer 2/3 protocols, VLAN, STP.
        # Embedded C/C++, RoCE (RDMA) implementation.
        # """
    
    if jd_content:
        search_candidates(jd_content)
