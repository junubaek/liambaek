
import json
import os
from connectors.openai_api import OpenAIClient

class JDAnalyzerV4:
    def __init__(self, openai_client):
        self.openai = openai_client
        # Load Universal Ontology for context
        ontology_path = os.path.join(os.path.dirname(__file__), "headhunting_engine/universal_ontology.json")
        try:
            with open(ontology_path, "r", encoding="utf-8") as f:
                self.ontology = json.load(f)
        except:
            self.ontology = {}

    def analyze(self, jd_text: str) -> dict:
        """
        [v5.2] Universal 7-Axis Extraction Engine
        Converts Job Description into high-fidelity hiring signals.
        """
        system_prompt = """
You are a structured hiring signal extraction engine (Universal v5.2).
Convert the Job Description into precise 7-Axis signals.

[7-AXIS DEFINITION]
1. Role Family: Single dominant category (e.g., SW_Backend, GA_Operations, HR_Talent, SCM_Logistics, Strategy_Planning, Sales_B2B).
2. Seniority Required: Minimum years of experience (int).
3. Leadership Level: Individual Contributor | Team Lead | Department Head | Executive.
4. Functional Domains: Actual work areas.
5. Experience Patterns: Concrete execution/leadership patterns (Project types, NOT tools).
   - e.g., Lease_Negotiation, Compensation_Framework_Design, Org_Restructuring, Inventory_Optimization.
6. Impact Requirements: Quantitative scale/scope (Budget scale, Headcount, Project scope).
7. Hard Constraints: Non-negotiable requirements (Specific certifications, degree, industry experience).

[CRITICAL JUDGMENT]
- Experience Pattern is NOT a tool name (e.g., Slack) or a job title. 
- It represents "What the person actually DID/LED".

Output JSON:
{
  "role_family": "",
  "seniority_required": 0,
  "leadership_level": "",
  "functional_domains": [],
  "experience_patterns": [],
  "impact_requirements": {
    "scale_type": "Budget | Headcount | Revenue | Branches | Area",
    "quant_signal_required": true/false
  },
  "hard_constraints": [],
  "risk_factors": ["Niche Domain | Over-Specified | Comp-Gap"],
  "strategy_clues": []
}
"""
        user_prompt = f"Analyze this JD:\n{jd_text[:8000]}"
        
        try:
            response = self.openai.get_chat_completion(system_prompt, user_prompt)
            clean_json = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            # Hybrid mapping for app_product.py backward compatibility
            data["domain"] = data.get("role_family", "Unknown")
            data["seniority"] = data.get("leadership_level", "Middle")
            data["patterns"] = data.get("experience_patterns", [])
            data["years_range"] = {"min": data.get("seniority_required", 0), "max": None}
            
            return data
        except Exception as e:
            print(f"JD Analyzer V4 Error: {e}")
            return {"domain": "Unknown", "must_patterns": [], "must_skills": []}
