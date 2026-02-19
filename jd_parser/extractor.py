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
        res = self.client.get_chat_completion_json(prompt)
        return res if res else {}
