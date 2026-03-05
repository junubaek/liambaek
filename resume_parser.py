
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
You are a Senior Experience Extraction Engine (AI Talent Intelligence OS v6.2).
Your task is to convert the resume into a structured Experience Graph focusing on strategic patterns, impact types, and career trajectories.

[RESUME TEXT]
{resume_text[:12000]}

[SCHEMA INSTRUCTIONS]
Output JSON:
{{
  "candidate_profile": {{
    "primary_sector": "TECH_SW | TECH_HW | SEMICONDUCTOR | DATA_AI | PRODUCT | BUSINESS | SECURITY | CORPORATE | CREATIVE",
    "secondary_sectors": [],
    "cross_sector_flag": bool,
    "cross_sector_type": "Optional type (e.g., AI_Semiconductor, DevSecOps)",
    "total_years_experience": 0,
    "current_leadership_level": "IC | Team Lead | Department Head | Executive"
  }},
  "patterns": [
    {{
      "pattern": "Standardized Pattern (e.g., RTL_Design, LLM_Fine_Tuning)",
      "depth": "Owned | Led | Applied | Assisted | Mentioned",
      "depth_weight": 0.0,
      "impact": "Quantified or Qualitative description",
      "impact_type": "Quantitative | Qualitative | Hybrid",
      "tools": []
    }}
  ],
  "career_path_quality": {{
    "avg_tenure_years": 0.0,
    "trajectory_grade": "Ascending | Stable | Neutral | Volatile | Declining",
    "job_moves": [
      {{ "from": "Company/Role", "to": "Company/Role", "type": "Promotion | Lateral | Drift", "score": 0 }}
    ],
    "career_path_score": 0
  }}
}}

[DEPTH RULES (v6.2)]
- Owned (1.00): Architected entire system, defined technical direction, final decision authority.
- Led (0.85): Core contributor, technical lead, mentoring, driving design of key modules.
- Applied (0.65): Independent implementation, built and deployed in production.
- Assisted (0.40): Contributed as team member, supported design/implementation under guidance.
- Mentioned (0.20): Familiar with, knowledge of, listed in skills without deep project detail.

[IMPACT TYPE RULES]
- Quantitative: TPS, Latency, MAU, Revenue, PPA, Tape-out success (Tech/Product/Sales/Finance).
- Qualitative: Risk prevention, Compliance, HR policy design, Strategy scoping (HR/Legal/Strategy).
- Hybrid: SCM optimization, SOC operations, Data pipelines (Data/Ops/Security).
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
