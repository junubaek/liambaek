import re

class JDNormalizer:
    def __init__(self):
        # In a real app, load these from DB_rules.md or a config file
        self.ALLOWED_ROLES = [
            "Backend Engineer", "Frontend Engineer", "Fullstack Engineer", "Mobile Engineer",
            "DevOps/SRE", "Data Engineer", "AI/ML Engineer", "Product Manager", "Unknown"
        ]
        self.ALLOWED_DOMAINS = [
            "Fintech", "E-commerce", "SaaS", "AI/Data", "Healthcare", "Gaming", "EduTech", "Logistics"
        ]
        
    def normalize(self, extracted_data: dict) -> dict:
        if not extracted_data:
            return {
                "role_candidates": [],
                "domain_candidates": [],
                "must_have": [],
                "nice_to_have": [],
                "raw_extracted": {}
            }

        # Simple fuzzy matching or keyword checking
        params = {
            "role_candidates": self._match_list(extracted_data.get("title_candidates", []), self.ALLOWED_ROLES),
            "domain_candidates": self._match_list(extracted_data.get("domain_clues", []), self.ALLOWED_DOMAINS),
            "must_have": extracted_data.get("explicit_skills", []),
            "nice_to_have": extracted_data.get("implicit_skills", []), # Treat implicit as nice-to-have for now
            "raw_extracted": extracted_data # Keep raw data for inference 
        }
        return params

    def _match_list(self, raw_list, canonical_list):
        matched = set()
        for raw in raw_list:
            raw_lower = raw.lower()
            for canon in canonical_list:
                # Basic substring match
                if raw_lower in canon.lower() or canon.lower() in raw_lower:
                    matched.add(canon)
        return list(matched)
