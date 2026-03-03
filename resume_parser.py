
import json
import re

class ResumeParser:
    def __init__(self, openai_client):
        self.client = openai_client

    def parse(self, resume_text: str) -> dict:
        """
        Parses raw resume text into a structured JSON using LLM.
        [v1.3.1.1] Extreme Hardened Prompt (Cold Judgment)
        """
        if not resume_text:
             return {}

        prompt = f"""
You are a COLD, SKEPTICAL Resume Auditor. LLM optimism is your enemy. 
Extract deterministic signals with extreme conservatism.

[RESUME TEXT]
{resume_text[:12000]}

[SCHEMA INSTRUCTIONS]
Output JSON:
{{
  "basics": {{
    "name": "Candidate Name",
    "position": "Current precise role",
    "total_years_experience": (int)
  }},
  "quant_signals": {{
    "short_tenures_count": (int, < 2 years),
    "quantified_impact_count": (int, NUMERICAL results only like %, $, hours),
    "big_tech_experience": (bool),
    "architecture_ownership": (bool),
    "unexplained_gap": (bool, > 1 year),
    "tier_improvement": (bool),
    "responsibility_increase": (bool, only if title upgraded or team doubled),
    "scope_expansion": (bool, fundamentally new tech/domain)
  }},
  "skills_depth": [
    {{"name": "Skill", "depth": "Mentioned | Applied | Architected"}}
  ],
  "summary": "One sentence value."
}}

[CRITICAL JUDGMENT RULES]
1. SKILL DEPTH:
- Mentioned: DEFAULT. Use if the candidate just lists the skill or describes routine usage without a specific achievement.
- Applied: Requires [Context] AND [Specific Problem Solved] AND [Proven Outcome/ROI]. If it's just "developed feature X", it's MENTIONED.
- Architected: Only if they designed the core structure/blueprint. Must show Tradeoff reasoning (why this tech?).

2. ASCENDING TRAJECTORY SIGNALS:
- responsibility_increase: FALSE unless they became a lead, manager, or moved to a significantly larger organization/project.
- tier_improvement: FALSE unless the new company is objectively higher tier (e.g., Startup -> Big Tech).

Be merciless. Better to underestimate than overpromise.
"""
        try:
            parsed_data = self.client.get_chat_completion_json(prompt)
            if not parsed_data.get("basics"):
                parsed_data["basics"] = {}
            if not parsed_data.get("skills_depth"):
                parsed_data["skills_depth"] = []
                
            return parsed_data
            
        except Exception as e:
            print(f"❌ Resume Parsing Error: {e}")
            return {}
