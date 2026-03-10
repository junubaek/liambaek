
import json
import os
from connectors.openai_api import OpenAIClient

class JDAnalyzerV5:
    def __init__(self, openai_client):
        self.openai = openai_client
        # Load Universal Ontology
        ontology_path = os.path.join(os.path.dirname(__file__), "headhunting_engine/universal_ontology.json")
        try:
            with open(ontology_path, "r", encoding="utf-8") as f:
                self.ontology = json.load(f)
        except:
            self.ontology = {}

    def analyze(self, jd_text: str) -> dict:
        """
        [v5.3] Standardized Pattern Extraction Engine
        Enforces use of patterns from the universal ontology.
        """
        # Collect all allowed patterns for the prompt
        allowed_patterns = []
        for sector_data in self.ontology.get("sectors", {}).values():
            allowed_patterns.extend(sector_data.get("patterns", []))
        allowed_patterns = sorted(list(set(allowed_patterns)))

        system_prompt = """
You are a structured hiring signal extraction engine (Standardized v5.3).
Convert the Job Description into precise 7-Axis signals.

[CRITICAL: ALLOWED EXPERIENCE PATTERNS]
You MUST ONLY use patterns from this list if they match the JD. Do NOT invent new pattern names.
Allowed Patterns: """ + ", ".join(allowed_patterns) + """

[7-AXIS DEFINITION]
1. Role Family: Single dominant category (e.g., SW_Backend, Strategy_Planning, Sales_B2B, Finance_Accounting).
2. Seniority Required: Minimum years of experience (int).
3. Leadership Level: Individual Contributor | Team Lead | Department Head | Executive.
4. Functional Domains: Actual work areas.
5. Experience Patterns: Concrete execution/leadership patterns chosen ONLY from the allowed list above.
6. Impact Requirements: Quantitative scale/scope (Budget scale, Headcount, Project scope).
7. Hard Constraints: Non-negotiable requirements (Specific certifications, degree, industry experience).

Output JSON:
{
  "role_family": "",
  "seniority_required": 0,
  "leadership_level": "",
  "functional_domains": [],
  "experience_patterns": [],
  "impact_requirements": {
    "scale_type": "Budget | Headcount | Revenue | Branches | Area",
    "quant_signal_required": true
  },
  "hard_constraints": [],
  "risk_factors": [],
  "strategy_clues": []
}
"""
        user_prompt = "Analyze this JD and map to standardized patterns:\n" + jd_text[:8000]
        
        try:
            response = self.openai.get_chat_completion(system_prompt, user_prompt)
            clean_json = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            # Compatibility Mapping
            data["domain"] = data.get("role_family", "Unknown")
            data["seniority"] = data.get("leadership_level", "Middle")
            data["patterns"] = data.get("experience_patterns", [])
            data["years_range"] = {"min": data.get("seniority_required", 0), "max": None}
            
            return data
        except Exception as e:
            print(f"JD Analyzer V5 Error: {e}")
            return {"domain": "Unknown", "patterns": [], "must_skills": []}
