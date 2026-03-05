import json
import os
import sys

# Ensure app is importable
sys.path.append(os.getcwd())

from app.connectors.openai_api import OpenAIClient
from app.utils.jd_parser_v3 import JDParserV3
from app.engine.risk_engine import JDRiskEngine
from app.engine.scarcity import ScarcityEngine

def run_analysis():
    # 1. Load Secrets
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    openai = OpenAIClient(secrets["OPENAI_API_KEY"])

    # 2. JD Text from User
    jd_text = """
    Position: Data Analyst (Strategy)
    Strategy Team은 전사의 주요 경영 지표(KPI) 설계 및 성과 트래킹, 사업 계획수립을 담당하며...
    비즈니스의 핵심 KPI를 정의하고 성과를 구조적으로 트레킹 합니다.
    (문제 정의 -> 가설 수립 -> 분석/모델링 -> 임팩트 추정 -> 실행안 도출 -> 실행결과 회고 및 Next Action) 전 과정에 주도적으로 참여합니다.
    SQL, BI 대시보드(Tableau), 데이터 시각화 경험...
    이해관계자 설득 커뮤니케이션.
    """

    # 3. Parse JD
    parser = JDParserV3(openai, "app/ontology/ontology.json")
    signals = parser.parse_jd(jd_text)
    
    # 4. Analyze Risk
    scarcity = ScarcityEngine()
    risk_engine = JDRiskEngine(scarcity)
    risk = risk_engine.predict_risk(signals.get("functional_domains", []), signals.get("experience_patterns", []))

    # 5. Output for Briefing
    report = {
        "signals": signals,
        "risk": risk
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    run_analysis()
