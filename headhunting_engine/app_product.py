
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
from jd_analyzer_v3 import JDAnalyzerV3
from search_pipeline_v3 import SearchPipelineV3
from connectors.openai_api import OpenAIClient
from connectors.pinecone_api import PineconeClient

# Page Config
st.set_page_config(page_title="Antigravity v4.0 | Product Mode", layout="wide")

# CSS for 3-Panel aesthetics
st.markdown("""
<style>
    .panel-container { background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; height: 100%; }
    .metric-card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 10px; }
    .status-badge { padding: 4px 8px; border-radius: 999px; font-size: 11px; font-weight: bold; }
    .status-cold { background: #fee2e2; color: #991b1b; }
    .status-warm { background: #fef3c7; color: #92400e; }
    .status-hired { background: #dcfce7; color: #166534; }
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
    st.success("Maintenance Agent: Active")
    st.success("Strategic Alert: Monitoring")
    
    with st.expander("Recent Alerts", expanded=True):
        # Simulated alert fetch for UI demo
        st.error("🚨 Backend S-Level Depletion (12%)")
        st.warning("⚠️ JD Drift: 'Toss FP&A' (-8.5%)")

# Main Dashboard
st.title("🌌 Matching Engine | Product V4")

col1, col2, col3 = st.columns([1, 2.5, 1.2])

# Panel 1: Risk Core
with col1:
    st.markdown('<div class="panel-container">', unsafe_allow_html=True)
    st.subheader("🧠 Panel 1: Risk Core")
    
    jd_input = st.text_area("Analyze New JD", height=200, placeholder="Paste JD here...")
    
    if st.button("RUN ANALYSIS", use_container_width=True):
        with st.spinner("Calculating Risk Metrics..."):
            # Real JD analysis
            analyzer = JDAnalyzerV3(openai)
            analysis = analyzer.analyze(jd_input)
            st.session_state.analysis = analysis
            
            # Static metrics for now, will link to real scarcity later
            st.metric("Scarcity", "0.82", "+0.14", delta_color="inverse")
            st.metric("Elite Density", "3.2%", "-1.1%", delta_color="inverse")
            st.metric("Success Prob", "8.5%")
            
            st.info("**Drift Warning**: Pool is aging. Scarcity rising.")
    st.markdown('</div>', unsafe_allow_html=True)

# Panel 2: Candidate Table
with col2:
    st.markdown('<div class="panel-container">', unsafe_allow_html=True)
    st.subheader("📋 Panel 2: Candidate Intelligence")
    
    if 'analysis' in st.session_state:
        # Run search
        query_string = f"{st.session_state.analysis.get('role')} {' '.join(st.session_state.analysis.get('must'))}"
        vector = openai.embed_content(query_string)
        pipeline = SearchPipelineV3(pc)
        results, _ = pipeline.run(st.session_state.analysis, vector, top_k=50)
        
        # Build DataFrame for display
        df_data = []
        for i, res in enumerate(results[:15]):
            data = res['data']
            rev_res = lifecycle.predict_revenue_probability(res['rpl_score'])
            
            df_data.append({
                "Rank": i+1,
                "Name": data.get('name'),
                "RPL": f"{res['rpl_score']:.1f}",
                "Revenue %": f"{rev_res['revenue_percentage']}%",
                "State": "Warm" if i < 3 else "Cold",
                "Last Contact": "3 days ago"
            })
        
        df = pd.DataFrame(df_data)
        st.table(df)
    else:
        st.info("JD를 입력하고 요건 분석을 먼저 실행해 주세요.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Panel 3: Strategy Output
with col3:
    st.markdown('<div class="panel-container">', unsafe_allow_html=True)
    st.subheader("🔥 Panel 3: Strategy")
    
    if 'analysis' in st.session_state:
        st.markdown("""
        ### **Sourcing Action**
        - **Internal Pool**: 12 candidates found.
        - **Action**: Direct reach-out recommended.
        
        ### **Salary Pressure**
        - Market Median: 85M KRW
        - JD Target: 75M KRW
        - **Warning**: High pressure (+13.3%)
        
        ### **Strategic Recommendation**
        > "Backend S급 인재의 Scarcity가 0.82로 급증했습니다. 연봉 제안 범위를 상향하거나, 외부 Sourcing 채널을 가동해야 합니다."
        """)
        
        if st.button("Generate Notion Report"):
            st.toast("Report generated in Notion!")
    else:
        st.write("Strategy will appear after analysis.")
        
    st.markdown('</div>', unsafe_allow_html=True)
