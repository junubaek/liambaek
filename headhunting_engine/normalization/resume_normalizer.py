import re
import json
from typing import Set, Dict, List, Tuple

class ResumeNormalizer:
    """
    Normalizes resume text into canonical skill nodes using a provided dictionary.
    Uses set-based optimized matching and handles __TEMP__ prefixing for unmapped terms.
    """
    def __init__(self, dictionary_path: str):
        with open(dictionary_path, 'r', encoding='utf-8') as f:
            self.dict_data = json.load(f)
        
        self.version = self.dict_data.get("version", "unknown")
        self.temp_prefix = self.dict_data.get("governance_policy", {}).get("temp_prefix", "__TEMP__")
        
        # Build Alias -> Canonical Map
        self.alias_to_canonical = {}
        for node_id, node_data in self.dict_data.get("canonical_skill_nodes", {}).items():
            for alias in node_data.get("aliases", []):
                self.alias_to_canonical[alias.lower()] = node_id

    def _preprocess_text(self, text: str) -> str:
        """
        Lowercases and removes special characters for better matching.
        """
        # Keep some characters like ++ for C++ or # for C#
        text = text.lower()
        text = re.sub(r'[^a-z0-9+#\s]', ' ', text)
        return text

    def normalize(self, resume_text: str) -> Dict:
        """
        Extracts canonical nodes, matched aliases, and unmapped potential skills.
        """
        processed_text = self._preprocess_text(resume_text)
        words = set(processed_text.split())
        
        matched_nodes = set()
        matched_aliases = {}
        
        # Exact match logic (higher precision)
        for alias, node_id in self.alias_to_canonical.items():
            # Check for multi-word aliases
            if ' ' in alias:
                if alias in processed_text:
                    matched_nodes.add(node_id)
                    matched_aliases[alias] = node_id
            elif alias in words:
                matched_nodes.add(node_id)
                matched_aliases[alias] = node_id
        
        # Simple heuristic for unmapped terms (placeholder for more advanced NLP if needed)
        # In this deterministic version, we look for capitalized-like terms in original if available,
        # but here we follow the "LLM usage forbidden" rule.
        # For now, unmapped terms will be handled by a separate process or marked if they look like skills.
        
        return {
            "canonical_skill_nodes": list(matched_nodes),
            "matched_aliases": matched_aliases,
            "unmapped_terms": [] # To be populated by a candidate-skill-detector or manual review
        }

    def normalize_skills_depth(self, skills_depth: List[Dict]) -> List[Dict]:
        """
        [v1.3] Maps a list of skill objects (name, depth) to canonical IDs.
        """
        normalized_skills = []
        for item in skills_depth:
            name = item.get("name", "")
            depth = item.get("depth", "Mentioned")
            
            # 1. Alias match
            name_lower = name.lower()
            if name_lower in self.alias_to_canonical:
                normalized_skills.append({
                    "name": self.alias_to_canonical[name_lower],
                    "depth": depth
                })
            else:
                # 2. Mark as __TEMP__
                normalized_skills.append({
                    "name": f"{self.temp_prefix}{name.replace(' ', '_')}",
                    "depth": depth
                })
        return normalized_skills

class JDNormalizer:
    """
    Converts LLM-parsed JD JSON into canonical sets for matching.
    """
    def __init__(self, resume_normalizer: ResumeNormalizer):
        self.normalizer = resume_normalizer

    def normalize_jd(self, jd_json: Dict) -> Dict:
        """
        jd_json expected format: {"must_have": ["skill1", ...], "nice_to_have": [...]}
        """
        must_nodes = set()
        nice_nodes = set()
        
        # Build Canonical ID Set for direct comparison
        canonical_ids = set(self.normalizer.dict_data.get("canonical_skill_nodes", {}).keys())
        
        def _map_to_nodes(skill_list):
            nodes = set()
            for s in skill_list:
                # 1. Direct ID match
                if s in canonical_ids:
                    nodes.add(s)
                    continue
                
                # 2. Alias match
                s_lower = s.lower()
                if s_lower in self.normalizer.alias_to_canonical:
                    nodes.add(self.normalizer.alias_to_canonical[s_lower])
                else:
                    # Mark as __TEMP__ if not in dictionary
                    nodes.add(f"{self.normalizer.temp_prefix}{s.replace(' ', '_')}")
            return nodes

        must_nodes = _map_to_nodes(jd_json.get("must_have", []))
        nice_nodes = _map_to_nodes(jd_json.get("nice_to_have", []))
        
        return {
            "must_nodes": list(must_nodes),
            "nice_nodes": list(nice_nodes),
            "normalized_title": jd_json.get("normalized_title")
        }
