from typing import Dict, List, Tuple
import sqlite3
import json

class Scorer:
    """
    Universal Scorer (Phase 5.3): 6-factor matching formula.
    """
    def calculate_score(self, candidate_skills: List[Dict], context_data: Dict, candidate_id: str = None, tenant_id: str = "default") -> Tuple[float, Dict]:
        # 1. Map Candidate Experience Patterns with Depth [v5.3 - Index Prioritized]
        depth_weights = {
            "Mentioned": 0.3, 
            "Executed": 0.7, 
            "Led": 1.0, 
            "Architected": 1.3
        }
        
        cand_patterns = {}
        
        if candidate_id:
            try:
                # Use a lightweight connection to avoid hangs
                with sqlite3.connect("headhunting_engine/data/analytics.db", timeout=5) as conn:
                    cursor = conn.cursor()
                    # Try with tenant_id first
                    cursor.execute(
                        "SELECT pattern, depth FROM candidate_patterns WHERE candidate_id = ? AND tenant_id = ?", 
                        (candidate_id, tenant_id)
                    )
                    rows = cursor.fetchall()
                    
                    # If no results and tenant_id isn't 'default', fallback to 'default'
                    if not rows and tenant_id != 'default':
                        cursor.execute(
                            "SELECT pattern, depth FROM candidate_patterns WHERE candidate_id = ?", 
                            (candidate_id,)
                        )
                        rows = cursor.fetchall()
                        
                    if rows:
                        cand_patterns = {r[0]: r[1] for r in rows}
            except Exception as e:
                print(f"Index Fetch Warning: {e}")

        if not cand_patterns:
            for item in candidate_skills:
                name = item.get("name") or item.get("pattern")
                depth = item.get("depth", "Mentioned")
                if isinstance(depth, (int, float)):
                    weight = depth
                else:
                    weight = depth_weights.get(depth, 0.3)
                cand_patterns[name] = weight

        # 2. Factor 1: Domain Fit (25%) - Role Cluster Alignment
        cand_role = context_data.get("role_cluster") or context_data.get("role") or "Unclassified"
        target_role = context_data.get("role_family") or "Unclassified"
        domain_score = 100 if cand_role == target_role else 50
        if cand_role == "Unclassified": domain_score = 0

        # 3. Factor 2: Pattern Match (35%) - Hybrid Nucleus [v5.3]
        jd_patterns = set(context_data.get("experience_patterns", []))
        pattern_match_score = 0
        if jd_patterns:
            match_sum = sum(cand_patterns.get(p, 0) for p in jd_patterns)
            det_match = (match_sum / len(jd_patterns)) * 100
            semantic_sim = context_data.get("semantic_similarity", 0.7)
            pattern_match_score = (det_match * 0.6) + (semantic_sim * 100 * 0.4)
        
        # 4. Factor 3: Impact Fit (15%)
        impact_score = 70
        if candidate_id:
             try:
                 with sqlite3.connect("headhunting_engine/data/analytics.db", timeout=3) as conn:
                     cursor = conn.cursor()
                     cursor.execute("SELECT AVG(impact) FROM candidate_patterns WHERE candidate_id = ?", (candidate_id,))
                     res = cursor.fetchone()
                     if res and res[0]: impact_score = res[0] * 100
             except: pass

        # 5. Factor 4: Seniority Fit (10%)
        req_seniority = context_data.get("seniority_required", 0)
        cand_exp = context_data.get("experience_years") or context_data.get("total_years_experience") or 0
        seniority_score = 100 if cand_exp >= req_seniority else (cand_exp / req_seniority * 100 if req_seniority > 0 else 100)
        
        # 6. Factor 5: Leadership Fit (10%)
        req_leadership = context_data.get("leadership_level", "IC")
        cand_lead = context_data.get("current_leadership_level") or context_data.get("leadership_level") or "IC"
        leadership_score = 100 if cand_lead == req_leadership else 50

        # 7. Factor 6: Culture Fit (5%)
        culture_score = 80

        # 8. Final Unified Formula [v5.3]
        base_match = (
            (domain_score * 0.25) +
            (pattern_match_score * 0.35) +
            (impact_score * 0.15) +
            (seniority_score * 0.10) +
            (leadership_score * 0.10) +
            (culture_score * 0.05)
        )

        # 9. Elite Modifier (EM)
        grade = context_data.get("career_path_grade", "B")
        em_mod = 1.0
        if grade == "S": em_mod = 1.10
        elif grade == "A": em_mod = 1.05
        
        final_score = base_match * em_mod

        return final_score, {
            "final_score": round(final_score, 2),
            "domain_fit": round(domain_score, 2),
            "pattern_match": round(pattern_match_score, 2),
            "impact_fit": round(impact_score, 2),
            "seniority_fit": round(seniority_score, 2),
            "leadership_fit": round(leadership_score, 2),
            "culture_fit": round(culture_score, 2)
        }
