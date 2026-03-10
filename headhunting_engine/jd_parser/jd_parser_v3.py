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
You are a Senior Strategic Headhunter AI. Your task is to extract high-precision recruitment signals from a Job Description (JD) using the AI Talent Intelligence OS v6.3.3 Universal Ontology.

[CRITICAL: FUNCTIONAL-ONLY PRINCIPLE]
- EXCLUDE SOFT SKILLS: Completely ignore terms like Communication, Teamwork, Leadership (as an attitude), Passion, Sincerity, Collaboration, Problem Solving (as an attitude).
- FOCUS ON HARD SKILLS: Extract specific tools, frameworks, protocols, technical architectures (e.g., RTL Design, LLM Fine-tuning, MCP Protocol).
- FOCUS ON FUNCTIONAL PATTERNS: Extract concrete business or technical requirements and outcomes (e.g., API Latency Optimization, KPI Framework Design, Yield Rate Improvement).

[9-SECTOR STRUCTURE]
Sectors: {", ".join(sectors_list)}

[MATCHING RULES: STRATEGIC FUNCTIONALITY]
1. Prioritize FUNCTIONAL OBJECTIVES over Abstract Descriptions. 
   - If JD mentions "KPI", "Strategy", "Insights" -> Sector: CORPORATE/DATA_AI. 
   - Focus on hard deliverables: "Metrics Framework", "Product Analytics", "Yield Optimization".
2. Cross-Sector Flag: If the role bridges two worlds (e.g., AI + Semiconductor, Finance + Tech), set `cross_sector_flag` to true.

[7-AXIS EXTRACTION RULES]
...
[JD TEXT]
{jd_text[:8000]}

[OUTPUT_FORMAT_JSON]
{{
  "jd_profile": {{
    "job_title": "",
    "primary_sector": "",
    "is_new_trend_detected": false
  }},
  "secondary_sectors": [],
  "cross_sector_flag": false,
  "seniority_required": 0,
  "leadership_level": "",
  "functional_domains": [],
  "must_patterns": [],
  "experience_patterns": [],
  "discovered_demands": [],
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
                "jd_profile": {
                    "job_title": "Unclassified",
                    "primary_sector": "Unclassified",
                    "is_new_trend_detected": False
                },
                "secondary_sectors": [],
                "cross_sector_flag": False,
                "seniority_required": 0,
                "leadership_level": "IC",
                "functional_domains": [],
                "must_patterns": [],
                "experience_patterns": [],
                "impact_requirements": {},
                "hard_constraints": ["Parsing Error"],
                "discovered_demands": []
            }

if __name__ == "__main__":
    # Test stub (requires API Key)
    pass
