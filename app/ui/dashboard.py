import streamlit as st
import json
import pandas as pd
import os
import sys
import sqlite3

# Ensure project root is in sys.path
sys.path.append(os.getcwd())

from headhunting_engine.matching.scorer import Scorer
from connectors.openai_api import OpenAIClient

# v6.2 Engine Configuration
st.set_page_config(page_title="AI Talent Intelligence OS v6.2", layout="wide")
st.title("🛡️ AI Talent Intelligence OS (v6.2)")
st.markdown("---")

if 'jd_signals' not in st.session_state:
    st.session_state.jd_signals = None

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔍 JD Intelligence v6.2")
    jd_input = st.text_area("Job Description", "Paste JD here...", height=250)
    if st.button("Analyze JD"):
        try:
            with open("secrets.json", "r") as f:
                secrets = json.load(f)
            with open("headhunting_engine/universal_ontology.json", "r", encoding="utf-8") as f:
                ontology = json.load(f)
            
            openai = OpenAIClient(secrets["OPENAI_API_KEY"])

            # Improved extraction for v6.2
            st.info("Extracting signals via OpenAI GPT-4o-mini...")
            prompt = f"""
Analyze this Job Description and extract recruitment signals as a JSON object.
Use the following ontology as a reference for sectors and experience patterns.

[ONTOLOGY]
{json.dumps(ontology)}

[SCHEMA]
{{
  "sector": "Primary sector from ontology",
  "experience_patterns": ["List of matching patterns"],
  "cross_sector_requested": boolean
}}

[JD]
{jd_input}

Respond ONLY with the JSON object.
"""
            signals = openai.get_chat_completion_json(prompt)
            print(f"DEBUG: Signals received: {signals}")
            
            if signals:
                st.session_state.jd_signals = signals
                st.success("Analysis Complete!")
                st.json(signals)
            else:
                st.error("Failed to extract signals. Please check your JD or API status.")
                print(f"DEBUG: Extraction failed for JD: {jd_input[:100]}...")
        except Exception as e:
            st.error(f"Error: {e}")

with col2:
    st.subheader("📊 Market Coverage")
    if st.session_state.jd_signals:
        patterns = st.session_state.jd_signals.get("experience_patterns", [])
        db_path = "headhunting_engine/data/analytics.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            counts = []
            for p in patterns:
                c = conn.execute("SELECT COUNT(*) FROM candidate_patterns WHERE pattern = ?", (p,)).fetchone()[0]
                counts.append({"Pattern": p, "Count": c})
            st.bar_chart(pd.DataFrame(counts).set_index("Pattern"))
            conn.close()

st.markdown("---")
st.subheader("🏆 Candidate Rankings (v6.2 Logic)")

if st.session_state.jd_signals:
    scorer = Scorer()
    db_path = "headhunting_engine/data/analytics.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT notion_id, name, data_json FROM candidate_snapshots")
    rows = cursor.fetchall()
    
    results = []
    for notion_id, name, data_json in rows:
        data = json.loads(data_json)
        # ONLY show candidates who have been migrated to v6.2
        if "v6_2_data" not in data:
            continue
            
        cand_v62 = data["v6_2_data"]
        score, details = scorer.calculate_score(cand_v62, st.session_state.jd_signals)
        
        # Link construction for Notion and Google Drive
        notion_url = data.get("url", f"https://www.notion.so/{notion_id.replace('-', '')}")
        drive_url = data.get("구글드라이브_링크") or data.get("cv_link") or data.get("구글_드라이브cv")
        
        results.append({
            "Name": name or "Unknown",
            "Total Score": score,
            "Coverage": details["pattern_coverage"],
            "Trajectory": details["trajectory"],
            "Fit": details["context_fit"],
            "Notion": notion_url,
            "CV": drive_url
        })
    
    if results:
        df = pd.DataFrame(results).sort_values("Total Score", ascending=False)
        st.dataframe(df, use_container_width=True, column_config={
            "Notion": st.column_config.LinkColumn("Notion Page", width="small"),
            "CV": st.column_config.LinkColumn("Google Drive", width="small")
        })
    else:
        st.warning("⚠️ No candidates migrated to v6.2 found. Please run Migration from the main terminal.")
    
    conn.close()
