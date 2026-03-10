
import streamlit as st
import pandas as pd
import json
import time
import textwrap
from connectors.pinecone_api import PineconeClient
from connectors.openai_api import OpenAIClient
from connectors.notion_api import NotionClient
from feedback_loop import FeedbackLoop
from matcher import calculate_final_score
# from jd_parser.pipeline import JDPipeline # Moved to after patch
from classification_rules import ALLOWED_DOMAINS, get_role_cluster # Load domains & cluster logic
from jd_confidence import estimate_jd_confidence
from search_strategy import decide_search_strategy
from feedback_weight import calculate_feedback_weight
from jd_analyzer import JDAnalyzer
from jd_analyzer_v2 import JDAnalyzerV2 # [Phase 2.1]
import jd_analyzer_v3
import jd_analyzer_v5 # [PHASE 3.2]
import matcher_v3      # [PHASE 3.3]
from resume_scoring import calculate_rpl
from explanation_engine import generate_explanation
from search_pipeline_v3 import SearchPipelineV3
import altair as alt # Visualization
import hashlib # For history
import os


# --- [HOTFIX] Monkey Patch OpenAIClient for Cloud Deployment ---
# Force-apply the patch to ensure the method exists
import sys
if 'connectors.openai_api' in sys.modules:
    target_class = sys.modules['connectors.openai_api'].OpenAIClient
else:
    target_class = OpenAIClient

