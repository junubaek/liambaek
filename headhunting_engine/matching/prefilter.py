from typing import List, Dict, Set

class PreFilterEngine:
    """
    Deterministic pre-filtering for large candidate pools.
    Uses an inverted index for performance: {skill_node: [candidate_ids]}
    """
    def __init__(self):
        self.skill_index = {} # node_id -> set(candidate_id)
        self.role_index = {}  # role -> set(candidate_id)

    def build_index(self, candidates: List[Dict], canonical_ids: Set[str] = None):
        """
        Builds inverted indices from candidate data.
        [v1.2] Apply __TEMP__ prefix to untracked skills to match JDNormalizer nodes.
        """
        self.skill_index = {}
        self.role_index = {}
        
        for c in candidates:
            c_id = c.get("id")
            # Index skills
            for node in c.get("canonical_skill_nodes", []):
                # Auto-prefix if not a canonical ID and not already prefixed
                indexed_node = node
                if canonical_ids is not None and node not in canonical_ids and not node.startswith("__TEMP__"):
                    indexed_node = f"__TEMP__{node}"
                
                if indexed_node not in self.skill_index:
                    self.skill_index[indexed_node] = set()
                self.skill_index[indexed_node].add(c_id)
            
            # Index roles
            role = c.get("position")
            if role:
                if role not in self.role_index:
                    self.role_index[role] = set()
                self.role_index[role].add(c_id)

    def filter(self, jd_normalized: Dict, adjacent_role_map: Dict, candidate_pool: List[Dict], search_mode: bool = False) -> Set[str]:
        """
        Applies pre-filters to match candidate IDs.
        [v1.2] added search_mode to bypass metadata for calibration.
        """
        must_nodes = set(jd_normalized.get("must_nodes", []))
        jd_position = jd_normalized.get("normalized_title")
        adjacent_roles = set(adjacent_role_map.get(jd_position, []))
        target_roles = adjacent_roles | {jd_position}
        
        # 1. Role Filter
        role_candidates = set()
        for role in target_roles:
            role_candidates.update(self.role_index.get(role, set()))

        # 2. Skill Intersection Pre-filter (Must nodes)
        skill_matched_candidates = set()
        if not must_nodes:
            skill_matched_candidates = role_candidates
        else:
            for node in must_nodes:
                skill_matched_candidates.update(self.skill_index.get(node, set()))
            
        if search_mode:
            # Discovery mode: Return anyone with the skills
            return skill_matched_candidates

        potential_ids = role_candidates & skill_matched_candidates

        # 3. Metadata Filter (Base Score & Career Path)
        final_ids = set()
        candidate_map = {c["id"]: c for c in candidate_pool}
        
        for c_id in potential_ids:
            c = candidate_map.get(c_id)
            if not c: continue
            
            if c.get("base_talent_score", 0) >= 40 and \
               c.get("career_path_grade") != "Declining":
                final_ids.add(c_id)
                
        return final_ids
