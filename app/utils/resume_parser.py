
import json
import re

class ResumeParser:
    def __init__(self, openai_client):
        self.client = openai_client

    def parse(self, resume_text: str) -> dict:
        """
        [v5.2] Experience Extraction Engine
        Converts resume into an Experience Graph with Depth and Impact metrics.
        """
        if not resume_text:
             return {}

        prompt = f"""
You are a Senior Experience Extraction Engine (Universal v5.2). 
Your task is to convert the resume into a structured Experience Graph focusing on strategic patterns rather than just keywords.

[RESUME TEXT]
{resume_text[:12000]}

[SCHEMA INSTRUCTIONS]
Output JSON:
{{
  "basics": {{
    "name": "",
    "total_years_experience": 0,
    "current_leadership_level": "IC | Team Lead | Department Head | Executive"
  }},
  "role_families": [],
  "domains": [],
  "experience_patterns": [
    {{
      "pattern": "Standardized Pattern (e.g., Office_Relocation_PM, Threat_Modeling)",
      "depth": "Mentioned | Executed | Led | Architected",
      "impact_scale": "Quantified scale (e.g., 500M KRW, 20 Engineers)",
      "quant_signal": true
    }}
  ],
  "impact_signals": {{
    "max_budget": "",
    "max_team_size": "",
    "org_reach": ""
  }},
  "elite_signals": {{
    "tier_improvement": bool,
    "top_institution": bool
  }}
}}

[DEPTH RULES]
- Mentioned (0.3): Simple listing in skills section.
- Executed (0.7): Described as a main job task with ownership.
- Led (1.0): Managed the project, team, or specific budget for it.
- Architected (1.3): Designed the core system, framework, or policy from scratch.
"""
        try:
            parsed_data = self.client.get_chat_completion_json(prompt)
            if not parsed_data.get("basics"):
                parsed_data["basics"] = {}
                parsed_data["skills_depth"] = []
                
            return parsed_data
            
        except Exception as e:
            print(f"❌ Resume Parsing Error: {e}")
            return {}

    def calculate_quality_score(self, parsed_data: dict) -> dict:
        """
        [v5] Candidate Data Quality Score
        Items: Completeness, Pattern Density, Consistency.
        """
        if not parsed_data: return {"total": 0, "status": "Invalid"}
        
        # 1. Completeness (40%)
        fields = ["basics", "role_families", "domains", "experience_patterns", "impact_signals"]
        present_fields = sum(1 for f in fields if parsed_data.get(f))
        completeness = (present_fields / len(fields)) * 100
        
        # 2. Pattern Density (30%)
        patterns = parsed_data.get("experience_patterns", [])
        # Healthy range: 3-8 patterns
        pattern_density = 100 if 3 <= len(patterns) <= 8 else 50 if len(patterns) > 0 else 0
        
        # 3. Experience Consistency (30%)
        # Logic: If total_years > 5, but patterns < 2, consistency is low
        total_years = parsed_data.get("basics", {}).get("total_years_experience", 0)
        consistency = 100
        if total_years > 5 and len(patterns) < 2:
            consistency = 40
            
        total_score = (completeness * 0.4) + (pattern_density * 0.3) + (consistency * 0.3)
        
        return {
            "total_score": round(total_score, 2),
            "status": "High" if total_score > 80 else "Medium" if total_score > 50 else "Low",
            "flags": ["INCOMPLETE"] if completeness < 60 else []
        }
