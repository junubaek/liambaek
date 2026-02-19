import os

# jd_parser/__init__.py
# (Empty)

# jd_parser/extractor.py
from connectors.openai_api import OpenAIClient

class JDExtractor:
    def __init__(self, client: OpenAIClient):
        self.client = client
        
    def extract(self, jd_text: str) -> dict:
        prompt = f"""
You are an objective Information Extractor.
Extract factual signals from the Job Description below. 
Do NOT infer or guess. Only extract what is explicitly stated or strongly implied by context.

JOB DESCRIPTION:
{jd_text[:4000]}

OUTPUT FORMAT (JSON):
{{
  "title_candidates": ["List of job titles mentioned"],
  "explicit_skills": ["List of technical skills explicitly required"],
  "implicit_skills": ["List of skills implied by tasks (e.g., 'Handle high traffic' -> 'High concurrency')"],
  "seniority_clues": ["Years of experience", "Junior/Senior", "Lead"],
  "domain_clues": ["Industry", "Product type", "Business model"],
  "conflict_signals": ["Signals that contradict each other (e.g., 'Senior' but '1 year exp')"]
}}
"""
        return self.client.get_chat_completion_json(prompt)

# jd_parser/normalizer.py
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

# jd_parser/inferencer.py
from connectors.openai_api import OpenAIClient

class JDInferencer:
    def __init__(self, client: OpenAIClient):
        self.client = client
        
    def infer(self, normalized_data: dict) -> dict:
        prompt = f"""
You are a Lead Recruiter. 
Based on the normalized signals below, determine the PRIMARY Role and Domain.

SIGNALS:
- Role Candidates: {normalized_data['role_candidates']}
- Domain Candidates: {normalized_data['domain_candidates']}
- Skills: {normalized_data['must_have']}
- Raw Context: {normalized_data['raw_extracted']}

INSTRUCTIONS:
1. Select ONE Primary Role from the Role Candidates. If none match well, choose the closest from standard tech roles.
2. Select ONE or TWO domains.
3. Determine if the JD is "Ambiguous" (e.g., asks for Frontend but requires AWS/DB heavily).
4. Calculate a Confidence Score (0-100) based on signal clarity.

OUTPUT FORMAT (JSON):
{{
  "primary_role": "String",
  "domains": ["String"],
  "ambiguity": boolean,
  "ambiguity_reason": "String or null",
  "confidence_score": integer
}}
"""
        return self.client.get_chat_completion_json(prompt)

# jd_parser/pipeline.py
from connectors.openai_api import OpenAIClient
from .extractor import JDExtractor
from .normalizer import JDNormalizer
from .inferencer import JDInferencer

class JDPipeline:
    def __init__(self):
        # We assume secrets are handled inside OpenAIClient or manually passed
        # For now, instantiating OpenAIClient directly (it loads secrets internally)
        self.client = OpenAIClient()
        self.extractor = JDExtractor(self.client)
        self.normalizer = JDNormalizer()
        self.inferencer = JDInferencer(self.client)
        
    def parse(self, jd_text: str) -> dict:
        # Stage 1: Extract
        s1 = self.extractor.extract(jd_text)
        
        # Stage 2: Normalize
        s2 = self.normalizer.normalize(s1)
        
        # Stage 3: Infer
        s3 = self.inferencer.infer(s2)
        
        # Merge results
        result = {**s2, **s3} # Merges must_have, role_candidates with final decisions
        return result
