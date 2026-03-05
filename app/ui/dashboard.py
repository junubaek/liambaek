import streamlit as st
import json
import pandas as pd
import os
import sys
import sqlite3

# Ensure app is importable
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.append(current_dir)

from app.connectors.openai_api import OpenAIClient
from app.utils.jd_parser_v3 import JDParserV3
from app.engine.risk_engine import JDRiskEngine
from app.engine.scarcity import ScarcityEngine
from app.engine.matcher import Scorer
from headhunting_engine.data_core import AnalyticsDB

# 1. Page Configuration
st.set_page_config(page_title="AI Headhunting Market Intelligence OS", layout="wide")

st.title("🛡️ AI Talent Market Intelligence OS (Phase 5.3)")
st.markdown("---")

# Initialize session state for JD analysis
if 'jd_signals' not in st.session_state:
    st.session_state.jd_signals = None

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔍 JD Intelligence Layer")
    jd_input = st.text_area("Job Description Analysis", "Paste JD here...", height=250)
    if st.button("Diagnose JD"):
        if jd_input and jd_input != "Paste JD here...":
            st.info("Analyzing structural risks & pattern density...")
            try:
                with open("secrets.json", "r") as f:
                    secrets = json.load(f)
                openai = OpenAIClient(secrets["OPENAI_API_KEY"])
                
                parser = JDParserV3(openai, "app/ontology/ontology.json")
                signals = parser.parse_jd(jd_input)
                st.session_state.jd_signals = signals
                
                scarcity = ScarcityEngine()
                risk_engine = JDRiskEngine(scarcity)
                risk = risk_engine.predict_risk(signals.get("functional_domains", []), signals.get("experience_patterns", []))
                
                st.success("Analysis Complete!")
                st.json({
                    "extracted_patterns": signals.get("experience_patterns"),
                    "extracted_domains": signals.get("functional_domains"),
                    "difficulty_score": risk['forecast']['difficulty_score'],
                    "success_probability": risk['forecast']['success_probability']
                })
            except Exception as e:
                st.error(f"Analysis Failed: {e}")

with col2:
    st.subheader("📊 Pattern Coverage Debugger")
    if st.session_state.jd_signals:
        jd_patterns = st.session_state.jd_signals.get("experience_patterns", [])
        if jd_patterns:
            db_path = "headhunting_engine/data/analytics.db"
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                coverage_data = []
                for p in jd_patterns:
                    cursor.execute("SELECT COUNT(*) FROM candidate_patterns WHERE pattern = ?", (p,))
                    count = cursor.fetchone()[0]
                    coverage_data.append({"Pattern": p, "Market Availability": count})
                
                df_coverage = pd.DataFrame(coverage_data)
                
                # Import altair for better control over the chart
                import altair as alt
                
                chart = alt.Chart(df_coverage).mark_bar(color='#4F46E5').encode(
                    x=alt.X('Market Availability:Q', title='Found in DB'),
                    y=alt.Y('Pattern:N', sort='-x', title=None),
                    tooltip=['Pattern', 'Market Availability']
                ).properties(height=300)
                
                st.altair_chart(chart, use_container_width=True)
                conn.close()
            except:
                st.warning("Could not calculate coverage. Index might be empty.")
        else:
            st.info("JD contains no extractable patterns.")
    else:
        st.info("Analyze JD to see Market Pattern Coverage.")

st.markdown("---")
st.markdown("### 🏆 Top Matches (Universal Matching Formula v5.3)")

if st.session_state.jd_signals:
    try:
        scorer = Scorer()
        db_path = "headhunting_engine/data/analytics.db"
        
        if not os.path.exists(db_path):
            st.error("Database connection failed.")
        else:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Fetch candidates from Data Lake (No tenant_id in snapshots)
            cursor.execute("SELECT notion_id, name, role, data_json FROM candidate_snapshots")
            candidates = cursor.fetchall()
            
            match_results = []
            with open("secrets.json", "r") as f:
                secrets = json.load(f)
            tenant_id = secrets.get("TENANT_ID", "default")
            
            for cand_id, name, role, data_json in candidates:
                try:
                    # Role is often saved in data_json or separate field during hardening
                    cand_data = json.loads(data_json)
                    role_cluster = role or cand_data.get("role_cluster") or "Unknown"
                    
                    # Pass cand_id to use the V5.3 Search Index [sqlite candidate_patterns]
                    score, b = scorer.calculate_score([], st.session_state.jd_signals, candidate_id=cand_id, tenant_id=tenant_id)
                    
                    match_results.append({
                        "Candidate": name,
                        "Score": b['final_score'],
                        "Role Cluster": role_cluster,
                        "Patterns Found": int(b.get("pattern_match", 0) / 10)
                    })
                except:
                    continue
            
            if match_results:
                df = pd.DataFrame(match_results).sort_values(by="Score", ascending=False)
                st.write(f"Showing matches from total pool of **{len(match_results)}** candidates.")
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No patterns found in index. Please run 'Pattern Extractor' to populate the search index.")
            conn.close()
    except Exception as e:
        st.error(f"Matching Error: {e}")
else:
    st.caption("Perform JD analysis to see live candidate rankings.")
