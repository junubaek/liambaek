
import json
import re

class ResumeParser:
    def __init__(self, openai_client):
        self.client = openai_client

    def parse(self, resume_text: str) -> dict:
        """
        Parses raw resume text into a structured JSON using LLM.
        """
        if not resume_text:
             return {}

        prompt = f"""
You are an expert Resume Parser. 
Extract structured data from the resume text below.
Be precise and factual. Do not hallucinate.

[RESUME TEXT]
{resume_text[:10000]}

[SCHEMA INSTRUCTIONS]
Output JSON with the following structure:
{{
  "basics": {{
    "name": "Candidate Name (or Unknown)",
    "email": "Email (or null)",
    "phone": "Phone (or null)",
    "total_years_experience": (Integer estimate based on career start year)
  }},
  "skills": ["List", "of", "technical", "skills"],
  "work_experience": [
    {{
      "company": "Company Name",
      "role": "Job Title",
      "start_year": "YYYY",
      "end_year": "YYYY (or Present)",
      "description": "Brief summary of responsibilities"
    }}
  ],
  "education": [
    {{
      "school": "School Name",
      "degree": "Degree (BS, MS, PhD)",
      "major": "Major"
    }}
  ],
  "summary": "A professional summary (3-4 sentences) effectively describing the candidate's core value proposition."
}}

If a field is missing, use null or empty list.
"""
        try:
            # Use the existing JSON mode method in OpenAIClient
            parsed_data = self.client.get_chat_completion_json(prompt)
            # Validation: Ensure key fields exist
            if not parsed_data.get("basics"):
                parsed_data["basics"] = {}
            if not parsed_data.get("skills"):
                parsed_data["skills"] = []
                
            return parsed_data
            
        except Exception as e:
            print(f"❌ Resume Parsing Error: {e}")
            return {}
