import json
import os
import sys

# Ensure app is importable
sys.path.append(os.getcwd())

from app.connectors.openai_api import OpenAIClient
from app.utils.jd_parser_v3 import JDParserV3
from app.utils.resume_parser import ResumeParser
from app.engine.matcher import Scorer
from app.engine.risk_engine import JDRiskEngine

def run_integrated_test():
    print("🚀 Starting Phase 5 Integrated End-to-End Test...")
    
    # 1. Load Secrets & Initialize
    try:
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
        openai = OpenAIClient(secrets["OPENAI_API_KEY"])
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        return

    # 2. Test JD Extraction (Universal GA Role)
    print("\n--- [Step 1] JD Extraction (7-Axis) ---")
    jd_text = """
    우리는 사옥 이전 및 자산 관리를 담당할 총무팀장(GA Team Leader)을 찾습니다.
    - 경력: 10년 이상
    - 주요 업무: 오피스 이전 프로젝트 리딩, 임대차 계약 협상, 자산 관리 시스템 구축.
    - 필수 조건: 영어 능통, 대기업 총무 경력.
    - 예산 관리: 연간 10억 규모.
    """
    ontology_path = "app/ontology/ontology.json"
    jd_parser = JDParserV3(openai, ontology_path)
    # Note: parse_jd normally calls LLM. For dry-run we simulate or call if keys exist.
    # In this environment, we should try to call to ensure reliability.
    jd_signals = jd_parser.parse_jd(jd_text)
    print(f"✅ Extracted Role Family: {jd_signals.get('role_family')}")
    print(f"✅ Extracted Patterns: {jd_signals.get('experience_patterns')}")

    # 3. Test Resume Extraction (Experience Pattern)
    print("\n--- [Step 2] Resume Extraction (Experience Graph) ---")
    resume_text = """
    김철수 - 총무 분야 12년 경력. 
    최근 300인 규모 오피스 이전을 설계(Architected)하고 성공적으로 완수함.
    임대차 계약 협상 및 관리를 주도(Led)함.
    총 자산 50억 규모 관리 경험.
    """
    resume_parser = ResumeParser(openai)
    candidate_data = resume_parser.parse(resume_text)
    quality = resume_parser.calculate_quality_score(candidate_data)
    print(f"✅ Extraction Status: {candidate_data.get('basics', {}).get('name', 'Extracted')}")
    print(f"✅ Data Quality: {quality['status']} ({quality['total_score']})")

    # 4. Test Universal Matching (v4)
    print("\n--- [Step 3] Universal Matching (6-Factor) ---")
    scorer = Scorer()
    # Flatten patterns for scorer v4
    flattened_patterns = [
        {"pattern": p.get("pattern"), "depth": p.get("depth")} 
        for p in candidate_data.get("experience_patterns", [])
    ]
    
    score, details = scorer.calculate_score(flattened_patterns, context_data=jd_signals)
    print(f"✅ Final Match Score: {score}")
    print(f"✅ Pattern Match Detail: {details['pattern_match']}")

    # 5. Test Risk Forecasting (v4)
    print("\n--- [Step 4] Strategic Risk Forecasting ---")
    risk_engine = JDRiskEngine(None) # Scarcity fallback for test
    risk = risk_engine.predict_risk(jd_signals.get("functional_domains"), jd_signals.get("experience_patterns"))
    print(f"✅ JD Difficulty: {risk['forecast']['difficulty_score']} ({risk['forecast']['difficulty_level']})")
    print(f"✅ Success Prob: {risk['forecast']['success_probability']}")

    print("\n🎉 Integrated Test Completed Successfully!")

if __name__ == "__main__":
    run_integrated_test()
