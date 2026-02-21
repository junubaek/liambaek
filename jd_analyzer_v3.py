import json
from connectors.openai_api import OpenAIClient

ROLE_EXPERIENCE_MAPPING = {
    "Data Engineer": {
        "searchable_keywords": [
            "Data Engineer", "데이터 엔지니어",
            "Airflow", "Spark", "Kafka", "ETL",
            "데이터 파이프라인", "Hadoop"
        ],
        "typical_experience": [
            "데이터 파이프라인 구축",
            "ETL 프로세스 설계",
            "실시간 데이터 처리"
        ],
        "avoid_keywords": ["데이터 분석 능력"]  # 너무 일반적
    },
    
    "Frontend Engineer": {
        "searchable_keywords": [
            "Frontend", "React", "Vue", "Angular",
            "TypeScript", "Webpack", "Next.js"
        ],
        "typical_experience": [
            "SPA 개발 경험",
            "상태 관리 (Redux, Zustand)",
            "반응형 웹 구현"
        ],
        "avoid_keywords": ["협업 능력", "커뮤니케이션"]
    },

    "Product Owner": {
        "searchable_keywords": [
            "Product Owner", "PO", "PM", "Service Planning", "기획", 
            "Jira", "Confluence", "Backlog", "Roadmap", "User Story"
        ],
        "typical_experience": [
            "Product Lifecycle Management",
            "데이터 기반 지표 도출",
            "백로그 우선순위 설정"
        ],
        "avoid_keywords": ["문제 해결 능력", "협업 능력", "소통", "커뮤니케이션", "문제 해결"]
    },
    # Korean Aliases
    "프로덕트 오너": "Product Owner",
    "데이터 엔지니어": "Data Engineer",
    "프론트엔드 엔지니어": "Frontend Engineer"
}

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
        You are a specialized Recruitment Token Extractor (V3).
        Your ONLY task is to extract industry-standard resume keywords (hard skills, titles, tools).

        [CRITICAL RULES]
        1. ❌ STRICTLY FORBIDDEN: "Communication", "Passion", "Mindset", "Collaboration", "Ability", "Thinking", "Proactive", "Problem Solving".
        2. ✅ ONLY EXTRACT tokens that a candidate would put in their "Skills" or "Work Experience" section.
        3. ✅ USE ENGLISH for `canonical_role` (e.g. Product Owner) and `core_signals` (e.g. Jira, Backlog) if possible, as these are standardized across resumes.
        4. ✅ AUTOMATICALLY INFER standard tools for the role.
        5. ✅ TRANSLATE vague JD text into concrete tokens.

        Output JSON Schema:
        {
          "canonical_role": "Standardized Job Title in English (e.g. Product Owner)",
          "inferred_role": "Functional name for search (can be Korean/English)",
          "core_signals": ["Concrete verifiable tokens (Prefer English/Industry terms)"],
          "supporting_signals": ["Tools/Tech skills"],
          "context_signals": ["Industry nouns"],
          "explicit_disqualifiers": [],
          "hidden_signals": ["B2B", "SaaS", etc.],
          "interview_checkpoints": []
        }
        """
        
        user_prompt = f"Analyze this JD for a {self.__class__.__name__}:\n{jd_text[:4000]}"
        
        try:
            response = self.openai.get_chat_completion(system_prompt, user_prompt)
            clean_json = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            # [PHASE 3.1] Role-Based Knowledge Injection
            canonical_role_raw = data.get("canonical_role", "")
            
            # Case-insensitive / Partial matching for mapping
            mapping = None
            role_to_use = canonical_role_raw
            
            # 1. Direct Alias or Key Check
            if canonical_role_raw in ROLE_EXPERIENCE_MAPPING:
                entry = ROLE_EXPERIENCE_MAPPING[canonical_role_raw]
                if isinstance(entry, str):
                    role_to_use = entry
                    mapping = ROLE_EXPERIENCE_MAPPING.get(role_to_use)
                else:
                    mapping = entry
                    role_to_use = canonical_role_raw
            
            # 2. Fuzzy/Partial Check
            if not mapping:
                for key, val in ROLE_EXPERIENCE_MAPPING.items():
                    if isinstance(val, str): continue # Skip aliases
                    if key.lower() in canonical_role_raw.lower() or canonical_role_raw.lower() in key.lower():
                        mapping = val
                        role_to_use = key
                        break
            
            if isinstance(mapping, dict):
                data["canonical_role"] = role_to_use # Standardize
            
            # Apply abstract signal filtering to ALL categories
            data["hidden_signals"] = self._filter_abstract_signals(data.get("hidden_signals", []))
            data["core_signals"] = self._filter_abstract_signals(data.get("core_signals", []))
            data["supporting_signals"] = self._filter_abstract_signals(data.get("supporting_signals", []))
            data["context_signals"] = self._filter_abstract_signals(data.get("context_signals", []))

            # Inject Mapping Knowledge
            if mapping:
                # Add mandatory keywords to core_signals if not present
                existing_core = [s.lower() for s in data["core_signals"]]
                for kw in mapping.get("searchable_keywords", []):
                    if kw.lower() not in existing_core:
                        data["core_signals"].append(kw)
                
                # Add typical experience to sub-signals
                data["hidden_signals"].extend(mapping.get("typical_experience", []))
                
                # Remove avoided keywords
                avoid = [a.lower() for a in mapping.get("avoid_keywords", [])]
                data["core_signals"] = [s for s in data["core_signals"] if str(s).lower() not in avoid]
                data["supporting_signals"] = [s for s in data["supporting_signals"] if str(s).lower() not in avoid]

            # Legacy Key Mapping for app.py backward compatibility
            data["must"] = data.get("core_signals", [])
            data["nice"] = data.get("supporting_signals", [])
            data["domain"] = data.get("context_signals", [])
            data["role"] = data.get("canonical_role", "Unknown")
            
            # [Fix] JDNormalizer Compatibility (expecting must_skills/nice_skills/explicit_skills)
            data["must_skills"] = data.get("core_signals", [])
            data["explicit_skills"] = data.get("core_signals", [])
            data["nice_skills"] = data.get("supporting_signals", [])
            data["title_candidates"] = [data.get("canonical_role", ""), data.get("inferred_role", "")]
            data["domain_clues"] = data.get("context_signals", [])
            
            # Ensure mandatory fields for app.py
            if "seniority" not in data: data["seniority"] = "Middle"
            if "years_range" not in data: data["years_range"] = {"min": 0, "max": None}
            if "confidence_score" not in data: data["confidence_score"] = 100
            
            data["inferred_role"] = data.get("inferred_role", data.get("canonical_role", "")) + " (V3)"
            
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
            "마인드", "열정", "사고", "능력", "태도", "역량", "소통", "협업", "해결", "경험", "지식", "이해",
            "관리", "조율", "개선", "커뮤니케이션", "문제", "적극적", "주도적", "원활한", "보유자",
            "mindset", "passion", "thinking", "ability", "attitude", "communication", "collaboration", "proactive",
            "experience", "knowledge", "understanding", "management", "coordination", "improvement"
        ]
        if not isinstance(signals, list): return []
        
        filtered = []
        for sig in signals:
            sig_str = str(sig).lower().strip()
            # If the entire signal is just an abstract word or very short generic phrase, skip it
            if len(sig_str) < 2: continue
            
            # Check against patterns
            is_abstract = any(pattern in sig_str for pattern in ABSTRACT_PATTERNS)
            
            # Exception: If it's a technical keyword combined with an abstract word (e.g. "React 경험"), 
            # we might want to keep it, but V3's goal is PURE tokens. So we are strict.
            if not is_abstract:
                filtered.append(sig)
        return filtered
