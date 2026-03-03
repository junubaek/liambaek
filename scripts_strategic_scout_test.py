
import json
import os
from headhunting_engine.matching.scorer import Scorer
from headhunting_engine.matching.version_manager import VersionManager
from headhunting_engine.analytics.scarcity import ScarcityEngine
from headhunting_engine.analytics.strategic_scout import StrategicScout

def test_solo_control_flow():
    # 0. Setup
    dict_path = "headhunting_engine/dictionary/canonical_dictionary_v1.json"
    snapshot_path = "headhunting_engine/analytics/scarcity_snapshot.json"
    pool_path = "headhunting_engine/analytics/reparsed_pool_v1.2.json"
    
    if not os.path.exists(pool_path):
        # Fallback to partial if full not ready
        pool_path += ".partial"

    vm = VersionManager("1.3.1")
    scorer = Scorer(vm)
    scarcity_engine = ScarcityEngine(snapshot_path)
    
    scout = StrategicScout(scorer, scarcity_engine, pool_path)

    # 1. New JD Simulation (AI Backend Engineer)
    new_jd = {
        "name": "Senior AI Platform Engineer",
        "must": ["Language_Python", "DL_Framework", "Cloud_AWS"],
        "nice": ["MLOps", "Distributed_Training"]
    }

    print(f"🚀 [JD Received] {new_jd['name']}")
    
    # 2. Diagnose
    diagnosis = scout.diagnose_jd(new_jd["must"], new_jd["nice"])
    print(f"\n🔍 [Diagnosis Results]")
    print(f"- Difficulty: {diagnosis['difficulty_level']}")
    print(f"- JD Scarcity: {diagnosis['jd_scarcity_score']}")
    print(f"- Expected Sourcing: {diagnosis['expected_sourcing_weeks']} weeks")

    # 3. Match & Analysis
    analysis = scout.match_and_analyze(new_jd["must"], new_jd["nice"])
    print(f"\n📊 [Match Analysis]")
    print(f"- Found {analysis['top_candidate_count']} potential matching candidates in DB.")
    print(f"- Top Candidates: {', '.join([c['name'] for c in analysis['top_candidates'][:3]])}")
    print(f"- Major Skill Gaps in DB: {analysis['major_skill_gaps']}")
    
    # 4. Strategic Script
    script = scout.generate_strategic_script(diagnosis, analysis)
    print("\n📜 [Strategic Response Script for Client]")
    print(script)

if __name__ == "__main__":
    test_solo_control_flow()