def straggler_patch(self, system_prompt, user_message=None):
    # ... (code same as before) ...
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {self.api_key}"
    }
    messages = []
    if user_message:
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
    else:
        messages.append({"role": "user", "content": system_prompt})

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "response_format": {"type": "json_object"},
        "max_tokens": 2000,
        "temperature": 0.3
    }
    
    data = json.dumps(payload).encode('utf-8')
    import urllib.request
    req = urllib.request.Request(url, data=data, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get("choices"):
                content = result["choices"][0]["message"]["content"]
                return json.loads(content)
            return None
    except Exception as e:
        print(f"[OpenAI JSON Error] {e}")
        return None

# Apply to both the imported symbol and the module source

# Apply to both the imported symbol and the module source
target_class.get_chat_completion_json = straggler_patch
OpenAIClient.get_chat_completion_json = straggler_patch
print("LOG: FORCE-PATCHED OpenAIClient.get_chat_completion_json")


# --- Cache JD Parser ---
# [Fix] Temporarily disabled cache to ensure patch updates apply immediately
# @st.cache_resource
def get_jd_pipeline():
    # Import here to ensure patch is applied first!
    from jd_parser.pipeline import JDPipeline
    
    # --- [SAFETY PATCH] Wrap Pipeline Parse ---
    # Because updating files on cloud is hard, we patch the method here to catch 'NoneType' errors
    if not hasattr(JDPipeline, "_is_patched_safe"):
        original_parse = JDPipeline.parse
        
        def safe_parse(self, jd_text: str) -> dict:
            try:
                res = original_parse(self, jd_text)
                return res if res else {}
            except Exception as e:
                print(f"⚠️ [Pipeline Recovery] Error ignored: {e}")
                import traceback
                traceback.print_exc()
                st.error(f"Pipeline Error: {e}")
                return {}
        
        JDPipeline.parse = safe_parse
        JDPipeline._is_patched_safe = True
        print("LOG: Applied Safety Patch to JDPipeline")

    # --- [DEEP FIX] Patch Extractor directly to prevent NoneType ---
    from jd_parser.extractor import JDExtractor
    
    pipeline = JDPipeline()
    
    # --- [CLOUD AUTH FIX] Inject API Key ---
    if not pipeline.client.api_key:
        try:
            if "OPENAI_API_KEY" in st.secrets:
                pipeline.client.api_key = st.secrets["OPENAI_API_KEY"]
                print("LOG: ✅ Successfully injected API Key from st.secrets")
        except Exception as e:
            print(f"⚠️ Warning: Failed to access st.secrets: {e}")

    # --- [CRITICAL FIX] Analyzer Closure for Monkey Patching ---
    analyzer_instance = JDAnalyzer(pipeline.client)
    analyzer_instance_v2 = JDAnalyzerV2(pipeline.client)
    analyzer_instance_v3 = jd_analyzer_v3.JDAnalyzerV3(pipeline.client) # [PHASE 3]

    def safe_extract_full(extractor_self, jd_text: str) -> dict:
        """
        [PHASE 3 Refactor]
        Switches between V1, V2, and V3 based on Session State.
        """
        try:
             import streamlit as st
             # Priority: analysis_engine radio button
             engine_choice = st.session_state.get("analysis_engine", "V5 (Standardized)")
             
             if engine_choice == "V5 (Standardized)": # [NEW]
                 print(f"LOG: [Step 1] Using JDAnalyzerV5 (Taxonomy Engine) for JD: {jd_text[:30]}...")
                 analyzer_instance_v5 = jd_analyzer_v5.JDAnalyzerV5(pipeline.client)
                 return analyzer_instance_v5.analyze(jd_text)
             elif engine_choice == "V3 (Experience)":
                 print(f"LOG: [Step 1] Using JDAnalyzerV3 (Experience Mode) for JD: {jd_text[:30]}...")
                 return analyzer_instance_v3.analyze(jd_text)
             elif engine_choice == "V2 (Expert)":
                 print(f"LOG: [Step 1] Using JDAnalyzerV2 (Expert Mode) for JD: {jd_text[:30]}...")
                 return analyzer_instance_v2.analyze(jd_text)
             else:
                 # Legacy fallback
                 if st.session_state.get("use_v2", False):
                     return analyzer_instance_v2.analyze(jd_text)
                 else:
                     return analyzer_instance.analyze(jd_text)

        except Exception as e:
             print(f"⚠️ [Analyzer Error] {e}")
             import traceback
             traceback.print_exc()
             return {}

    # Apply the Full Logic Patch (Once)
    # [Update] Bumped to v4 to force overwrite old sessions
    if not hasattr(JDExtractor, "_is_patched_deep_v4") or True: 
        JDExtractor.extract = safe_extract_full
        JDExtractor._is_patched_deep_v4 = True
        print("LOG: Applied Deep Logic Patch v4 to JDExtractor")

    return pipeline

jd_pipeline = get_jd_pipeline()

# --- [수정 1] Rule Book 로드 (기존 코드 상단에 추가) ---
def load_scoring_rules():
    # 폴더에 있는 .md 파일 이름을 정확히 적어주세요
    rule_path = "DB_rules.md" 
    try:
        with open(rule_path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "" # 파일이 없으면 빈 문자열

SCORING_RULES = load_scoring_rules()

# --- [HOTFIX] Version Control & Cache Clearing ---
# --- [HOTFIX] Version Control & Cache Clearing ---
APP_VERSION = "3.7.0 (Pattern-Aware Matcher)" # V5 & V3.3 Implementation
if "app_version" not in st.session_state or st.session_state.app_version != APP_VERSION:
    st.cache_resource.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.app_version = APP_VERSION
    print(f"LOG: Cache Cleared & Session Reset for Version {APP_VERSION}")

# --- Initialize Session State ---
if "pipeline_logs" not in st.session_state:
    st.session_state.pipeline_logs = []

if "search_strategy" not in st.session_state:
    # Default to V3.5 Recall Mode
    st.session_state.search_strategy = {"mode": "recall", "top_k": 500, "rerank": 100}

if "rpl_cutline" not in st.session_state:
    st.session_state.rpl_cutline = 45

# ---
# [Cache Management]
def clear_analysis_cache():
    if 'analysis_data_v3' in st.session_state:
        del st.session_state['analysis_data_v3']
    if 'analysis_data' in st.session_state: # Legacy cleanup
        del st.session_state['analysis_data']
    st.cache_resource.clear()

# Page config
st.set_page_config(page_title="AI Headhunter V3.6.1", page_icon="🕵️", layout="wide")

# --- CSS Styling (Clean White/Black + High Contrast Inputs) ---
st.markdown("""
<style>
    /* 1. Global Reset & Force Light Theme Colors */
    [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #FAFAFA !important;
        border-right: 1px solid #E5E5E5 !important;
    }
    
    /* 2. Text Visibility Fixes (Force Black Text) */
    h1, h2, h3, p, div, span, label, .stMarkdown, .stMarkdown p {
        color: #171717 !important;
    }
    
    /* 3. Input Fields (White BG, Black Text, Black Border) */
    .stTextArea textarea {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #000000 !important; /* Thicker border */
        border-radius: 6px;
    }
    .stTextArea textarea:focus {
        border-color: #E11D48 !important;
        box-shadow: none !important;
    }
    
    /* 4. Checkbox Styling (Force White BG/Black Border regardless of theme) */
    div[data-testid="stCheckbox"] label span[role="checkbox"] {
        background-color: #FFFFFF !important;
        border: 2px solid #000000 !important;
        border-radius: 4px;
        width: 1.2rem;
        height: 1.2rem;
    }
    /* Checked State: White BG, Black Checkmark */
    div[data-testid="stCheckbox"] label span[role="checkbox"][aria-checked="true"] {
        background-color: #FFFFFF !important;
        border-color: #000000 !important;
    }
    div[data-testid="stCheckbox"] label span[role="checkbox"][aria-checked="true"] svg {
        fill: #000000 !important; /* Black Checkmark */
        stroke: #000000 !important;
    }
    
    /* 5. Buttons (Home, Search - Force White/Black) */
    div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        border-radius: 6px;
        padding: 0.6rem 1.2rem;
        font-weight: 700;
        box-shadow: none !important;
    }
    div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #F3F4F6 !important;
        border-color: #000000 !important;
        color: #000000 !important;
    }
    div.stButton > button:active {
        background-color: #E5E7EB !important;
    }
    div.stButton > button p {
        color: #000000 !important; /* Force text black inside buttons */
    }

    /* 6. Job Item List Style */
    .job-item {
        border-bottom: 1px solid #E5E5E5;
        padding: 32px 0;
        transition: all 0.2s;
    }
    .job-item:hover {
        background-color: #F8FAFC;
        cursor: pointer;
    }
    .job-title {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 8px;
        color: #171717 !important;
    }
    .job-meta {
        font-size: 1rem;
        color: #64748B !important; /* Slate-500 */
    }
    .score-tag {
        font-size: 0.85rem;
        font-weight: 600;
        color: #E11D48 !important; /* Red Text */
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 8px;
    }
    
    /* 7. AI Reason Text */
    .ai-text {
        font-size: 0.95rem;
        line-height: 1.6;
        color: #334155 !important;
        margin-top: 16px;
        background-color: #f0fdf4;
        padding: 16px;
        border-left: 3px solid #16a34a;
    }
    
    /* 8. Text Input (Feedback) */
    .stTextInput input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        border-radius: 6px;
    }
    
    /* 9. Expander Styling (Super Aggressive) */
    div[data-testid="stExpander"] {
        background-color: #FFFFFF !important;
        border: 2px solid #000000 !important;
        border-radius: 6px;
        color: #000000 !important;
    }
    div[data-testid="stExpander"] details {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    div[data-testid="stExpander"] summary {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
    }
    div[data-testid="stExpander"] * {
        color: #000000 !important;
    }
    
    /* 10. Checkbox Styling (Force Black Label) */
    div[data-testid="stCheckbox"] label p {
        color: #000000 !important;
    }
    div[data-testid="stCheckbox"] label {
        color: #000000 !important;
    }
    div[data-testid="stCheckbox"] {
        background-color: #FFFFFF !important;
    }

    /* 11. Toast */
    div[data-testid="stToast"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
    }
    
    /* Hide Streamlit Chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# [UI] Sidebar (Global)
with st.sidebar:
    st.header("⚙️ 검색 설정 (Settings)")
    
    # Define Default Weights
    default_weights = {"vector": 0.5, "keyword": 0.3, "ontology": 0.2}

    # [NEW] Cache Clear Button
    if st.button("🧹 FORCE RESET (DEV)", type="primary", help="⚠️ 완전 초기화: 모든 캐시와 세션 데이터를 삭제하고 새로고침합니다."):
        clear_analysis_cache()
        st.cache_data.clear()
        st.cache_resource.clear()
        st.session_state.clear()
        st.rerun()

    # Search Mode Selection
    mode = st.radio(
        "검색 모드",
        ["정밀 (Precision)", "확장 (Recall)"],
        index=0 if st.session_state.get('current_strategy_mode', 'precision') == 'precision' else 1,
        help="""
        **정밀 (Precision)**: JD에 정확히 일치하는 후보자를 찾습니다. JD가 명확할 때 적합합니다.
        **확장 (Recall)**: JD와 유사한 키워드를 가진 후보자까지 넓게 찾습니다. JD가 모호하거나 다양한 가능성을 탐색할 때 유용합니다.
        """
    )
    
    # Store Strategy in Session
    if mode == "정밀 (Precision)":
        st.session_state.strategy = {"mode": "precision", "top_k": 30, "rerank": 10}
    else:
        st.session_state.strategy = {"mode": "recall", "top_k": 60, "rerank": 15}

    # [SIDEBAR] RPL Slider (Phase 3)
    st.sidebar.markdown("---")
    st.sidebar.subheader("📄 서류 통과 기준 (RPL)")
    rpl_cutline = st.sidebar.slider(
        "최소 합격 점수",
        min_value=30,
        max_value=90,
        value=st.session_state.get("rpl_cutline", 55),
        step=5,
        key="rpl_slider_key",
        help="후보가 너무 적으면 낮추고, 많으면 높이세요."
    )
    st.session_state["rpl_cutline"] = rpl_cutline

    # [NEW] JD Analysis Engine Selection (Phase 3)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 JD 분석 엔진")
    
    # [Fix 3.3] Detect Engine Change to force re-analysis
    prev_engine = st.session_state.get("analysis_engine")
    
    analysis_engine = st.sidebar.radio(
        "분석 엔진 선택",
        ["V2 (Expert)", "V3 (Experience)", "V5 (Standardized)"],
        index=2,  # Default to V5
        help="""
        **V2 (Expert)**: JD에서 직접적인 키워드를 추출합니다.
        **V3 (Experience)**: 이력서에서 검증 가능한 경험을 추론합니다.
        **V5 (Standardized)**: [NEW] 우리가 정의한 표준 Taxonomy(Pattern ID)로 JD를 분석합니다.
        """
    )
    
    if prev_engine and prev_engine != analysis_engine:
        # Engine changed! Reset to forced analysis if we already have JD
        if st.session_state.get("jd_text"):
            st.session_state.step = "analyze"
            st.toast(f"🔄 엔진 변경 ({analysis_engine}): 재분석을 위해 초기화되었습니다.")

    st.session_state["analysis_engine"] = analysis_engine

    # [NEW] Debug Expander in Sidebar
    with st.expander("디버그 정보", expanded=False):
        st.write("현재 세션 상태:")
        st.write(st.session_state.to_dict()) # Fix for non-serializable objects maybe?

# --- Helper: Save Feedback ---
import hashlib
import os

def get_jd_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest() if text else "global"

def save_feedback(candidate_name, reason, feedback_type="negative", jd_text="", candidate_id=None):
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "candidate": candidate_name,
        "candidate_id": candidate_id,
        "type": feedback_type,
        "reason": reason,
        "context_id": get_jd_hash(jd_text) # Save which JD this was for
    }
    
    # 1. Try Saving to Notion (If Configured)
    try:
        # Check if DB ID exists in secrets
        db_id = secrets.get("NOTION_FEEDBACK_DB_ID")
        if db_id and 'notion' in globals():
            props = {
                "Candidate": {"title": [{"text": {"content": candidate_name}}]},
                "Type": {"select": {"name": feedback_type}},
                "Reason": {"rich_text": [{"text": {"content": reason}}]},
                "Context Hash": {"rich_text": [{"text": {"content": entry["context_id"]}}]},
                "Timestamp": {"rich_text": [{"text": {"content": entry["timestamp"]}}]}
            }
            if candidate_id:
                props["Candidate ID"] = {"rich_text": [{"text": {"content": str(candidate_id)}}]}
                
            notion.create_page(db_id, props)
            print(f"LOG: Feedback saved to Notion DB {db_id}")
    except Exception as e:
        print(f"⚠️ Failed to save to Notion: {e}")

    # 2. Local Fallback (Always save to file just in case)
    file_path = "feedback_log.json"
    
    existing_data = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except: pass
    
    existing_data.append(entry)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2, ensure_ascii=False)

# --- Helper: Phase 3 History & Estimations ---
def save_jd_rpl_history(jd_text, jd_analysis, results, cutline):
    # Save statistics for future recommendation tuning
    jd_hash = get_jd_hash(jd_text)
    history_file = "jd_rpl_history.json"
    
    # Calculate Stats
    scores = [r.get('rpl_score', 0) for r in results]
    if not scores: return
    
    avg_score = sum(scores) / len(scores)
    pass_rate = len([s for s in scores if s >= cutline]) / len(scores) * 100
    
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "jd_hash": jd_hash,
        "difficulty_score": estimate_jd_difficulty(jd_analysis), # Calc on fly
        "avg_rpl": avg_score,
        "pass_rate_at_cutline": pass_rate,
        "cutline_used": cutline,
        "candidate_count": len(results)
    }
    
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except: pass
        
    history.append(entry)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def estimate_jd_difficulty(jd_analysis):
    # 0 (Easy) to 10 (Hard)
    # Factors: Number of Must Skills, Specificity, Niche Role
    score = 5 # Base
    
    if not jd_analysis: return 5
    
    # Factor 1: Must Skills Count
    must_count = len(jd_analysis.get('must_skills', []) or jd_analysis.get('must', []))
    if must_count > 5: score += 2
    elif must_count < 3: score -= 1
    
    # Factor 2: Role Specificity (Heuristic)
    role = jd_analysis.get('canonical_role', '' if not jd_analysis else jd_analysis.get('role', ''))
    if "Head" in role or "Lead" in role or "Principal" in role:
        score += 2
        
    return min(max(score, 1), 10)

def recommend_rpl_cutline(jd_analysis, result_scores):
    # Dynamic Cutline Recommendation
    # Goal: Ensure at least 3-5 candidates pass, but keep quality high.
    
    if not result_scores: return 55
    
    # Sort scores descending
    sorted_scores = sorted(result_scores, reverse=True)
    
    # Target: Top 5th candidate's score
    target_idx = min(4, len(sorted_scores) - 1)
    target_score = sorted_scores[target_idx]
    
    # Baseline constraints
    difficulty = estimate_jd_difficulty(jd_analysis)
    
    # If difficult JD, lower the bar slightly
    base_cut = 60 - (difficulty * 2) # e.g. Diff=5 -> 50, Diff=8 -> 44
    
    # Hybrid: Weight actual distribution (70%) + Baseline (30%)
    recommended = (target_score * 0.7) + (base_cut * 0.3)
    
    # Round to nearest 5
    return int(round(recommended / 5) * 5)


# --- Helper: Seniority Extraction ---
SENIORITY_MAP = {
    "junior":    ["junior", "entry", "entry-level", "0-2", "신입", "주니어"],
    "middle":    ["mid", "middle", "intermediate", "3-5", "미들"],
    "senior":    ["senior", "sr.", "lead", "principal", "5+", "시니어", "리드"],
    "executive": ["head", "director", "vp", "c-level", "executive", "임원"]
}

def extract_seniority(parsed_jd: dict, jd_text: str) -> str:
    # Step 1: Trust Pipeline if explicit
    if parsed_jd.get("seniority"):
        return parsed_jd["seniority"]
    
    # Step 2: Keyword Matching
    jd_lower = jd_text.lower()
    scores = {level: 0 for level in SENIORITY_MAP}
    for level, keywords in SENIORITY_MAP.items():
        for kw in keywords:
            if kw in jd_lower:
                scores[level] += 1
    
    # Select best match
    best = max(scores, key=scores.get)
    return best.capitalize() if scores[best] > 0 else "Middle"

    return best.capitalize() if scores[best] > 0 else "Middle"

# --- [Phase 2.3] Role Aliasing (Bridge Logic) ---
ROLE_ALIASES = {
    "Product Owner": ["Product Manager", "PM", "Service Planner", "기획자", "서비스 기획"],
    "Product Manager": ["Product Owner", "PO", "PM", "Service Planner", "기획자"],
    "Project Manager": ["PM", "Program Manager", "사업 관리"],
    "Backend Engineer": ["Server Developer", "Back-end", "Java Developer", "Python Developer", "Node.js"],
    "Frontend Engineer": ["Web Developer", "Front-end", "React", "Vue", "UI Developer"],
    "Data Scientist": ["AI Engineer", "ML Engineer", "Data Analyst", "데이터 분석가"],
    "FP&A 매니저": ["재무", "경영관리", "사업기획", "전략기획", "관리회계", "Corporate Finance", "Business Planning", "Finance Analyst", "Financial Analyst", "예산 관리"],
    "Strategic Finance": ["전략 재무", "사업 전략", "Corporate Strategy", "Finance BP"],
    "Finance Manager": ["재무 팀장", "회계", "Accounting", "Finance Lead"]
}

def get_role_aliases(role_name):
    """Returns a list of aliases for a given role (case-insensitive lookup)."""
    if not role_name: return []
    
    # Direct lookup
    if role_name in ROLE_ALIASES:
        return ROLE_ALIASES[role_name]
    
    # Partial lookup
    for key, aliases in ROLE_ALIASES.items():
        if key.lower() in role_name.lower():
            return aliases
            
    return []
def get_notion_url(notion_client, page_id: str) -> str:
    try:
        page = notion_client.get_page(page_id)
        return page.get("url", f"https://www.notion.so/{page_id.replace('-', '')}")
    except:
        return f"https://www.notion.so/{page_id.replace('-', '')}"

# --- Helper: RAG Cache ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_rag_recommendation(page_id: str, jd_summary: str, candidate_name: str, context_text: str) -> str:
    prompt = f"""
    Role: Senior HR Partner.
    Task: Explain why {candidate_name} matches the JD.
    JD Summary: {jd_summary}
    Resume: {context_text}
    Output: 3 bullet points (Korean). Convincing tone.
    """
    try:
        # Use global openai client (cached functions effectively snapshot global state/args)
        return openai.get_chat_completion("HR Expert", prompt)
    except Exception as e:
        return f"AI analysis unavailable: {e}"

# --- Logic Setup ---
try:
    if os.path.exists("secrets.json"):
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
    else:
        # Fallback to Streamlit Cloud Secrets
        secrets = st.secrets

    pc_host = secrets.get("PINECONE_HOST", "")
    if not pc_host.startswith("https://"): pc_host = f"https://{pc_host}"
    
    pinecone = PineconeClient(secrets["PINECONE_API_KEY"], pc_host)
    openai = OpenAIClient(secrets["OPENAI_API_KEY"])
    notion = NotionClient(secrets["NOTION_API_KEY"])
except Exception as e:
    st.error(f"Secrets not found or Error initializing: {e}")
    st.stop()

# --- Session State Initialization ---
if "step" not in st.session_state:
    st.session_state.step = "input" # input -> review -> results
if "analysis_data_v3" not in st.session_state:
    st.session_state.analysis_data_v3 = {"must": [], "nice": [], "domain": []}
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "jd_text" not in st.session_state:
    st.session_state.jd_text = ""

# --- Two Column Layout ---
col_sidebar, col_main = st.columns([1, 3])

with col_sidebar:
    st.caption(f"🚀 Version: **{APP_VERSION}**")
    st.markdown("---")
    
    st.session_state.analysis_engine = st.radio(
        "분석 엔진 선택 (Engine Selection)",
        ["V3 (Experience)", "V2 (Expert)"],
        index=0 if st.session_state.get("analysis_engine", "V3") == "V3 (Experience)" else 1,
        help="V3는 검증 가능한 경험 중심, V2는 포괄적 역량 중심 분석입니다."
    )
    st.markdown("---")
    # 3. Home Button (Reset)
    if st.button("🏠 New Search", key="btn_home", use_container_width=True):
        st.session_state.step = "input"
        st.session_state.analysis_data = {"must": [], "nice": [], "domain": []}
        st.session_state.search_results = []
        st.session_state.jd_text = ""
        st.rerun()

    # --- JD Analysis Status ---
    if st.session_state.get("analysis_data_v3"):
        conf = st.session_state.analysis_data_v3.get("confidence_score", 0)
        is_ambiguous = st.session_state.analysis_data_v3.get("ambiguity", False)
        
        st.markdown("### 📊 AI Confidence")
        if is_ambiguous:
            st.warning(f"⚠️ Ambiguous ({conf}/100)")
            st.caption("Conflicting signals found.")
        elif conf >= 80:
            st.success(f"✅ High ({conf}/100)")
        elif conf >= 50:
            st.info(f"ℹ️ Medium ({conf}/100)")
        else:
            st.error(f"❌ Low ({conf}/100)")

    st.write("")
    st.markdown("---")
    st.subheader("Experimental Features")
    # [Phase 2.1] V2 Toggle
    st.checkbox("Use Deep Domain Analysis (V2) 🧠", value=False, key="use_v2", help="Enables 'Domain Expert' mode with deeper inference and negative signal detection.")
    
    # [Phase 2.9] Reset Cache Button
    # [UI] Custom White Style for Cache Button
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
        background-color: white;
        border: 1px solid #e5e7eb;
        color: #374151;
    }
    section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
        border-color: #d1d5db;
        color: #111827;
        background-color: #f9fafb;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if st.button("🗑️ Clear Analysis Cache", help="Reset all analysis data and cached embeddings."):
        st.session_state.analysis_data_v3 = {}
        st.session_state.search_results = []
        st.session_state.pipeline_logs = []
        st.cache_data.clear()
        st.cache_resource.clear()
        st.toast("Cache Cleared!", icon="🗑️")
        st.rerun()

    st.markdown("---")
    st.subheader("Industry / Sector")
    
    # Use imported ALLOWED_DOMAINS
    domains = ALLOWED_DOMAINS
    selected_domains = []
    
    st.write("Target Industries:")
    for d in domains:
        if st.checkbox(d, key=f"chk_{d}"):
            selected_domains.append(d)
    
    st.caption("No selection = Ignore Domain Filter")
    
    st.write("")
    st.markdown("---")
    st.subheader("Weights Configuration")


# --- Main Content ---
with col_main:
    st.title("Antigravity")
    st.markdown("### 🌌 AI 기반 심층 인재 검색")
    st.write("")
    
    # ==========================
    # STEP 1: JD Input & Analyze
    # ==========================
    if st.session_state.step == "input":
        with st.form("analyze_form"):
            st.markdown("#### 1️⃣ 채용 공고(JD) 입력")
            jd_input = st.text_area("Keywords", 
                                  value=st.session_state.jd_text,
                                  placeholder="채용 공고(JD) 내용을 여기에 붙여넣으세요...", 
                                  label_visibility="collapsed", 
                                  height=200)
            
            submitted_analyze = st.form_submit_button("요건 분석 시작 🚀", use_container_width=True)
            
            if submitted_analyze and jd_input:
                st.session_state.jd_text = jd_input # Save input
                
                with st.spinner("🤖 JD 분석 중입니다 (AI 역할 추론 / 숨겨진 의도 파악)..."):
                    try:
                        # [PHASE 3 Refactor] Use explicit engine choice to avoid monkey-patch instability
                        engine_choice = st.session_state.get("analysis_engine", "V3 (Experience)")
                        
                        if "V3" in engine_choice:
                            analyzer = jd_analyzer_v3.JDAnalyzerV3(openai)
                            raw = analyzer.analyze(jd_input)
                            # Standardize for the legacy UI flow
                            parsed_jd = {
                                "must_have": raw.get("core_signals", []),
                                "nice_to_have": raw.get("supporting_signals", []),
                                "domains": raw.get("context_signals", []),
                                "primary_role": raw.get("canonical_role", "Engineer"),
                                "raw_extracted": raw,
                                "years_range": raw.get("years_range", {"min": 0, "max": None}),
                                "confidence_score": raw.get("confidence_score", 100),
                                "ambiguity": raw.get("ambiguity", False),
                                "search_contract": raw.get("search_contract", {})
                            }
                        else:
                            # Fallback to JDPipeline (V1/V2)
                            parsed_jd = jd_pipeline.parse(jd_input)
                            raw = parsed_jd.get("raw_extracted", {})

                         # Map parsed results to session state
                        d_list = parsed_jd.get("domains", []) or parsed_jd.get("domain_candidates", []) or [raw.get("domain", "General")]
                        if isinstance(d_list, str): d_list = [d_list]
                        
                        analysis_data_current = {
                            "must": parsed_jd.get("must_have", []) or raw.get("must_skills", []), 
                            "nice": parsed_jd.get("nice_to_have", []) or raw.get("nice_skills", []),
                            "domain": d_list,
                            "role": parsed_jd.get("primary_role", raw.get("primary_role", "Engineer")),
                            "inferred_role": raw.get("inferred_role", ""), 
                            "hidden_signals": raw.get("hidden_signals", []), 
                            "negative_signals": raw.get("negative_signals", []), 
                            "wrong_roles": raw.get("wrong_roles", []), 
                            "seniority": extract_seniority(parsed_jd, jd_input),
                            "years_range": parsed_jd.get("years_range", {"min": 0, "max": None}),
                            "confidence_score": parsed_jd.get("confidence_score", 0),
                            "ambiguity": parsed_jd.get("ambiguity", False),
                            "search_contract": parsed_jd.get("search_contract", {})
                        }
                        st.session_state.analysis_data_v3 = analysis_data_current
                        st.session_state.analysis_data = analysis_data_current # [PHASE 3] Back-sync for Reranker Compatibility
                        
                        st.session_state.step = "review" # Move to next step
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Analysis Error: {e}")
                        st.session_state.analysis_data_v3 = {"must": [], "nice": [], "domain": []}
                        if st.button("Continue Manually"):
                             st.session_state.step = "review"
                             st.rerun()

    # ==========================
    # STEP 2: Review & Edit Keys
    # ==========================
    elif st.session_state.step == "review":
        engine_name = st.session_state.get("analysis_engine", "V3 (Experience)")
        st.markdown(f"#### 2️⃣ 키워드 검토 및 수정 (AI 분석) - `{engine_name}`")
        
        # [DEBUG] Data Inspection
        with st.expander("🛠️ Debug Data (Developer Only)"):
            st.json(st.session_state.analysis_data_v3)
            st.caption(f"Active Engine: {engine_name}")

        # [NEW] Headhunter Insights Display
        inferred = st.session_state.analysis_data_v3.get('inferred_role', '')
        if inferred:
            # [V2.9.5] Display Years Range
            years_range = st.session_state.analysis_data_v3.get('years_range', {})
            min_y = years_range.get("min", 0) if isinstance(years_range, dict) else 0
            max_y = years_range.get("max") if isinstance(years_range, dict) else None
            range_str = f"{min_y}년 ~ {max_y}년" if max_y else f"최소 {min_y}년 이상"
            seniority_str = st.session_state.analysis_data_v3.get('seniority', 'N/A')
            
            st.info(f"🧠 **AI 추론 역할**: {inferred} | 📅 **경력 요건**: {range_str} ({seniority_str})")
        
        with st.expander("🕵️‍♂️ 헤드헌터 심층 분석 (Hidden & Negative Signals)", expanded=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**🔍 숨겨진 의도 (Hidden Signals)**")
                hidden = st.session_state.analysis_data_v3.get('hidden_signals', [])
                if hidden:
                    for s in hidden:
                        st.markdown(f"- {s}")
                else:
                    st.caption("감지된 특이사항 없음")
            
            with col_b:
                st.markdown("**🚫 제외 기준 (Negative Signals)**")
                neg = st.session_state.analysis_data_v3.get('negative_signals', [])
                if neg:
                    for s in neg:
                        st.markdown(f"- {s}")
                else:
                    st.caption("제외 기준 없음")

        # [Fix] Force Clear Negative Signals if Domain Unselected (Stale Data Fix)
        if not selected_domains and st.session_state.analysis_data_v3.get("negative_signals"):
             st.session_state.analysis_data_v3["negative_signals"] = []
             st.rerun()

        st.caption("AI가 추출한 키워드입니다. 검색 정확도를 높이려면 수정하세요.")
        
        # Show Original JD Reference (Collapsible)
        with st.expander("📄 원본 JD 보기 (View Original)", expanded=False):
            st.text(st.session_state.jd_text)
        
        # Color Legend Badge
        st.markdown("""
         <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
            <span style="background-color: #E3F2FD; border: 1px solid #90CAF9; color: #1565C0; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500;">🔵 필수 (x3)</span>
            <span style="background-color: #FFF9C4; border: 1px solid #FFF59D; color: #FBC02D; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500;">🟡 우대 (x1.5)</span>
            <span style="background-color: #E8F5E9; border: 1px solid #A5D6A7; color: #2E7D32; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500;">🟢 도메인 (x1)</span>
         </div>
         """, unsafe_allow_html=True)
         
        with st.form("search_execution_form"):
            c1, c2, c3 = st.columns(3)
            with c1: 
                st.markdown("##### 🔵 필수 요건")
                must_txt = st.text_area("must", value=", ".join(st.session_state.analysis_data_v3["must"]), height=150, label_visibility="collapsed")
            with c2: 
                st.markdown("##### 🟡 우대 사항")
                nice_txt = st.text_area("nice", value=", ".join(st.session_state.analysis_data_v3["nice"]), height=150, label_visibility="collapsed")
            with c3: 
                st.markdown("##### 🟩 도메인")
                # [Fix] Handle legacy string data in session_state gracefully
                d_val = st.session_state.analysis_data_v3["domain"]
                if isinstance(d_val, str): d_val = [d_val]
                domain_txt = st.text_area("domain", value=", ".join(d_val), height=150, label_visibility="collapsed")
            
            st.write("")
            st.session_state.use_recall_mode_toggle = st.toggle("🔍 넓게 검색하기 (Recall Mode)", value=False, help="체크하면 더 많은 후보를 가져오지만, 정확도는 떨어질 수 있습니다.", key="recall_toggle_widget")
            submitted_search = st.form_submit_button("인재 검색 시작 🔍", use_container_width=True)
            
            if submitted_search:
                # Update Analysis Data with User Edits
                st.session_state.analysis_data_v3["must"] = [x.strip() for x in must_txt.split(",") if x.strip()]
                st.session_state.analysis_data_v3["nice"] = [x.strip() for x in nice_txt.split(",") if x.strip()]
                st.session_state.analysis_data_v3["domain"] = [x.strip() for x in domain_txt.split(",") if x.strip()]
                
                with st.spinner("Searching Vector Database..."):
                    # 1. Load Feedback History (JD-specific)
                    current_jd_hash = get_jd_hash(st.session_state.jd_text)
                    rejected_candidates = set()
                    liked_candidate_ids = set()
                    feedback_adjustments = {}
                    
                    if os.path.exists("feedback_log.json"):
                        try:
                            with open("feedback_log.json", "r", encoding="utf-8") as f:
                                fb_data = json.load(f)
                                for item in fb_data:
                                    # Filter by Context (Same JD) for simple filtering
                                    if item.get("context_id") == current_jd_hash:
                                        if item.get("type") == "negative":
                                            rejected_candidates.add(item.get("candidate"))
                                        elif item.get("type") == "positive" and item.get("candidate_id"):
                                            liked_candidate_ids.add(item.get("candidate_id"))
                                    
                                    # [PHASE 3] Global Feedback Decay (Apply to everything)
                                    # [Improvement 2] Use ID instead of Name for safety
                                    cand_id_target = item.get("candidate_id") or item.get("candidate") # Fallback to name if ID missing
                                    if cand_id_target:
                                        base_w = 1.0 if item.get("type") == "positive" else -1.0
                                        decayed_w = calculate_feedback_weight(base_w, item.get("timestamp"))
                                        feedback_adjustments[cand_id_target] = feedback_adjustments.get(cand_id_target, 0) + decayed_w
                        except: pass
                    
                    # [PHASE 2.5] EMERGENCY PATCH: Always use Role Aliases for Product Roles
                    # The user identified that "PO" and "PM" are often mismatched.
                    # We must expand aliases even in Precision Mode for these key roles.
                    inferred_role = st.session_state.analysis_data_v3.get('inferred_role', '')
                    aliases = []
                    
                    # Check if role is "Product" related (PO, PM, Planner)
                    # "product" in "product owner" -> True
                    if "product" in inferred_role.lower() or "pm" in inferred_role.lower() or "기획" in inferred_role:
                        aliases = get_role_aliases(inferred_role)
                        print(f"DEBUG: Emergency Alias Expansion for {inferred_role}: {aliases}")

                    # [PHASE 2.2] Determine Search Strategy (Confidence-Driven)
                    conf_score_val = st.session_state.analysis_data_v3.get("confidence_score", 0)
                    
                    # Store for UI display
                    st.session_state.analysis_data_v3["confidence_score_val"] = int(conf_score_val)
                    
                    # [Fix 1] Centralized Strategy Logic
                    # If high confidence but specific role (like PO), we might get 0 results due to resume mismatch.
                    # We enables aliases for these roles ALWAYS.
                    
                    # Default: Precision if >= 80
                    # [V3.0] Wide Funnel: Top-K 300 for ALL strategies
                    new_strategy = {"mode": "precision", "top_k": 300, "rerank": 50}
                    
                    
                    # [V5.0] Precision Tuning: Default to Precision Mode
                    # V4.2 fixed connectivity, so we can be stricter.
                    
                    # Strategy Toggle UI
                    use_recall_mode = st.toggle("🔍 넓게 검색하기 (Recall Mode)", value=False, help="체크하면 더 많은 후보를 가져오지만, 정확도는 떨어질 수 있습니다.")

                    if use_recall_mode or conf_score_val < 80:
                        new_strategy = {"mode": "recall", "top_k": 600, "rerank": 150}
                        st.session_state.search_strategy = new_strategy
                        if not use_recall_mode:
                            st.toast(f"🔎 신뢰도 낮음({conf_score_val}) → Recall Mode 자동 적용")
                        else:
                            st.toast(f"🔎 Recall Mode Activated (User Selection)")
                    else:
                        # Precision Mode (Default)
                        new_strategy = {"mode": "precision", "top_k": 300, "rerank": 50}
                        st.session_state.search_strategy = new_strategy
                        st.toast(f"🎯 Precision Mode (Default)")

                    # [V5.0] Default Cutline: 55 (Restored from 45)
                    if "rpl_cutline" not in st.session_state:
                         st.session_state.rpl_cutline = 55
                    
                    st.session_state.analysis_data_v3["search_strategy"] = new_strategy
                    
                    # [Fix 1.1] Auto-Fallback Logic Consistency
                    if st.session_state.get("force_recall", False):
                        new_strategy = {"mode": "recall", "top_k": 600, "rerank": 150}
                        st.session_state.search_strategy = new_strategy
                        st.toast(f"🔄 Auto-Recall Mode Activated (Previous: {conf_score_val})")
                    
                    st.session_state.analysis_data_v3["search_strategy"] = new_strategy
                    
                    # 2. Embed & Query (Vector Search - The "Broad Net")
                    role_str = st.session_state.analysis_data_v3.get("role", "Engineer")
                    seniority_str = st.session_state.analysis_data_v3.get("seniority", "Middle")
                    must_str = ", ".join(st.session_state.analysis_data_v3["must"])
                    nice_str = ", ".join(st.session_state.analysis_data_v3["nice"])
                    domain_str = ", ".join(st.session_state.analysis_data_v3["domain"])

                    # Natural Language Query for Embedding Model
                    # [PHASE 2.2] Prioritize Canonical Role & Hidden Signals
                    # [PHASE 2.3] Inject Role Aliases if Recall Mode
                    
                    # [Fix 2] ALIAS ALWAYS ON for key roles
                    # Regardless of strategy, if it's PM/PO/Planner, we extend the query.
                    aliases = []
                    inferred = st.session_state.analysis_data_v3.get('inferred_role', '')
                    
                    # Check key roles or if strategy is recall
                    is_product_role = any(x in inferred.lower() for x in ["product", "pm", "po", "기획"])
                    if is_product_role or st.session_state.search_strategy['mode'] == 'recall':
                         aliases = get_role_aliases(inferred)
                         if is_product_role:
                             print(f"DEBUG: Forced Alias Expansion for {inferred}: {aliases}")
                    
                    alias_str = f"(Also considering: {', '.join(aliases)})" if aliases else ""

                    # [V2.9.5] Junior Query Expansion
                    years_range = st.session_state.analysis_data_v3.get('years_range', {})
                    junior_expansion = ""
                    if isinstance(years_range, dict):
                        max_y = years_range.get("max")
                        # If max years is low (<= 3), explicitly expand query to catch signals often matching juniors
                        if max_y is not None and max_y <= 3:
                            junior_expansion = "Potential, Growth, Learning, Entry Level, Junior, Assistant, Intern, 신입, 주니어, 성장 가능성"

                    
                    # [V2.9.6] Conditional Domain Filtering (User Preference)
                    # ONLY include domain in retrieval query if "Deep Domain Analysis" is checked.
                    # Otherwise, use domain only for ranking (Stage 3).
                    domain_context = ""
                    use_deep_domain = st.session_state.get("use_v2", False)
                    
                    if selected_domains and use_deep_domain:
                        domain_context = f"Domain experience: {', '.join(st.session_state.analysis_data_v3.get('domain', []))}"
                    else:
                        print(f"DEBUG: Domain Context Excluded from Retrieval (Deep Domain={use_deep_domain})")

                    # [V3.1] Task-Centric Query for Finance/FP&A
                    # Problems: "FP&A" title is rare. Querying by title fails.
                    # Solution: Query by TASKS (Budgeting, Forecasting, Modeling).
                    is_finance_role = any(x in inferred.lower() for x in ["finance", "fp&a", "전략", "재무", "회계", "ir"])
                    
                    if is_finance_role:
                        print(f"DEBUG: Finance Role Detected ({inferred}) -> Switching to Task-Centric Query")
                        # Construct Task List from Must/Nice or Defaults
                        # If 'Must' contains generic terms, we add specific Finance tasks
                        finance_tasks = ["Budgeting", "Financial Modeling", "Forecasting", "Variance Analysis", "ERP", "Closing"]
                        task_str = ", ".join(st.session_state.analysis_data_v3["must"] + finance_tasks)
                        
                        weighted_query = f"""
                        Role: {st.session_state.analysis_data_v3.get('inferred_role', '')} {alias_str}
                        Key Tasks & Responsibilities: {task_str}
                        Technical Skills: {must_str}
                        Seniority: {seniority_str} Level {junior_expansion}
                        {domain_context}
                        Nice to have: {nice_str}
                        """
                    else:
                        # Standard Role-Centric Query
                        weighted_query = f"""
                        Role: {st.session_state.analysis_data_v3.get('inferred_role', '')} {role_str} {alias_str}
                        Must have skills: {must_str}
                        Hidden context: {', '.join(st.session_state.analysis_data_v3.get('hidden_signals', []))}
                        Seniority: {seniority_str} Level {junior_expansion}
                        {domain_context}
                        Nice to have: {nice_str}
                        """
                    
                    # 3. Vector Embedding (Query) - Use User-Edited Signals
                    # [Fix] Use 'must' and 'domain' instead of raw AI 'core_signals' to ensure user edits are applied.
                    role_vec = st.session_state.analysis_data_v3.get("role", "Unknown")
                    must_vec = st.session_state.analysis_data_v3.get("must", [])
                    domain_vec = st.session_state.analysis_data_v3.get("domain", [])
                    
                    # Text for embedding
                    query_text = f"Role: {role_vec}, Skills: {', '.join(must_vec)}, Context: {', '.join(domain_vec)}"
                    
                    query_vector = openai.embed_content(query_text)
                    
                    # 4. Run Pipeline V3
                    pipeline = SearchPipelineV3(pinecone)
                    
                    # Use Strategy Top-K
                    top_k_val = st.session_state.search_strategy.get("top_k", 300)
                    
                    # Execute (Unpack Tuple)
                    raw_results, trace_log = pipeline.run(
                        jd_analysis=st.session_state.analysis_data_v3,
                        query_vector=query_vector,
                        top_k=top_k_val
                    )
                    
                    # Store Trace
                    st.session_state.latest_trace_log = trace_log

                    # 5. Save History & Recommend Cutline
                    # Current user cutline
                    current_cut = st.session_state.get("rpl_cutline", 45)
                    
                    save_jd_rpl_history(
                        jd_text=st.session_state.jd_text,
                        jd_analysis=st.session_state.analysis_data_v3,
                        results=raw_results,
                        cutline=current_cut
                    )
                    
                    # Recommendation Logic (Optimized for Low Sample)
                    rec_cut = 55
                    if len(raw_results) < 20:
                        rec_cut = 40 # Lower if few candidates
                    else:
                        rec_cut = recommend_rpl_cutline(
                            st.session_state.analysis_data_v3, 
                            [r['rpl_score'] for r in raw_results]
                        )
                    st.session_state.recommended_cutline = rec_cut
                    
                    # 6. Store Results
                    st.session_state.search_results = raw_results
                    st.session_state.formatted_matches = raw_results # For compatibility
                    
                    # Log
                    st.session_state.pipeline_logs.append(f"SEARCH V3: Retrieved {len(raw_results)} candidates.")
                    st.session_state.pipeline_logs.append(f"TRACE: {trace_log}")
                    st.session_state.pipeline_logs.append(f"RPL Cutline: User={current_cut}, Recommended={rec_cut}")

                    st.session_state.step = "results"
                    st.rerun()
                    
                   # ==========================
    # STEP 2: JD Analysis (AI)
    # ==========================
    elif st.session_state.step == "analyze":
        with st.spinner("🤖 AI가 JD를 분석하여 '서류 통과 기준'을 수립 중입니다..."):
            try:
                # [PHASE 3] Engine Selection (V2 vs V3)
                engine = st.session_state.get("analysis_engine", "V3 (Experience)")
                if "V3" in engine:
                    analyzer = jd_analyzer_v3.JDAnalyzerV3(openai)
                    print("LOG: Using JD Analysis Engine V3 (Experience)")
                else:
                    analyzer = JDAnalyzerV2(openai)
                    print("LOG: Using JD Analysis Engine V2 (Expert)")
                
                # [Fix 3.4] Use session state JD text
                jd_to_analyze = st.session_state.get("jd_text", "")
                analysis_result = analyzer.analyze(jd_to_analyze)
                
                # Store in Session State
                st.session_state.analysis_data_v3 = analysis_result
                st.session_state.analysis_data = analysis_result # [PHASE 3] Back-sync
                st.success(f"✅ {engine}를 통한 JD 재분석이 완료되었습니다!")
                
                # Save Summary for UI
                role = analysis_result.get("canonical_role", "Unknown")
                core_signals = analysis_result.get("core_signals", [])
                st.session_state.jd_summary = f"{role} ({', '.join(core_signals[:3])}...)"
                
                # Log
                st.session_state.pipeline_logs.append(f"JD ANALYSIS V3: Role={role}")

                st.session_state.step = "review" # [CRITICAL] Move to review so user can trigger search
                st.rerun()
                
            except Exception as e:
                st.error(f"Analysis Error: {e}")
                print(f"Analysis Error: {e}")
                if st.button("Retry"):
                    st.rerun()




    # ==========================
    # STEP 3: Results & Feedback
    # ==========================
    elif st.session_state.step == "results":
        # [PHASE 3] Display Strategy & Confidence
        conf = st.session_state.analysis_data_v3.get("confidence_score", 0)
        mode = "PRECISION" if conf >= 70 else "RECALL"
        
        c1, c2, c3 = st.columns([1, 1, 2])
        c1.metric("JD Confidence", f"{conf}%", delta_color="normal" if conf > 70 else "off")
        c2.metric("Search Mode", mode, help="Precision: Strict matching. Recall: Broader search for ambiguous JDs.")
        
        if conf < 70:
            st.warning(f"⚠️ **JD 명확도 낮음 ({conf}%)**: JD 내용이 모호합니다. 더 넓은 범위로 검색합니다 (Recall Mode).")
            
        st.markdown(f"#### 3️⃣ 검색 결과: **{len(st.session_state.search_results)}** 건 매칭")
        
        # [DEBUG] Internal State Inspector
        with st.expander("🕵️‍♂️ Debug Info (Why this result?)", expanded=False):
            st.write(f"**Confidence Score:** {conf} (Raw: {st.session_state.analysis_data_v3.get('confidence_score_val', 0)})")
            st.write(f"**Current Strategy:** {st.session_state.get('current_strategy_mode', 'Unknown').upper()}")
            st.write(f"**Inferred Role:** {st.session_state.analysis_data_v3.get('inferred_role', 'N/A')}")
            st.write(f"**Discriminator (Wrong Roles):** {st.session_state.analysis_data_v3.get('wrong_roles', [])}")
            st.write(f"**Role Aliases Used:** {get_role_aliases(st.session_state.analysis_data_v3.get('inferred_role', '')) if st.session_state.get('current_strategy_mode') == 'recall' else 'None (Precision Mode)'}")
            st.json(st.session_state.analysis_data_v3)

        # [NEW] Search Logic Trace
        with st.expander("🔍 검색 로그 (Search Logic Trace)", expanded=False):
            if "pipeline_logs" in st.session_state:
                for log in st.session_state.pipeline_logs:
                    if "DROP" in log:
                        st.markdown(f"<span style='color:red'>{log}</span>", unsafe_allow_html=True)
                    elif "PIPELINE" in log:
                         st.markdown(f"**{log}**")
                    else:
                        st.text(log)
            else:
                st.caption("로그가 없습니다.")
        
        if not st.session_state.search_results:
            # [PHASE 2.3] Smart Empty State
            inferred = st.session_state.analysis_data_v3.get('inferred_role', 'Unknown Role')
            conf_val = st.session_state.analysis_data_v3.get("confidence_score_val", 0)
            
            st.warning("⚠️ 매칭된 후보자가 없습니다.")
            
            if conf_val >= 80:
                st.markdown(f"""
                **🧐 분석 결과**: 
                JD가 매우 구체적입니다. AI가 추론한 **'{inferred}'** 역할에 정확히 부합하는 후보자가 부족합니다.
                
                **시스템 조치**:
                - 정밀도(Precision) 기준을 높여 '오탐(False Positive)'을 방지했습니다.
                - 이력서와 JD 간의 **'해상도 불일치(Resolution Mismatch)'** 가능성이 있습니다.
                """)
            else:
                st.markdown("""
                **🧐 분석 결과**: 
                검색 범위를 넓혔음에도(Recall Mode) 적절한 후보자를 찾지 못했습니다.
                """)

            if st.button("🔄 조건 수정하여 다시 검색"):
                st.session_state.step = "review"
                st.rerun()
        
        for cand in st.session_state.search_results:
            data = cand['data']
            cand_id = cand['id']
            name = data.get('name', 'Unknown')
            comp = data.get('current_company', 'N/A')
            
            # [PHASE 3] Human Verification Flag
            # If Search Mode is RECALL (Low Confidence) OR AI Score is borderline (40-60)
            needs_human_review = (conf < 70) or (40 <= cand.get('ai_eval_score', 0) <= 60)
            domain = data.get('domain', 'General')
            
            # [Fix] Construct URL if missing
            url = data.get('url')
            if not url or url == '#' or 'notion.so' not in url:
                page_id = data.get('candidate_id', cand_id)
                if page_id and len(page_id) >= 32:
                    # [Fix] Use robust URL fetcher (Cached if possible, but for now direct)
                    # We pass 'notion' client to the helper
                    url = get_notion_url(notion, page_id)
                else:
                    url = "#" # No valid link
            
            ai_score = cand.get('ai_eval_score', 0)
            ai_reason = cand.get('ai_reason', '')
            
            # [PHASE 3] Logic for Badge
            verify_badge = ""
            if (conf < 70) or (40 <= ai_score <= 60):
                verify_badge = "<span style='background-color: #FEF3C7; color: #92400E; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; margin-left: 8px; vertical-align: middle;'>⚠️ Verify</span>"
            
            # --- Candidate Card ---
            # Dynamic Badge Color based on AI Score
            badge_color = "#E5E7EB" # gray
            if ai_score >= 80: badge_color = "#D1FAE5" # green
            elif ai_score >= 50: badge_color = "#FEF9C3" # yellow
            elif ai_score > 0: badge_color = "#FEE2E2" # red (low match)
            
            card_html = textwrap.dedent(f"""\
            <div class="job-item">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div class="job-title" style="margin:0; display: flex; align-items: center;">{name} {verify_badge}</div>
                    <a href="{url}" target="_blank" style="text-decoration:none;">
                        <div style="
                            background: {badge_color}; 
                            padding: 6px 12px; 
                            border-radius: 6px; 
                            font-size: 0.9rem; 
                            color: #111827; 
                            font-weight: 600; 
                            border: 1px solid #E5E5E5;">
                            AI Match: {ai_score}
                        </div>
                    </a>
                </div>
                <div class="job-meta" style="margin-top: 4px;">
                    {domain} <span style="margin:0 8px">|</span> {comp}
                </div>
                
                <div style="margin-top: 12px; background: #F9FAFB; padding: 10px; border-radius: 6px; font-size: 0.9em; border-left: 3px solid #6366F1;">
                    <span style="font_weight:600">🤖 AI 분석:</span> {ai_reason}
                    {"<br><span style='color:#EF4444; font-weight:600'>⚠️ 조건 불일치 (감점 -" + str(cand.get('filter_penalty', 0)) + "): " + ", ".join(cand.get('penalty_reasons', [])) + "</span>" if cand.get('filter_penalty', 0) > 0 else ""}
                </div>
            </div>
            """)
            st.markdown(card_html, unsafe_allow_html=True)
            
            # --- Feedback UI (Interactive) ---
            # Unique ID for feedback state
            fb_key_bad = f"fb_bad_{cand_id}"
            fb_key_good = f"fb_good_{cand_id}"
            input_key_good = f"txt_good_{cand_id}"
            input_key_bad = f"txt_bad_{cand_id}"
            
            c_fb1, c_fb2, c_rest = st.columns([1, 1, 8])
            
            with c_fb1:
                # LIKE Button
                if st.button("👍", key=f"btn_like_{cand_id}"):
                     st.session_state[fb_key_good] = not st.session_state.get(fb_key_good, False)
                     st.session_state[fb_key_bad] = False # Close bad if open
            
            with c_fb2:
                # DISLIKE Button
                if st.button("👎", key=f"btn_dislike_{cand_id}"):
                    st.session_state[fb_key_bad] = not st.session_state.get(fb_key_bad, False)
                    st.session_state[fb_key_good] = False # Close good if open
            
            # Show Feedback Inputs
            if st.session_state.get(fb_key_good, False):
                with st.expander("이 인재가 적합한 이유는?", expanded=True):
                    reason_good = st.text_input("Good Points", key=input_key_good, placeholder="예: 직무 경험 일치, 필수 스택 보유...")
                    if st.button("피드백 저장", key=f"sub_good_{cand_id}"):
                        save_feedback(name, reason_good, "positive", st.session_state.jd_text, candidate_id=cand_id)
                        st.toast("Positive Feedback Saved! ✅")
                        st.session_state[fb_key_good] = False
                        st.session_state.pop(input_key_good, None) # Clear text
                        st.rerun()

            if st.session_state.get(fb_key_bad, False):
                with st.expander("이 인재가 부적합한 이유는?", expanded=True):
                    reason_bad = st.text_input("Missing Points", key=input_key_bad, placeholder="예: 연차 부족, 기술 스택 불일치...")
                    if st.button("피드백 저장", key=f"sub_bad_{cand_id}"):
                        save_feedback(name, reason_bad, "negative", st.session_state.jd_text, candidate_id=cand_id)
                        st.toast("Negative Feedback Saved! 📉")
                        st.session_state[fb_key_bad] = False
                        st.session_state.pop(input_key_bad, None) # Clear text
                        st.rerun()
            
            # --- AI Recommendation (RAG) ---
            # Using st.expander for cleaner UI
            with st.expander(f"🤖 AI Recommendation for {name}", expanded=False):
                 # Check if we already fetched RAG for this candidate
                rag_key = f"rag_{cand_id}"
                if rag_key not in st.session_state:
                    with st.spinner("Reading resume..."):
                        full_text = ""
                        page_id = data.get('candidate_id', cand_id) # Ensure page_id is defined
                        
                        if page_id:
                            try:
                                full_text = notion.get_page_full_text(page_id)
                            except: pass
                        
                        context = full_text[:3000] if full_text else str(data)
                        
                        # [Fix] Use Cached RAG Function
                        try:
                            rec_text = get_rag_recommendation(
                                page_id=page_id,
                                jd_summary=st.session_state.jd_text[:500],
                                candidate_name=name,
                                context_text=context
                            )
                            st.session_state[rag_key] = rec_text
                        except Exception:
                            st.session_state[rag_key] = "AI analysis unavailable."
                
                # Display cached RAG text
                st.info(st.session_state.get(rag_key, ""))

        st.markdown("---")
        if st.button("🔄 Start Fresh Search", use_container_width=True):
             st.session_state.step = "input"
             st.session_state.analysis_data_v3 = {"must": [], "nice": [], "domain": []}
             st.session_state.search_results = []
             st.session_state.jd_text = ""
             st.rerun()

    else:
        st.markdown("""
        <div style="color:#9CA3AF; margin-top:40px; text-align:center;">
            Enter Job Description above to start search.
        </div>
        """, unsafe_allow_html=True)
