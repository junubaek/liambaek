
import json
from connectors.openai_api import OpenAIClient

class JDAnalyzerV3:
    def __init__(self, openai_client):
        self.openai = openai_client
        
    def analyze(self, jd_text: str) -> dict:
        """
        Analyzes JD using a 2-step Verifiable Experience Extraction (V3).
        1. Infer the Industry-standard Role (PO, PM, Backend, etc.)
        2. Map to Verifiable Experiences and Skills that appear on resumes.
        """
        system_prompt = """
        You are a Expert Recruitment Consultant (V3 - Verifiable Experience Mode-S).
        Your goal is to translate JD requirements into VERIFIABLE resume tokens.

        [STEP 1: INFER ROLE & TOOLING]
        - Identify the industry-standard role (e.g., Product Owner, Service Planner, Backend Engineer).
        - **IMPORTANT**: If the role is Product-related (PM/PO), you MUST include "Product Owner", "PO", and "서비스 기획" as core signals if appropriate.
        - **IMPORTANT**: Infer common tools even if not explicitly named (e.g., PM/PO likely use "Jira", "Confluence", "Slack").

        [STEP 2: EXTRACT RESUME TOKENS]
        - ❌ AVOID: Abstract skills like "Communication", "Proactive", "Passion", "Problem Solving", "Customer-centric".
        - ✅ EXTRACT: Hard skills, Role Titles, Tools, and Specific Experiences.
        - Think: "What would a candidate write on their resume for this job?"
        - Example: Instead of "협업하여 제품 기획", use ["Product Owner", "PO Experience", "Backlog Management"].
        
        [STEP 3: HIDDEN SIGNALS]
        - Extract nouns describing the specific BUSINESS or TECH context.
        - ❌ AVOID: "Mindset", "Culture", "Attitude".

        Output JSON Schema:
        {
          "canonical_role": "Standardized Job Title (e.g. Product Owner, Backend Engineer)",
          "inferred_role": "Functional Role name used in candidates' resumes",
          "core_signals": ["List of VERIFIABLE experience/skill tokens (Max 5)"],
          "supporting_signals": ["List of technical tools or secondary hard skills"],
          "context_signals": ["Industry/Work context tokens (Nouns only)"],
          "explicit_disqualifiers": ["Negative signals found in JD"],
          "hidden_signals": ["Contextual clues (e.g. 'B2B SaaS')"],
          "interview_checkpoints": ["Soft skills/Logic to check in interview"]
        }
        """
        
        user_prompt = f"Analyze this JD for a {self.__class__.__name__}:\n{jd_text[:4000]}"
        
        try:
            response = self.openai.get_chat_completion(system_prompt, user_prompt)
            clean_json = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            # Apply abstract signal filtering
            data["hidden_signals"] = self._filter_abstract_signals(data.get("hidden_signals", []))
            data["core_signals"] = self._filter_abstract_signals(data.get("core_signals", []))
            
            # Legacy Key Mapping for app.py backward compatibility
            data["must"] = data.get("core_signals", [])
            data["nice"] = data.get("supporting_signals", [])
            data["domain"] = data.get("context_signals", [])
            data["role"] = data.get("canonical_role", "Unknown")
            
            # Ensure mandatory fields for app.py
            if "seniority" not in data: data["seniority"] = "Middle"
            if "years_range" not in data: data["years_range"] = {"min": 0, "max": None}
            if "confidence_score" not in data: data["confidence_score"] = 100
            
            return data
        except Exception as e:
            print(f"JD Analyzer V3 Error: {e}")
            return {
                "canonical_role": "Unknown",
                "core_signals": [],
                "supporting_signals": [],
                "context_signals": [],
                "explicit_disqualifiers": [],
                "hidden_signals": [],
                "interview_checkpoints": []
            }

    def _filter_abstract_signals(self, signals: list) -> list:
        """Removes abstract concepts like 'Mindset', 'Passion', etc."""
        ABSTRACT_PATTERNS = [
            "마인드셋", "열정", "사고", "능력", "태도", "역량",
            "mindset", "passion", "thinking", "ability", "attitude"
        ]
        filtered = []
        for sig in signals:
            if not any(pattern in str(sig).lower() for pattern in ABSTRACT_PATTERNS):
                filtered.append(sig)
        return filtered
