
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
You are a Senior Experience Extraction Engine (AI Talent Intelligence OS v6.3.3).
Your task is to convert the resume into a structured Experience Graph focusing on strategic functional patterns, hard skills, and career trajectories.

[CRITICAL: FUNCTIONAL-ONLY PRINCIPLE]
- EXCLUDE SOFT SKILLS: Completely ignore terms like Communication, Teamwork, Leadership (as an attitude), Passion, Sincerity, Collaboration, Problem Solving (as an attitude).
- FOCUS ON HARD SKILLS: Extract specific tools, frameworks, protocols, technical architectures (e.g., RTL Design, LLM Fine-tuning, MCP Protocol).
- FOCUS ON FUNCTIONAL PATTERNS: Extract concrete business or technical actions and achievements (e.g., API Latency Optimization, KPI Framework Design, Yield Rate Improvement).

[RESUME TEXT]
{resume_text[:12000]}

[SCHEMA INSTRUCTIONS]
Output JSON:
{{
  "candidate_profile": {{
    "primary_sector": "Pick one OR more (separated by |) from: TECH_SW | TECH_HW | SEMICONDUCTOR | DATA_AI | PRODUCT | BUSINESS | SECURITY | CORPORATE | CREATIVE",
    "secondary_sectors": [],
    "cross_sector_flag": bool,
    "cross_sector_type": "Optional type (e.g., AI_Semiconductor, DevSecOps)",
    "total_years_experience": 0,
    "current_leadership_level": "IC | Team Lead | Department Head | Executive",
    "experience_summary": "1) Achievement A... 2) Role B... (Numbered list summary focusing on FUNCTIONAL results)"
  }},
  "patterns": [
    {{
      "pattern": "Standardized Functional Pattern",
      "depth": "Owned | Led | Applied | Assisted | Mentioned",
      "depth_weight": 0.0,
      "impact": "Quantified or Qualitative functional result",
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

[DEPTH RULES (v6.3)]
- Owned (1.00): Architected system, defined technical/business direction, final authority.
- Led (0.85): Core contributor, tech lead, driving design of functional modules.
- Applied (0.65): Independent implementation of functional tasks.
- Assisted (0.40): Supported functional implementation under guidance.
- Mentioned (0.20): Knowledge of tool/task without deep functional evidence.

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
