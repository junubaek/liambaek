import json
from typing import List, Dict
from headhunting_engine.normalization.resume_normalizer import ResumeNormalizer, JDNormalizer
from headhunting_engine.matching.prefilter import PreFilterEngine
from headhunting_engine.matching.scorer import Scorer
from headhunting_engine.matching.version_manager import VersionManager
from headhunting_engine.matching.rpl import RPLEngine, DifficultyEngine
from headhunting_engine.analytics.scarcity import ScarcityEngine

class MainPipeline:
    """
    Orchestrates the AI Headhunting Quant Engine pipeline.
    Deterministic, Performant, and Audit-Ready.
    """
    def __init__(self, dictionary_path: str, snapshot_path: str = None):
        # Initialize Normalization
        self.resume_normalizer = ResumeNormalizer(dictionary_path)
        self.jd_normalizer = JDNormalizer(self.resume_normalizer)
        
        # Initialize Versioning
        self.version_manager = VersionManager(self.resume_normalizer.version)
        
        # Initialize Matching Engine
        self.prefilter = PreFilterEngine()
        self.scorer = Scorer(self.version_manager)
        
        # Initialize Analytics
        self.scarcity_engine = ScarcityEngine(snapshot_path)
        self.difficulty_engine = DifficultyEngine()
        self.rpl_engine = RPLEngine()
        
        self.audit_trail = []

    def run_matching(self, jd_data: Dict, candidate_pool: List[Dict], top_n: int = 5, debug: bool = False, search_mode: bool = False) -> Dict:
        """
        Executes the deterministic matching pipeline with audit trail.
        """
        # ... (JD normalization)
        jd_normalized = self.jd_normalizer.normalize_jd(jd_data)
        jd_must = set(jd_normalized["must_nodes"])
        jd_nice = set(jd_normalized["nice_nodes"])
        
        # 2. Build Inverted Index (for performance)
        canonical_ids = set(self.resume_normalizer.dict_data.get("canonical_skill_nodes", {}).keys())
        self.prefilter.build_index(candidate_pool, canonical_ids=canonical_ids)
        
        # 3. Pre-filter (Deterministic initial screening)
        adjacent_map = self.resume_normalizer.dict_data.get("adjacent_role_map", {})
        potential_ids = self.prefilter.filter(jd_normalized, adjacent_map, candidate_pool, search_mode=search_mode)
        
        # 4. Scorer/Matching (Hard filter + Detailed logs)
        matching_results = []
        debug_all_scored = []
        coverage_sums = 0.0
        
        # Create a map for quick candidate lookup
        candidate_map = {c["id"]: c for c in candidate_pool}
        
        for c_id in potential_ids:
            c = candidate_map.get(c_id)
            if not c: continue # Should not happen if potential_ids are from candidate_pool
            
            # [v1.3] Pass structured skills with depth
            cand_skills = c.get("skills_depth", [])
            
            score, calc_log = self.scorer.calculate_score(
                cand_skills,
                jd_must,
                jd_nice,
                c,
                canonical_ids=canonical_ids
            )
            
            # Record for debug/stats regardless of hard filter
            if debug:
                must_matches = list(cand_nodes & jd_must)
                debug_all_scored.append({
                    "candidate_id": c["id"],
                    "must_coverage": len(must_matches) / len(jd_must) if jd_must else 1.0,
                    "score": score
                })
            
            if score > 0:
                matching_results.append({
                    "candidate_id": c["id"],
                    "score": score,
                    "calculation_log": calc_log
                })
                coverage_sums += calc_log.get("must_coverage", 0)
        
        # 5. [v1.1] Scoring Statistics & Integrated Difficulty
        scores = [res["score"] for res in matching_results]
        import statistics
        mean_score = statistics.mean(scores) if scores else 0
        std_score = statistics.stdev(scores) if len(scores) > 1 else 0
        
        jd_scarcity = self.scarcity_engine.calculate_jd_scarcity(jd_normalized["must_nodes"], canonical_ids=canonical_ids)
        avg_coverage = (coverage_sums / len(matching_results)) if matching_results else 0.0
        
        diff_score = self.difficulty_engine.calculate_difficulty_score(avg_coverage, jd_scarcity)
        diff_label = self.difficulty_engine.get_difficulty_label(diff_score)
        
        for res in matching_results:
            res["rpl"] = round(self.rpl_engine.calculate_rpl(res["score"], mean_score, std_score, diff_score), 2)
            res["difficulty"] = diff_label
            res["difficulty_score"] = round(diff_score, 2)

        # 6. Final Sorting & Audit Trail
        final_results = sorted(matching_results, key=lambda x: x["score"], reverse=True)[:top_n]
        
        dynamic_threshold_used = matching_results[0]["calculation_log"]["dynamic_threshold_used"] if matching_results else 0.0
        
        self.audit_trail.append({
            "jd_id": jd_data.get("id", "unknown"),
            "pool_size": len(candidate_pool),
            "prefilter_passed": len(potential_ids),
            "hard_filter_passed": len(matching_results),
            "top_candidates": [r["candidate_id"] for r in final_results],
            "mean_score": round(mean_score, 2),
            "std_score": round(std_score, 2),
            "avg_coverage": round(avg_coverage, 2),
            "dynamic_threshold_used": dynamic_threshold_used,
            "difficulty_score": round(diff_score, 2),
            "jd_scarcity": round(jd_scarcity, 4),
            "difficulty": diff_label,
            "meta": self.version_manager.get_metadata()
        })
        
        return {
            "top_candidates": final_results,
            "audit_trail": self.audit_trail[-1],
            "scarcity_index": jd_scarcity,
            "debug_all_scored": debug_all_scored
        }
