
import json
import argparse
import os
from connectors.pinecone_api import PineconeClient
from connectors.openai_api import OpenAIClient
from jd_confidence import estimate_jd_confidence
from search_strategy import decide_search_strategy
from classification_rules import get_role_cluster
from jd_analyzer_v5 import JDAnalyzerV5

# --- SCORING WEIGHTS (Configurable) ---
WEIGHTS = {
    "VECTOR_RELEVANCE": 0.50,  # Semantic Match
    "PATTERN_MATCH": 0.20,     # Structured Experience Alignment (NEW)
    "QUANT_TIER": 0.10,
    "QUANT_SKILL": 0.10,
    "QUANT_EXP": 0.10
}

def calculate_final_score(vector_score, metadata, target_patterns):
    # 1. Base Scores
    tier_score = float(metadata.get('company_tier_score', 0))
    skill_score = float(metadata.get('skill_score', 0))
    exp_score = float(metadata.get('experience_bonus', 0))
    
    # 2. Pattern Match Calculation
    candidate_patterns = metadata.get('experience_patterns', [])
    if isinstance(candidate_patterns, str):
        try:
            candidate_patterns = json.loads(candidate_patterns)
        except:
            candidate_patterns = []
            
    pattern_match_count = 0
    if target_patterns and candidate_patterns:
        target_set = set(target_patterns)
        cand_set = set(candidate_patterns)
        matches = target_set.intersection(cand_set)
        pattern_match_count = len(matches)
        
    # Normalize Pattern Score: 1.0 if at least 2 patterns match, or proportional
    norm_pattern = min(1.0, pattern_match_count / 2.0) if target_patterns else 0.5 # Neutral if no patterns asked
    
    norm_tier = min(1.0, tier_score / 10.0)
    norm_skill = min(1.0, skill_score / 15.0)
    norm_exp = min(1.0, exp_score / 20.0)
    
    # 3. Weighted Sum
    final_score = (
        (vector_score * WEIGHTS["VECTOR_RELEVANCE"]) +
        (norm_pattern * WEIGHTS["PATTERN_MATCH"]) +
        (norm_tier * WEIGHTS["QUANT_TIER"]) +
        (norm_skill * WEIGHTS["QUANT_SKILL"]) +
        (norm_exp * WEIGHTS["QUANT_EXP"])
    )
    
    return final_score * 100

def deduplicate_results(results_list):
    seen = {}
    final_list = []
    for batch in results_list:
        for match in batch:
            mid = match['id']
            if mid not in seen:
                seen[mid] = match
                final_list.append(match)
            elif match['score'] > seen[mid]['score']:
                seen[mid] = match
                for i, item in enumerate(final_list):
                    if item['id'] == mid:
                        final_list[i] = match
                        break
    return final_list

def search_candidates(jd_text, limit=5):
    # 1. Load Secrets
    secrets_path = os.path.join(os.path.dirname(__file__), "secrets.json")
    with open(secrets_path, "r") as f:
        secrets = json.load(f)
        
    pc_host = secrets.get("PINECONE_HOST", "")
    if pc_host and not pc_host.startswith("https://"):
        pc_host = f"https://{pc_host}"

    pinecone = PineconeClient(secrets["PINECONE_API_KEY"], pc_host)
    openai = OpenAIClient(secrets["OPENAI_API_KEY"])
    analyzer = JDAnalyzerV5(openai)
    
    print(f"Analyzing JD with V5 (Standardized Axis)...")
    semantic_data = analyzer.analyze(jd_text)
    target_patterns = semantic_data.get("patterns", [])
    print(f"  -> Targeted Patterns: {target_patterns}")
    
    # 2. Strategy & Confidence
    confidence_score = estimate_jd_confidence({
        "explicit_skills": semantic_data.get('functional_domains', []),
        "title_candidates": [semantic_data.get('role_family', '')],
        "domain_clues": [semantic_data.get('role_family', '')],
        "seniority_clues": [str(semantic_data.get('seniority_required', ''))]
    })
    strategy = decide_search_strategy(confidence_score)
    role_cluster = get_role_cluster(semantic_data.get('role_family', 'Unclassified'))
    
    # 3. Ensemble Search
    # We use the role family and functional domains for semantic query
    semantic_query = f"Role: {semantic_data.get('role_family')} / Domains: {', '.join(semantic_data.get('functional_domains', []))} / Patterns: {', '.join(target_patterns)}"
    q_vec = openai.embed_content(semantic_query)
    
    filter_meta = {}
    min_years = semantic_data.get('seniority_required', 0)
    if min_years > 0:
        filter_meta['total_years'] = {"$gte": min_years}
    if role_cluster != "Unclassified":
        filter_meta['role_cluster'] = {"$eq": role_cluster}

    print(f"  -> Querying Pinecone (Top-K: {strategy['top_k']})")
    res = pinecone.query(q_vec, top_k=strategy['top_k'], filter_meta=filter_meta)
    
    if not res or 'matches' not in res:
        print("No matches found.")
        return []

    # 4. Hybrid Ranking with Pattern Bonus
    ranked_candidates = []
    for match in res['matches']:
        vec_score = match['score']
        meta = match['metadata']
        
        final_score = calculate_final_score(vec_score, meta, target_patterns)
        
        ranked_candidates.append({
            "name": meta.get('name', 'Unknown'),
            "final_score": final_score,
            "vector_score": vec_score,
            "patterns_matched": list(set(target_patterns).intersection(set(meta.get('experience_patterns', [])))),
            "summary": f"{meta.get('position', '')} at {meta.get('current_company', '')}",
            "id": match['id']
        })

    # Sort
    ranked_candidates.sort(key=lambda x: x['final_score'], reverse=True)
    
    # Output
    print(f"\n{'RANK':<5} | {'SCORE':<6} | {'NAME':<20} | {'PATTERNS':<30}")
    print("-" * 80)
    for i, cand in enumerate(ranked_candidates[:limit]):
        patterns_str = ", ".join(cand['patterns_matched']) if cand['patterns_matched'] else "None"
        print(f"{i+1:<5} | {cand['final_score']:<.1f}   | {cand['name']:<20} | {patterns_str[:30]}")
        
    return ranked_candidates

if __name__ == "__main__":
    test_jd = """
    Senior Finance Manager with experience in M&A Due Diligence, 
    Financial Modeling, and Budget Management. 5+ years experience required.
    """
    search_candidates(test_jd)
