import json
from jd_confidence import estimate_jd_confidence
from search_strategy import decide_search_strategy

class JDAnalyzerV2:
    def __init__(self, openai_client):
        self.openai = openai_client

    def analyze(self, jd_text: str) -> dict:
        """
        Analyzes the Job Description using Domain Expert methodology (V2).
        1. Semantic Data (Role, Skills, Hidden Signals, Discriminator) via LLM
        2. Confidence Score (0-100)
        3. Search Strategy
        """
        if not jd_text or len(jd_text) < 10:
            return {}

        # 1. Semantic Extraction (Deep Dive)
        semantic_data = self._extract_semantics(jd_text)
        
        # 2. Confidence Estimation (Re-using V1 logic for compatibility check, 
        # but V2 has its own confidence_score from LLM. We might mix them or use LLM's.)
        # For now, we trust the LLM's 'confidence_score' more in V2, 
        # but let's calculate the V1 score as a fallback or component.
        conf_input = {
            "explicit_skills": semantic_data.get("must_skills", []),
            "title_candidates": [
                semantic_data.get("primary_role", ""),
                semantic_data.get("inferred_role", "")
            ],
            "domain_clues": [semantic_data.get("domain", "")],
            "seniority_clues": [semantic_data.get("seniority", "")]
        }
        
        # Calculate V1 score for strategy decision
        # (V2 LLM score is often better for qualitative confidence, V1 for quantitative coverage)
        v1_conf = estimate_jd_confidence(conf_input)
        
        # Use the MAX of V1 and V2 scores for strategy to be safe (or average them)
        llm_conf = semantic_data.get("confidence_score", 0) / 100.0
        final_conf = max(v1_conf, llm_conf)
        
        # 3. Strategy Decision
        strategy = decide_search_strategy(final_conf)
        
        # 4. Difficulty Assessment (V3.4 Feature)
        difficulty = self._calculate_difficulty(semantic_data)
        semantic_data["difficulty"] = difficulty
        
        # 5. Integrate Results
        # Ensure semantic_data has all keys expected by app.py
        semantic_data["confidence_score"] = int(final_conf * 100)
        semantic_data["is_ambiguous"] = (final_conf < 0.7)
        semantic_data["search_strategy"] = strategy
        
        # Map V2 specific keys to generic keys if needed (app.py expects 'must_skills' etc.)
        # The prompt already ensures compatibility.
        
        return semantic_data

    def _calculate_difficulty(self, data: dict) -> dict:
        """
        Calculates JD Difficulty Score (0-100) and suggests a Cutline.
        Factors:
        - Specificity (Length of Must Haves)
        - Seniority (Higher = Harder)
        - Niche Keywords (e.g. AI, Blockchain, Quant)
        """
        score = 30 # Base difficulty
        
        # 1. Skill Complexity
        must_skills = data.get("must_skills", [])
        score += len(must_skills) * 5  # +5 per skill
        
        # 2. Seniority Impact
        seniority = data.get("seniority", "Junior").lower()
        if "lead" in seniority or "manager" in seniority:
            score += 20
        elif "senior" in seniority or "head" in seniority:
            score += 15
        elif "c-level" in seniority or "director" in seniority:
            score += 30
            
        # 3. Domain Niche Check
        domain = data.get("domain", "").lower()
        niche_domains = ["blockchain", "ai", "machine learning", "quant", "crypto", "security", "defense"]
        if any(nd in domain for nd in niche_domains):
            score += 15
            
        # Cap Score
        score = min(score, 95)
        
        # Leveling
        if score >= 70:
            level = "Hard"
            cutline = 20 # Lower cutline for hard roles (Recall focused)
            desc = "🔥 매우 어려움 (시장 인재 부족 예상)"
        elif score >= 50:
            level = "Medium"
            cutline = 30 
            desc = "⚖️ 보통 (적절한 타겟팅 필요)"
        else:
            level = "Easy"
            cutline = 40 # Higher cutline for easy roles (Precision focused)
            desc = "✅ 무난함 (다수의 후보자 예상)"
            
        return {
            "score": score,
            "level": level,
            "suggested_cutline": cutline,
            "description": desc
        }

    def _extract_semantics(self, jd_text: str) -> dict:
        """
        Uses LLM with Domain Expert Prompting (Few-Shot) to extract deep insights.
        """
        prompt = f"""
        You are a **Domain Expert Headhunter** specialized in interpreting ambiguous Job Descriptions (JDs).
        Your capability goes beyond keyword extraction; you create a "Role Embedding" by understanding the *implicit* requirements.

        [OBJECTIVE]
        Analyze the Job Description to extract a **"Search Contract"** (Structured Resume Query).
        Your goal is to find facts that can be cross-checked against a candidate's written resume.
        
        [CRITICAL RULES - READ CAREFULLY]
        1. **VERIFIABILITY RULE**: 
           - ❌ STOP extracting "Startup Mindset", "Problem Solving", "Passion", "Communication". (These are interview criteria, NOT search criteria).
           - ✅ EXTRACT "Service Planning", "JIRA", "SQL", "AWS", "Internal Tools". (These are resume keywords).
        
        2. **NEGATIVE SIGNALS (STRICT NO-INFERENCE)**:
           - ❌ NEVER infer a negative signal from a missing preference. (e.g. "Insurance preferred" does NOT mean "No Insurance experience").
           - ✅ ONLY add if explicitly disqualified (e.g. "Junior Not Allowed", "Marketing PM Not Allowed", "No Agency Background").
        
        3. **HIDDEN SIGNALS = WORK CONTEXT (NOUN PHRASES ONLY)**:
           - ❌ NO TRAITS: Do not use adjectives like "Proactive", "Responsible", "Detail-oriented".
    2. Hidden Context (Work Environment & Tech Challenges):
        - Extract *implied* signals about the work environment or technical challenges.
        - **STRICT RULE**: Use only **NOUN PHRASES**. 
        - **BAN LIST**: Do NOT include personality traits or abstract concepts like "Passion", "Communication", "Proactive", "Startup Mindset", "Ownership", "Collaborative".
        - **GOOD EXAMPLES**: "High Traffic System", "Legacy Code Refactoring", "AWS Cloud Environment", "B2B SaaS", "Global Service Launch", "Data Pipeline Construction".
        - If the JD mentions "collaborating with designers", extract "Cross-functional Collaboration" ONLY if it implies a specific workflow (e.g. Agile/Scrum mentioned), otherwise ignore.
        
    3. Negative Signals (Explicit Disqualifiers ONLY):
        - Only extract clear "NOT" conditions or "Deal Breakers".
        - **STRICT RULE**: Do NOT infer negative signals from missing "Nice-to-have" skills.
        - **CRITICAL**: Do NOT include "Lack of Industry Knowledge" or "Domain Mismatch" (e.g., "No Finance Experience", "No Insurance understanding"). Domain knowledge is a preference, not a disqualifier.
        - **EXAMPLE**: If JD says "Preferred: Insurance experience", do NOT add "No Insurance experience" to negative signals.
        - **EXAMPLE**: If JD says "Must have Python", do NOT add "Java developer" unless explicitly excluded.
        - **RULE**: If you are unsure whether it's a negative signal, DO NOT generate it.
        - **VALID NEGATIVE SIGNALS**: "No agencies", "Must be fluent in Korean", "Visa sponsorship not available", "No remote work", "Job Hoppers".

    4. Search Contract (The Recruiting Strategy):
        - **Role Family**: Assign one: [PM/PO, Engineering, Design, Data, Business, Other].
        - **Product Type**: B2B / B2C / Platform / Internal Tool.
        - **Domain Optional**: List domains that are PREOFERED but NOT MANDATORY. *Most* domain experience (Fintech, E-commerce, etc.) should go here unless the JD says "Must have [Domain] experience" in the *Requirements* section.
        - **Must Core**: Essential Hard Skills/Tech Stack (e.g. Python, SQL, JIRA). Max 5.
        - **Nice**: Preferred skills or domains.

    Output JSON Format:
    {{
        "role_cluster": "Inferred Role",
        "years_range": {"min": 0, "max": 3},
        "must_skills": ["Skill 1", "Skill 2"],
        "nice_skills": ["Skill 3", "Skill 4"],
        "primary_role": "Job Title",
        "domain_experience": ["Domain 1"],
        "hidden_signals": ["Context 1", "Context 2"], 
        "negative_signals": ["Signal 1"],
        "search_contract": {{
            "role_family": "PM/PO",
            "product_type": "B2C",
            "domain_optional": ["Insurance"],
            "must_core": ["Service Planning", "JIRA"],
            "nice": ["SQL", "Data Analysis"]
        }},
        "confidence_score": 90
    }}
        
        **Case 2: Senior Backend (Clear)**
        - Input: "Server dev. Python/Django. No Juniors (5y+ only)."
        - Analysis:
            - Primary Role: "Backend Engineer"
            - Must Skills: ["Python", "Django", "API Design"]
            - Nice Skills: ["Cloud (AWS)"]
            - Negative Signals: ["Junior (Under 5 years experience)"]
            - Hidden Signals: ["Scalability focus"]
            - Search Contract:
                {{
                    "role_family": "Engineering",
                    "product_type": "Platform",
                    "domain_optional": [],
                    "must_core": ["Python", "Django"],
                    "nice": ["AWS"]
                }}
            - Confidence: 95

        [ANALYSIS STEPS]
        1. **Role Identification**: Extract verified title & functional role.
        2. **Search Contract Generation**: Build the structured query for the search engine.
        3. **Verifiable Signals**: Extract Hard Skills and Contextual Hidden Signals (Nouns).
        4. **Negative Signal**: Explicit disqualifiers only.

        [JOB DESCRIPTION]
        {jd_text[:5000]}

        [OUTPUT FORMAT - STRICT JSON]
        (Values must be in Korean for User readability, except standard Tech terms)
        {{
            "primary_role": "String (Official Title)",
            "inferred_role": "String (Functional Role, e.g. '서비스 기획자' or 'B2B PM')",
            "role_cluster": "String (Standard Category, e.g. 'Planning/PM')",
            "seniority": "String (e.g. '5년차 이상' or 'Senior')",
            "years_range": {
                "min": Integer (0 if undefined or 'Under N years'),
                "max": Integer (null if undefined or 'Over N years')
            },
            "domain": "String (e.g. '핀테크 Payment')",
            "must_skills": ["Hard Skill 1", "Hard Skill 2", ...],
            "nice_skills": ["Soft Skill 1", "Preference 2", ...],
            "hidden_signals": ["Work Context Noun 1", "Work Context Noun 2", ...],
            "negative_signals": ["Explicit Disqualifier 1", ...],
            "wrong_roles": ["This role is NOT X", ...],
            "search_contract": {{
                "role_family": "String (PM/PO, Backend, Frontend, etc.)",
                "product_type": "String (B2B, B2C, Platform, etc.)",
                "domain_optional": ["String (Insurance, Fintech, etc.)"],
                "must_core": ["Critical Skill 1", "Critical Skill 2"],
                "nice": ["Nice Skill 1"]
            }},
            "confidence_score": Integer (0-100),
            "search_queries": [
                "Query 1 (Semantic/Broad)",
                "Query 2 (Skill Focused)",
                "Query 3 (Domain Focused)"
            ]
        }}
        """
        
        try:
            resp = self.openai.get_chat_completion("Domain Expert Headhunter", prompt)
            if not resp: return {}
            
            clean = resp.replace("```json", "").replace("```", "").strip()
            # [DEBUG] Print raw response to trace parsing issues
            print(f"[JDAnalyzerV2] Raw LLM Response: {clean[:200]}...") 
            
            data = json.loads(clean)
            
            
            # [DEBUG] Print keys
            # print(f"[JDAnalyzerV2] Parsed Keys: {list(data.keys())}")
            
            # [SAFETY NET] Force remove subjective/banned terms
            data = self._apply_safety_filter(data)
            
            data["analysis_status"] = "success"
            return data
        except Exception as e:
            print(f"Error in JD extraction V2: {e}")
            return {"analysis_status": "failed", "reason": str(e)}

    def _apply_safety_filter(self, data: dict) -> dict:
        """
        Hard-coded safety net to remove known subjective patterns 
        that LLMs sometimes leak despite prompts.
        """
        # 1. Hidden Signals (Ban Adjectives/Abstract Concepts)
        banned_hidden = [
            "스타트업 마인드", "Startup Mindset", "열정", "Passion", 
            "커뮤니케이션", "Communication", "적극적", "Proactive",
            "책임감", "Ownership", "성장", "Growth", "문제 해결 능력",
            "유연한 사고", "Flexible", "긍정적", "협업", "Teamwork"
        ]
        
        if "hidden_signals" in data:
            cleaned = []
            for signal in data["hidden_signals"]:
                is_banned = False
                # Normalize signal: lower + remove spaces
                sig_norm = signal.lower().replace(" ", "")
                
                for ban in banned_hidden:
                    # Normalize ban: lower + remove spaces (fix for multi-word bans)
                    ban_norm = ban.lower().replace(" ", "")
                    
                    if ban_norm in sig_norm: 
                        is_banned = True
                        break
                if not is_banned:
                    cleaned.append(signal)
            data["hidden_signals"] = cleaned
            
        # 2. Negative Signals (Ban "No X Experience" inferred from Preferences)
        if "negative_signals" in data:
            cleaned_neg = []
            
            # [V3.2] Get extracted domains to cross-reference
            current_domains = data.get("domain", [])
            if isinstance(current_domains, str): current_domains = [current_domains]
            
            for signal in data["negative_signals"]:
                # Heuristic: Drop "No [Industry] Experience" signals as they are usually hallucinations from Preferences
                # Also drop generic "soft skill" negatives like "No teamwork experience"
                
                # [Rule 1] "Understanding" is not a disqualifier
                if "이해" in signal and ("없음" in signal or "없는" in signal):
                     continue
                     
                if "경험" in signal and ("없음" in signal or "없는" in signal) and "신입" not in signal:
                     continue
                if "협업" in signal or "Teamwork" in signal or "소통" in signal:
                     continue
                     
                # [Rule 2] Domain-Specific Negative Signals are BANNED
                is_domain_signal = False
                for d in current_domains:
                    if d in signal:
                        is_domain_signal = True
                        break
                if is_domain_signal:
                    continue
                     
                cleaned_neg.append(signal)
            data["negative_signals"] = cleaned_neg
            
        return data
