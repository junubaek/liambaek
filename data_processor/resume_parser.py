
import json
import re
from connectors.openai_api import OpenAIClient

def parse_resume_to_json(openai_client: OpenAIClient, text_content: str):
    """
    Uses LLM to parse raw resume text into a structured JSON object.
    Extracts: Summary, Work Experience (List), Skills (Categorized), Education, Projects.
    """
    
    prompt = f"""
    You are an expert Resume Parser. Your job is to extract structured data from the provided resume text.
    
    [INSTRUCTIONS]
    1. Extract the candidate's **Name** and a **Professional Summary** (3 sentences max).
    2. Extract **Work Experience** as a list. For each role:
       - Company Name
       - Role / Title
       - Period (Start - End)
       - Duration (in years, estimated)
       - Key Skills used in this specific role
       - Description / Achievements (summarized bullets)
    3. Extract **Skills** and categorize them:
       - Languages (e.g. Python, C++)
       - Frameworks/Libs (e.g. React, PyTorch)
       - Infrastructure/Tools (e.g. AWS, Docker, Git)
       - Domain Knowledge (e.g. Finance, Semiconductor, eCommerce)
    4. Extract **Education** (Degree, Major, School).
    5. Extract **Projects** (Name, Tech Stack, Description).
    6. Estimate **Total Years of Experience** (number).

    [RESUME TEXT]
    {text_content[:15000]}  # Limit to ~15k chars to fit context if needed
    
    [OUTPUT FORMAT - STRICT JSON]
    {{
        "name": "String",
        "summary": "String",
        "total_years_experience": Number,
        "work_experience": [
            {{
                "company": "String",
                "role": "String",
                "period": "String",
                "duration_years": Number,
                "key_skills": ["String", ...],
                "description": "String"
            }},
            ...
        ],
        "skills": {{
            "languages": ["String", ...],
            "frameworks": ["String", ...],
            "infrastructure": ["String", ...],
            "domain_knowledge": ["String", ...]
        }},
        "education": [
            {{
                "school": "String",
                "degree": "String",
                "major": "String"
            }}
        ],
        "projects": [
            {{
                "name": "String",
                "tech_stack": ["String", ...],
                "description": "String"
            }}
        ]
    }}
    """
    
    try:
        # Use a model with good JSON capability (GPT-4o or GPT-3.5-turbo-1106+)
        # Assuming OpenAIClient has a method to allow specifying model or consistent prompt
        # We will use the existing get_chat_completion which likely wraps generic call.
        
        # If possible, force JSON mode if client supports it, otherwise prompt engineering.
        response = openai_client.get_chat_completion(
            system_prompt="You are a strict JSON extractor. Output ONLY valid JSON.",
            user_message=prompt
        )
        
        if not response:
            return {
                "name": "",
                "summary": "Parsing Failed (API Error)",
                "total_years_experience": 0,
                "work_experience": [],
                "skills": {},
                "education": [],
                "projects": []
            }

        # Clean markdown code blocks if present
        clean_json = response.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(clean_json)
        return data

    except Exception as e:
        print(f"  [!] Resume Parsing Failed: {e}")
        # Return empty structure
        return {
            "name": "",
            "summary": "Parsing Failed",
            "total_years_experience": 0,
            "work_experience": [],
            "skills": {},
            "education": [],
            "projects": []
        }
