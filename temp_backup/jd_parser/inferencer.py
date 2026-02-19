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
        result = self.client.get_chat_completion_json(prompt)
        return result if result else {}
