
import json
from connectors.openai_api import OpenAIClient

class JDAnalyzerV3:
    def __init__(self, openai_client):
        self.openai = openai_client
        
    def analyze(self, jd_text: str) -> dict:
        """
        Analyzes JD to extract verifiable screening signals, NOT ideal persona.
        """
        system_prompt = """
        You are a senior in-house recruiter.
        Your goal is NOT to describe the perfect candidate.
        Your goal is to define who would PASS the document screening stage.

        Rules:
        - Only include skills that can be VERIFIED on a resume.
        - Do NOT infer personality, mindset, or attitude.
        - Domain experience is NEVER a disqualifier unless explicitly stated in the JD (e.g., "Must be from Fintech").
        - If a skill can be learned on the job, do NOT treat it as a core signal.

        Think like:
        "Would I move this resume to the interview pile?"
        
        Output JSON Schema:
        {
          "canonical_role": "Standardized Job Title (e.g. Backend Engineer, Product Owner)",
          "core_signals": ["List of CRITICAL skills that appear on resume"],
          "supporting_signals": ["List of Nice-to-have skills or tools"],
          "context_signals": ["Business context keywords (e.g. B2B, SaaS, High Traffic)"],
          "explicit_disqualifiers": ["List only if JD says 'Do not apply if...'"],
          "interview_checkpoints": ["List of soft skills/domain knowledge to check in interview"]
        }
        """
        
        user_prompt = f"Analyze this JD:\n{jd_text[:4000]}"
        
        try:
            response = self.openai.get_chat_completion(system_prompt, user_prompt)
            clean_json = response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception as e:
            print(f"JD Analyzer V3 Error: {e}")
            return {
                "canonical_role": "Unknown",
                "core_signals": [],
                "supporting_signals": [],
                "context_signals": [],
                "explicit_disqualifiers": [],
                "interview_checkpoints": []
            }
