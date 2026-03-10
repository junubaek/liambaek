
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

[LANGUAGE RULE]
- If the JD is in Korean, extract 'role_family', 'functional_domains', and 'hard_constraints' in Korean.
- 'experience_patterns' MUST ALWAYS be in English from the allowed list.

Output JSON:
{
  "role_family": "Korean Name",
  "seniority_required": 0,
  "leadership_level": "Korean Name",
  "functional_domains": ["Korean Domain 1", ...],
  "experience_patterns": ["English_Pattern_From_List", ...],
  "impact_requirements": {
    "scale_type": "Budget | Headcount | Revenue | Branches | Area",
    "quant_signal_required": true
  },
  "hard_constraints": ["Korean Constraint 1", ...],
  "risk_factors": [],
  "strategy_clues": []
}
"""
        user_prompt = "Analyze this JD and map to standardized patterns:\n" + jd_text[:8000]
        
        try:
            response = self.openai.get_chat_completion(system_prompt, user_prompt)
            clean_json = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            # Compatibility Mapping (Fat Dictionary for all app versions)
            data["must"] = data.get("functional_domains", [])
            data["must_have"] = data["must"]
            data["must_skills"] = data["must"]
            data["core_signals"] = data["must"]
            
            data["nice"] = data.get("hard_constraints", [])
            data["nice_to_have"] = data["nice"]
            data["nice_skills"] = data["nice"]
            data["supporting_signals"] = data["nice"]
            
            data["domain"] = [data.get("role_family", "Unknown")]
            data["domains"] = data["domain"]
            data["context_signals"] = data["domain"]
            
            data["role"] = data.get("role_family", "Unknown")
            data["primary_role"] = data["role"]
            data["canonical_role"] = data["role"]
            data["inferred_role"] = data["role"]
            data["role_family"] = data["role"]
            
            data["seniority"] = data.get("leadership_level", "Middle")
            data["years_range"] = {"min": data.get("seniority_required", 0), "max": None}
            
            # Missing fields in V5 (Initialize for UI)
            data["hidden_signals"] = data.get("strategy_clues", [])
            data["negative_signals"] = data.get("risk_factors", [])
            data["wrong_roles"] = []
            data["confidence_score"] = 100
            data["ambiguity"] = False
            data["search_contract"] = {
                "role_family": data["role"],
                "must_core": data["must"]
            }
            
            return data
        except Exception as e:
            print(f"JD Analyzer V5 Error: {e}")
            return {"domain": "Unknown", "patterns": [], "must_skills": []}
