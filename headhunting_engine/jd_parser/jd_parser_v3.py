import json
# Supports both OpenAI and Gemini clients

class JDParserV3:
    """
    JD Parser v3: Extracts 7-axis recruitment signals from raw JD text.
    v6.2: Supports both OpenAI and Gemini clients.
    """
    def __init__(self, client, ontology_path: str):
        self.client = client
        with open(ontology_path, 'r', encoding='utf-8') as f:
            self.ontology = json.load(f)

    def parse_jd(self, jd_text: str) -> dict:
        sectors_list = list(self.ontology["sectors"].keys())
        all_patterns = []
        for s in sectors_list:
            all_patterns.extend(self.ontology["sectors"][s]["patterns"])
        all_patterns = sorted(list(set(all_patterns)))

        prompt = f"""
You are a Senior Strategic Headhunter AI. Your task is to extract high-precision recruitment signals from a Job Description (JD) using the AI Talent Intelligence OS v6.2 Universal Ontology.

[9-SECTOR STRUCTURE]
Sectors: {", ".join(sectors_list)}

[MATCHING RULES: STRATEGY VS ENGINEERING]
1. Prioritize BUSINESS OBJECTIVES over Technical Tools. 
   - If JD mentions "KPI", "Strategy", "Insights", "Business Plan" -> Sector: CORPORATE/DATA_AI. 
   - DO NOT extract "Data_Pipeline_Building" unless the JD specifically mentions building E/L/T architecture.
   - For Analyst roles, prioritize: Corporate_Strategy, Metrics_Framework, Product_Analytics, KPI_Framework_Design.
2. Cross-Sector Flag: If the role bridges two worlds (e.g., AI + Semiconductor, Finance + Tech), set `cross_sector_flag` to true.

[7-AXIS EXTRACTION RULES]
1. primary_sector: The dominant sector. Choose from: {", ".join(sectors_list)}.
2. secondary_sectors: List of additional relevant sectors.
3. cross_sector_flag: Boolean.
4. seniority_required: Integer (Years of experience required).
5. leadership_level: IC | Team Lead | Department Head | Executive.
6. functional_domains: List of domains matching the JD's strategic scope.
7. experience_patterns: List 5-8 patterns from the ONTOLOGY. 
   - CRITICAL: List the "Non-negotiable" (Must-have) patterns first.
8. impact_requirements: Dictionary of quantified requirements.
9. hard_constraints: List of absolute deal-breakers.

[JD TEXT]
{jd_text[:8000]}

[OUTPUT_FORMAT_JSON]
{{
  "primary_sector": "",
  "secondary_sectors": [],
  "cross_sector_flag": false,
  "seniority_required": 0,
  "leadership_level": "",
  "functional_domains": [],
  "experience_patterns": [],
  "impact_requirements": {{}},
  "hard_constraints": []
}}
"""
        try:
            # Detect client type and use appropriate method
            if hasattr(self.client, "get_chat_completion_json"):
                # Both our OpenAIClient and GeminiClient now have this method
                parsed_data = self.client.get_chat_completion_json(prompt)
            else:
                raise ValueError("Unsupported client type")
            
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
