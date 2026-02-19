import json
from jd_confidence import estimate_jd_confidence
from search_strategy import decide_search_strategy

class JDAnalyzer:
    def __init__(self, openai_client):
        self.openai = openai_client

    def analyze(self, jd_text: str) -> dict:
        """
        Analyzes the Job Description to extract:
        1. Semantic Data (Role, Skills, etc.) via LLM
        2. Confidence Score
        3. Search Strategy
        """
        if not jd_text or len(jd_text) < 10:
            return {}

        # 1. Semantic Extraction
        semantic_data = self._extract_semantics(jd_text)
        
        # 2. Confidence Estimation
        # Structure data for confidence engine
        conf_input = {
            "explicit_skills": semantic_data.get("must_skills", []),
            "title_candidates": [
                semantic_data.get("primary_role", ""),
                semantic_data.get("inferred_role", "")  # Add inferred role
            ],
            "domain_clues": [semantic_data.get("domain", "")],
            "seniority_clues": [semantic_data.get("seniority", "")]
        }
        
        confidence_score = estimate_jd_confidence(conf_input)
        
        # 3. Strategy Decision
        strategy = decide_search_strategy(confidence_score)
        
        # 4. Integrate Results
        semantic_data["confidence_score"] = int(confidence_score * 100)
        semantic_data["is_ambiguous"] = (confidence_score < 0.7)
        semantic_data["search_strategy"] = strategy
        
        return semantic_data

    def _extract_semantics(self, jd_text: str) -> dict:
        """
        Uses LLM to extract structured data from JD text.
        """
        prompt = f"""
        You are a **Senior Executive Search Partner** (Headhunter) in Korea with 20+ years of experience.
        Your goal is to infer the **REAL** requirements behind the Job Description (JD) and identifying hidden signals.
        
        [JOB DESCRIPTION]
        {jd_text[:4000]}
        
        [TASK]
        1. **Domain Detection**: Identify the specific industry/domain (e.g., "Semiconductor / NPU", "Fintech").
        2. **Persona Adoption**: Adopt the mindset of a specialist headhunter in that domain.
        3. **Deep Inference**:
           - **Inferred Role**: What is the canonical role? (e.g., JD says "PM" -> Inferred "Product Owner")
           - **Hidden Signals**: What is implied but not stated? (e.g., "Fast-paced" -> "Startup Mindset")
           - **Negative Signals**: Who should be REJECTED? (e.g., "Web Dev applying for Embedded")
        4. **Search Queries**: Generate 3 distinct boolean/semantic queries to find the perfect candidate.
        
        [INSTRUCTIONS]
        Analyze the JD and extract the following fields. **All output values must be in Korean (Example: "Project Manager" -> "프로젝트 매니저").**
        
        [OUTPUT FORMAT - STRICT JSON]
        {{
            "primary_role": "String (Official Title in Korean, e.g. 백엔드 개발자)",
            "inferred_role": "String (The REAL role title in Korean, e.g. 고성능 서버 엔지니어)",
            "seniority": "String (Junior, Senior, Lead, Executive - in Korean)",
            "min_years": Integer (0 if unsure),
            "domain": "String (Specific Domain in Korean, e.g. 핀테크)",
            "must_skills": ["Critical Skill 1", "Critical Skill 2", ...],
            "nice_skills": ["Bonus Skill 1", "Bonus Skill 2", ...],
            "hidden_signals": ["Signal 1 (Korean)", "Signal 2 (Korean)", ...],
            "negative_signals": ["Reject logic 1 (Korean)", "Reject logic 2 (Korean)", ...],
            "search_queries": [
                "Query 1 (Natural Language - Korean/English Mix)",
                "Query 2 (Skill focus)",
                "Query 3 (Domain focus)"
            ]
        }}
        """
        
        try:
            resp = self.openai.get_chat_completion("You are a smart JSON extractor.", prompt)
            if not resp: return {}
            
            clean = resp.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            
            # Normalize keys if needed (LLM can be inconsistent)
            if "must_have_skills" in data: data["must_skills"] = data.pop("must_have_skills")
            
            return data
        except Exception as e:
            print(f"Error in JD extraction: {e}")
            return {}
