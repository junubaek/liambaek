from headhunting_engine.matching.scorer import Scorer
from headhunting_engine.analytics.strategic_scout import StrategicScout
from headhunting_engine.analytics.risk_engine import JDRiskEngine
from headhunting_engine.analytics.scarcity import ScarcityEngine
import json
import os

def run_toss_analysis():
    # 1. Setup Paths
    # Use the elite pool for matching (v1.3_elite)
    pool_path = "headhunting_engine/analytics/reparsed_pool_v1.3_elite.json"
    scarcity_path = "headhunting_engine/analytics/scarcity_snapshot.json"
    dict_path = "headhunting_engine/dictionary/canonical_dictionary_v1.json"

    if not os.path.exists(pool_path):
        # Fallback to current batch if elite doesn't exist yet (though it should)
        pool_path = "headhunting_engine/analytics/reparsed_pool_v1.2.json.partial"

    # 2. Define JD Data
    must = [
        "__TEMP__Financial_Modeling",
        "__TEMP__Finance"
    ]
    nice = [
        "__TEMP__Strategic_Planning",
        "__TEMP__Data_Analysis",
        "DB_SQL",
        "__TEMP__BI_Dashboard"
    ]

    # 3. Initialize Engines
    scorer = Scorer(dict_path)
    se = ScarcityEngine(scarcity_path)
    re = JDRiskEngine(se, pool_path)
    scout = StrategicScout(scorer, se, re, pool_path)

    # 4. Run Analysis
    print(f"🕵️ Analyzing JD for Toss Insurance...")
    
    # JD Risk Forecast
    diagnosis = scout.diagnose_jd(must, nice)
    
    # 4. Run Analysis
    diagnosis = re.predict_risk(must, nice)
    analysis = scout.match_and_analyze(must, nice)
    
    # 5. Generate Strategic Report
    # Pass the list of matches (top_candidates) to generate_strategic_script
    script = scout.generate_strategic_script(diagnosis, analysis.get("top_candidates", []))

    # 5. Output Results
    report_output_path = "headhunting_engine/analytics/strategic_report_toss.md"
    with open(report_output_path, "w", encoding="utf-8") as f:
        f.write("# 💎 [Strategy Analysis] 토스인슈어런스 FP&A Manager\n")
        f.write(script)
    
    print(f"✅ Strategic Report generated at {report_output_path}")

if __name__ == "__main__":
    run_toss_analysis()
