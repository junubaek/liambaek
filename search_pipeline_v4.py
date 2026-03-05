
import json
import os
import sys
from typing import List, Dict, Any, Tuple

# Path Setup
current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_path = os.path.abspath(os.path.join(current_dir, ".."))
if workspace_path not in sys.path: sys.path.append(workspace_path)

class SearchPipelineV4:
    def __init__(self, pinecone_client):
        self.pc = pinecone_client
        
    def run(self, jd_analysis: Dict[str, Any], query_vector: List[float], top_k: int = 50) -> Tuple[List[Dict[str, Any]], List[str]]:
        logs = []
        logs.append("PIPELINE V4: Universal Experience Matching Start")
        
        # 1. Retrieval
        raw_results = self.pc.query(query_vector, top_k=top_k, namespace="ns1")
        candidates = self._convert_results(raw_results)
        
        # 2. Universal Scoring (5-Axis)
        for cand in candidates:
            score_meta = self._calculate_universal_score(jd_analysis, cand)
            cand['rpl_score'] = score_meta['total_score']
            cand['score_breakdown'] = score_meta
            
        # 3. Sort
        candidates.sort(key=lambda x: x.get('rpl_score', 0), reverse=True)
        
        return candidates, logs

    def _calculate_universal_score(self, jd, cand) -> Dict[str, float]:
        metadata = cand.get('data', {})
        
        # 1. Domain Fit (DF) - 25%
        jd_domains = set(jd.get('functional_domains', [jd.get('role_family')]))
        cand_domains = set(metadata.get('domains', [metadata.get('domain_fit')]))
        df_score = (len(jd_domains & cand_domains) / len(jd_domains)) * 100 if jd_domains else 50
        
        # 2. Experience Pattern Match (EPM) - 35%
        jd_patterns = {p.get('pattern') if isinstance(p, dict) else p for p in jd.get('experience_patterns', [])}
        cand_patterns = metadata.get('experience_patterns', [])
        
        epm_sum = 0
        depth_map = {"Mentioned": 0.3, "Executed": 0.7, "Led": 1.0, "Architected": 1.3}
        
        matched_patterns = 0
        for cp in cand_patterns:
            p_name = cp.get('pattern')
            if p_name in jd_patterns:
                weight = depth_map.get(cp.get('depth'), 0.3)
                epm_sum += (weight * 100)
                matched_patterns += 1
        
        epm_score = min(epm_sum / (len(jd_patterns) if jd_patterns else 1), 130) # Max 130% for over-achievement
        
        # 3. Impact Fit (IF) - 15%
        # Check for quant signals
        if metadata.get('experience_patterns') and any(p.get('quant_signal') for p in metadata['experience_patterns']):
            impact_score = 100
        else:
            impact_score = 40
            
        # 4. Seniority Fit (SF) - 10%
        req_years = jd.get('seniority_required', 1)
        cand_years = metadata.get('basics', {}).get('total_years_experience', 0)
        sf_score = min((cand_years / req_years) * 100, 100)
        
        # 5. Leadership Fit (LF) - 10%
        req_lead = jd.get('leadership_level')
        cand_lead = metadata.get('basics', {}).get('current_leadership_level')
        lf_score = 100 if req_lead == cand_lead else 60
        
        # 6. Cultural Fit (CF) - 5%
        cf_score = 80 # Default for now
        
        # Elite Modifier (EM)
        em = 1.2 if metadata.get('elite_signals', {}).get('tier_improvement') else 1.0
        
        total_score = em * (
            (df_score * 0.25) +
            (epm_score * 0.35) +
            (impact_score * 0.15) +
            (sf_score * 0.10) +
            (lf_score * 0.10) +
            (cf_score * 0.05)
        )
        
        return {
            "total_score": total_score,
            "df": df_score,
            "epm": epm_score,
            "if": impact_score,
            "sf": sf_score,
            "lf": lf_score,
            "cf": cf_score,
            "em": em
        }

    def _convert_results(self, res):
        candidates = []
        if res and 'matches' in res:
            for m in res['matches']:
                # Handle potential missing metadata in some vectors
                meta = m.get('metadata', {})
                # Double Parse if metadata is stored as JSON string
                if isinstance(meta, str):
                    try: meta = json.loads(meta)
                    except: pass
                
                candidates.append({
                    "id": m['id'],
                    "vector_score": m['score'],
                    "data": meta
                })
        return candidates
