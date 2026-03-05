import json
from app.connectors.openai_api import OpenAIClient

class JDParserV3:
    """
    JD Parser v3: Extracts 7-axis recruitment signals from raw JD text.
    Axes: Role Family, Seniority, Leadership, Domains, Patterns, Impact, Constraints.
    """
    def __init__(self, openai_client: OpenAIClient, ontology_path: str):
        self.client = openai_client
        with open(ontology_path, 'r', encoding='utf-8') as f:
            self.ontology = json.load(f)

    def parse_jd(self, jd_text: str) -> dict:
        role_families = ", ".join(self.ontology.keys())
        
        prompt = f"""
You are a Senior Strategic Headhunter AI. Your task is to extract high-precision recruitment signals from a Job Description (JD) using the 7-Axis Universal Matching Framework.

[DOMAIN KNOWLEDGE: UNIVERSAL ONTOLOGY v5]
{json.dumps(self.ontology, indent=2)}

[7-AXIS EXTRACTION RULES]
1. role_family: Choose EXACTLY ONE from: {role_families}.
2. seniority_required: Integer (Years of experience required).
3. leadership_level: IC | Team Lead | Department Head | Executive.
4. functional_domains: List of domains from ONTOLOGY that match the JD scope.
5. experience_patterns: List of specific project/execution patterns from ONTOLOGY.
6. impact_requirements: Dictionary of quantified requirements (e.g., "Budget": "500M KRW").
7. hard_constraints: List of absolute deal-breakers (Degree, Location, Language).

[JD TEXT]
{jd_text[:8000]}

[OUTPUT_FORMAT_JSON]
{{
  "role_family": "",
  "seniority_required": 0,
  "leadership_level": "",
  "functional_domains": [],
  "experience_patterns": [],
  "impact_requirements": {{}},
  "hard_constraints": []
}}
"""
        try:
            # Use JSON mode for reliable extraction
            parsed_data = self.client.get_chat_completion_json(prompt)
            return parsed_data
        except Exception as e:
            print(f"❌ JD Parser v3 Error: {e}")
            return {
                "role_family": "Unclassified",
                "seniority_required": 0,
                "leadership_level": "IC",
                "functional_domains": [],
                "experience_patterns": [],
                "impact_requirements": {},
                "hard_constraints": ["Parsing Error"]
            }

if __name__ == "__main__":
    # Test stub (requires API Key)
    pass
