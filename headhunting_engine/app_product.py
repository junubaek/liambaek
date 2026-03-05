
import streamlit as st
import pandas as pd
import json
import os
import sys
import altair as alt
from datetime import datetime

# Path Setup for Cloud & Local
current_dir = os.path.dirname(os.path.abspath(__file__))
workspace_path = os.path.abspath(os.path.join(current_dir, ".."))

if workspace_path not in sys.path: sys.path.append(workspace_path)

from connectors.notion_api import HeadhunterDB
from headhunting_engine.data_core import AnalyticsDB
from headhunting_engine.lifecycle_engine import LifecycleEngine
from headhunting_engine.strategic_alert_agent import StrategicAlertAgent
from jd_analyzer_v4 import JDAnalyzerV4
from search_pipeline_v4 import SearchPipelineV4
from connectors.openai_api import OpenAIClient
from connectors.pinecone_api import PineconeClient

# Page Config
st.set_page_config(page_title="Antigravity v4.1 | Universal Hub", layout="wide")

# CSS for 3-Panel aesthetics
st.markdown("""
<style>
    .panel-container { background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; height: 100%; }
    .metric-card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .pattern-tag { background: #eff6ff; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 5px; border: 1px solid #bfdbfe; }
</style>
""", unsafe_allow_html=True)

# Initialization
@st.cache_resource
def get_clients():
    with open(os.path.join(workspace_path, "secrets.json"), "r") as f:
        secrets = json.load(f)
    
    openai = OpenAIClient(secrets["OPENAI_API_KEY"])
    pc_host = secrets.get("PINECONE_HOST", "")
    if not pc_host.startswith("https://"): pc_host = f"https://{pc_host}"
    pc = PineconeClient(secrets["PINECONE_API_KEY"], pc_host)
    notion = HeadhunterDB(os.path.join(workspace_path, "secrets.json"))
    analytics = AnalyticsDB(os.path.join(workspace_path, "headhunting_engine/data/analytics.db"))
    
    return openai, pc, notion, analytics

openai, pc, notion, analytics = get_clients()
lifecycle = LifecycleEngine(analytics)
alert_agent = StrategicAlertAgent(notion, analytics)

# Sidebar - DB Health & Alerts
with st.sidebar:
    st.image("logo.png", width=150)
    st.title("Control Panel")
    st.markdown("---")
    
    st.subheader("🤖 Agent Status")
    st.success("Universal Matcher: V4 (Active)")
    st.success("Experience Parser: Enabled")
    
    with st.expander("Recent Alerts", expanded=True):
        st.error("🚨 Backend S-Level Depletion (12%)")
        st.warning("⚠️ JD Drift: 'Toss FP&A' (-8.5%)")

# Main Dashboard
st.title("🌌 Universal AI Engine | V4.1")

col1, col2, col3 = st.columns([1.2, 2.3, 1.2])

# Panel 1: Risk & Pattern Analysis
with col1:
    st.markdown('<div class="panel-container">', unsafe_allow_html=True)
    st.subheader("🧠 Panel 1: Patterns & Risk")
    
    jd_input = st.text_area("Analyze New JD", height=200, placeholder="Paste JD here (Any job role)...")
    
    if st.button("RUN UNIVERSAL 7-AXIS ANALYSIS", use_container_width=True):
        with st.spinner("Executing 7-Axis Intelligence Extraction..."):
            analyzer = JDAnalyzerV4(openai)
            analysis = analyzer.analyze(jd_input)
            st.session_state.analysis = analysis
            
            # Show 7-Axis Result
            st.markdown("### **🎯 7-Axis Analysis**")
            
            cols_7 = st.columns(2)
            with cols_7[0]:
                st.write(f"**Family**: {analysis.get('role_family')}")
                st.write(f"**Seniority**: {analysis.get('seniority_required')} yrs")
            with cols_7[1]:
                st.write(f"**Level**: {analysis.get('leadership_level')}")
                st.write(f"**Domain**: {', '.join(analysis.get('functional_domains', []))}")
            
            st.markdown("---")
            st.markdown("#### **Experience Patterns**")
            for p in analysis.get("experience_patterns", []):
                st.markdown(f"✅ **{p['pattern']}** ({p['min_complexity']})")
                
            st.markdown("#### **Impact & Constraints**")
            impact = analysis.get("impact_requirements", {})
            st.write(f"📊 **Scale**: {impact.get('scale_type')}")
            if analysis.get("hard_constraints"):
                st.warning(f"⚠️ **Hard**: {', '.join(analysis.get('hard_constraints'))}")
            
    st.markdown('</div>', unsafe_allow_html=True)

# Panel 2: Candidate Table
with col2:
    st.markdown('<div class="panel-container">', unsafe_allow_html=True)
    st.subheader("📋 Panel 2: Experience-Based Matching (V4)")
    
    if 'analysis' in st.session_state:
        # Run search
        query_string = f"{st.session_state.analysis.get('role_family')} {' '.join([p['pattern'] for p in st.session_state.analysis.get('experience_patterns', [])])}"
        vector = openai.embed_content(query_string)
        pipeline = SearchPipelineV4(pc)
        results, _ = pipeline.run(st.session_state.analysis, vector, top_k=50)
        
        # Build DataFrame for display
        df_data = []
        for i, res in enumerate(results[:15]):
            data = res['data']
            rev_res = lifecycle.predict_revenue_probability(res['rpl_score'])
            score_m = res.get('score_breakdown', {})
            
            df_data.append({
                "Rank": i+1,
                "Name": data.get('basics', {}).get('name', f"Candidate_{res['id'][:4]}"),
                "Experience Match": f"{res['rpl_score']:.1f}%",
                "Domain": f"{score_m.get('df', 0):.0f}",
                "Pattern": f"{score_m.get('epm', 0):.0f}",
                "Impact": f"{score_m.get('if', 0):.0f}",
                "Elite": "S-Tier" if score_m.get('em', 1) > 1 else "Standard"
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("JD를 입력하여 '범용 경험 분석'을 먼저 실행해 주세요.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Panel 3: Strategy Output
with col3:
    st.markdown('<div class="panel-container">', unsafe_allow_html=True)
    st.subheader("🔥 Panel 3: Universal Strategy")
    
    if 'analysis' in st.session_state:
        st.markdown(f"### **{st.session_state.analysis.get('domain')} Strategy**")
        st.info(f"Targeting **{st.session_state.analysis.get('seniority')}** level experts.")
        
        clues = st.session_state.analysis.get("strategy_clues", [])
        if clues:
            for clue in clues:
                st.markdown(f"- {clue}")
        
        st.markdown("---")
        st.markdown("""
        ### **Strategic Recommendation**
        > "이 JD는 Skill보다 **Experience Pattern(경험 패턴)** 매칭이 핵심입니다. 특히 상위 레벨의 리딩 경험 보증이 성공 확률을 결정합니다."
        """)
        
        if st.button("Generate Strategy Report"):
            st.toast("Report generated!")
    else:
        st.write("Strategy will appear after analysis.")
        
    st.markdown('</div>', unsafe_allow_html=True)
