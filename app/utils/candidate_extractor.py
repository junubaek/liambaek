from typing import List, Dict
import json

class CandidatePatternExtractor:
    """
    [v5.1] Transforms ResumeParser JSON into normalized Pattern Index rows.
    """
    def __init__(self, ontology_path: str = "app/ontology/ontology.json"):
        try:
            with open(ontology_path, 'r', encoding='utf-8') as f:
                self.ontology = json.load(f)
        except:
            self.ontology = {}

    def extract_indexable_patterns(self, parsed_resume: Dict) -> List[Dict]:
        """
        Extracts and normalizes patterns from experience_patterns list in resume JSON.
        """
        raw_patterns = parsed_resume.get("experience_patterns", [])
        indexable = []
        
        depth_map = {
            "Mentioned": 0.3,
            "Executed": 0.7,
            "Led": 1.0, 
            "Architected": 1.3
        }

        for rp in raw_patterns:
            pattern_name = rp.get("pattern", "Unknown")
            
            # 1. Strict Ontology Validation [v5.2]
            valid_pattern = False
            for domain_data in self.ontology.get("domains", {}).values():
                if pattern_name in domain_data.get("patterns", []):
                    valid_pattern = True
                    break
            
            if not valid_pattern:
                continue

            depth_val = rp.get("depth", "Mentioned")
            depth_score = depth_map.get(depth_val, 0.3)
            
            impact_score = 0.5
            if rp.get("quant_signal") or "impact" in str(rp).lower():
                impact_score = 0.8
            if depth_val == "Architected":
                impact_score = min(1.0, impact_score + 0.2)

            indexable.append({
                "pattern": pattern_name,
                "depth": depth_score,
                "impact": impact_score
            })
            
        return indexable
