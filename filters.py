from typing import List, Dict, Any, Optional, Tuple
from matrices import ScoreMatrix, Competency

class BaseFilter:
    def apply(self, candidates: List[Dict[str, Any]], context: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
        raise NotImplementedError

class HardFilter(BaseFilter):
    """
    Stage 2: Mechanical Cut
    - Filters by Years of Experience (with buffer)
    - Filters by Major Role Mismatch (if applicable)
    """
    def apply(self, candidates: List[Dict[str, Any]], context: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
        jd_min_years = context.get('min_years', 0)
        contract = context.get('search_contract', {})
        role_family = contract.get('role_family', context.get('role_cluster', ''))
        neg_signals = contract.get('negative_signals', context.get('negative_signals', []))
        
        # [v3.0] Wide Funnel Strategy: No longer dropping candidates.
        # Instead, we apply Penalties.
        processed_candidates = []
        logs = []
        
        for cand in candidates:
            penalty = 0
            reasons = []
            
            try:
                # 1. Years Filter (Range-Based)
                try:
                    cand_years = int(cand['data'].get('total_years', 0))
                except (ValueError, TypeError):
                    cand_years = 0
                
                years_range = jd_context.get('years_range')
                
                # Backward compatibility
                if not isinstance(years_range, dict):
                    old_min = jd_context.get('min_years', 0)
                    years_range = {"min": int(old_min) if old_min else 0, "max": None}

                min_y = years_range.get("min")
                max_y = years_range.get("max")
                
                # Check Min
                if min_y and isinstance(min_y, (int, float)) and min_y > 0:
                    if cand_years < (min_y - 1): # 1 year buffer
                         penalty += 10
                         reasons.append(f"Years < {min_y}")
                         logs.append(f"PENALTY(Years-Min): {cand.get('id')} -10 ({cand_years} < {min_y})")
                
                # Check Max
                if max_y and isinstance(max_y, (int, float)):
                     if cand_years > (max_y + 2): # +2 year buffer
                         penalty += 5 # Warning penalty for overqualified?
                         reasons.append(f"Years > {max_y}")
                         logs.append(f"PENALTY(Years-Max): {cand.get('id')} -5 ({cand_years} > {max_y})")

                # 2. Hard Role Mismatch -> Softened to Penalty
                if role_family:
                    cand_role = str(cand['data'].get('role_cluster', 'Unknown'))
                    if not self._is_role_compatible(role_family, cand_role, cand['data']):
                         penalty += 5 # Lighter penalty as clusters can be vague
                         reasons.append(f"Role Mismatch ({cand_role})")
                         logs.append(f"PENALTY(Role): {cand.get('id')} -5 ({cand_role} != {role_family})")

                # 3. Explicit Negative Signals
                if self._check_negative_signals(cand['data'], neg_signals):
                    penalty += 15 # Severe penalty
                    reasons.append("Negative Signal")
                    logs.append(f"PENALTY(Negative): {cand.get('id')} -15 (Triggered Signal)")
                
                # Store Penalty Data
                cand['filter_penalty'] = penalty
                cand['penalty_reasons'] = reasons
                
                processed_candidates.append(cand)

            except Exception as e:
                print(f"ERROR in HardFilter loop for {cand.get('id')}: {e}")
                processed_candidates.append(cand) # Keep safely
            
        summary_log = f"SoftFilter: Processed {len(candidates)} candidates. (No Drops, applied penalties)"
        logs.insert(0, summary_log)
        
        return processed_candidates, logs

    def _is_role_compatible(self, target_family: str, cand_role: str, cand_data: Dict) -> bool:
        """
        Returns True if candidate role is compatible with target family.
        """
        t = target_family.lower()
        c = cand_role.lower()
        
        # 1. Exact or Substring Match
        if t in c or c in t: return True
        
        # 2. PM/PO/Planner Cluster
        pm_keywords = ["product", "pm", "po", "planning", "기획", "manager"]
        if any(k in t for k in pm_keywords) and any(k in c for k in pm_keywords):
            return True
            
        # 3. Engineering Cluster
        dev_keywords = ["engineer", "developer", "backend", "frontend", "fullstack", "sw", "software", "개발"]
        if any(k in t for k in dev_keywords):
            # If target is Dev, candidate must be Dev
            if any(k in c for k in dev_keywords): return True
            return False 

        # Default: Allow if unsure
        return True

    def _check_negative_signals(self, cand_data: Dict, signals: List[str]) -> bool:
        """
        Returns True if candidate TRIGGERS a negative signal (should be dropped).
        """
        if not signals: return False
        
        summary = cand_data.get('summary', '').lower()
        title = cand_data.get('title', '').lower()
        
        for sig in signals:
            sig_lower = sig.lower()
            # Simple Keyword Checks for common disqualifiers
            if "marketing" in sig_lower and "marketing" in title and "pm" not in title: 
                 return True
                 
            if "junior" in sig_lower and "junior" in title:
                return True
                
            if "intern" in sig_lower and "intern" in title:
                 return True
                 
        return False

class MatrixFilter(BaseFilter):
    """
    Stage 3: Role Matrix Scoring
    - Applies specific ScoreMatrix based on role
    - Dynamic Threshold adjustment based on Confidence
    """
    def __init__(self, matrix: ScoreMatrix):
        self.matrix = matrix

    def apply(self, candidates: List[Dict[str, Any]], context: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
        passed = []
        logs = []
        
        # Determine Threshold
        base_threshold = self.matrix.base_threshold
        confidence = context.get('confidence_score', 0)
        
        # Dynamic Adjustment
        if confidence >= 80:
            threshold = base_threshold + 1
        elif confidence < 50:
            threshold = base_threshold - 1
        else:
            threshold = base_threshold
            
        # Safety: Don't let threshold go below 1
        threshold = max(1, threshold)
        
        logs.append(f"MatrixFilter ({self.matrix.name}) Threshold: {threshold} (Base: {base_threshold}, Conf: {confidence})")
        
        for cand in candidates:
            score = 0
            reasons = []
            
            for comp in self.matrix.competencies:
                matched = False
                
                # Check custom logic first
                if comp.custom_logic:
                    if comp.custom_logic(cand['data']):
                        matched = True
                
                if matched:
                    score += comp.weight
                    reasons.append(comp.name)
            
            # Record score for debugging/UI
            cand['matrix_score'] = score
            cand['matrix_reasons'] = reasons
            
            if score >= threshold:
                passed.append(cand)
            else:
                 logs.append(f"DROP(Matrix): {cand.get('id')} Score {score} < {threshold}")
        
        summary_log = f"MatrixFilter: Input {len(candidates)} -> Output {len(passed)} (Dropped {len(candidates) - len(passed)})"
        print(f"DEBUG: {summary_log}")
        logs.insert(0, summary_log)
        
        return passed, logs
