import json
import os
import sys

# Ensure app is importable
sys.path.append(os.getcwd())

from app.connectors.openai_api import OpenAIClient
from app.utils.jd_parser_v3 import JDParserV3

def verify_finance_extraction():
    print("🚀 Verifying Finance JD Extraction...")
    
    # 1. Load Secrets & Initialize
    try:
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
        openai = OpenAIClient(secrets["OPENAI_API_KEY"])
    except Exception as e:
        print(f"❌ Initialization Failed: {e}")
        return

    # 2. Finance JD Text
    jd_text = """
    Position: Strategic Finance Manager(FP&A)
    Strategy Team은 전사의 주요 경영 지표(KPI) 설계 및 성과 트래킹, 사업 계획수립을 담당하며, 데이터에 기반해 회사의 중·장기 사업 방향과 실행 전략을 점검하고 개선하는 역할을 합니다.
    FP 모델을 더 뾰족하게 고도화하고 운영하면서, 회사가 더 잘 성장할 수 있게 돕습니다.
    회사 전략부터 손익 Projection까지, 크고 작은 중요한 의사결정에 직접 참여하게 돼요.
    재무 모델링·데이터 분석에 강점이 있으신 분이 필요해요.
    문제를 정의하고, 가설을 세운 뒤 임팩트 추정 -> 액션 아이템으로 연결한 경험이 있다면, 작성해 주세요.
    """
    
    ontology_path = "app/ontology/ontology.json"
    jd_parser = JDParserV3(openai, ontology_path)
    
    print("\n--- [Test] Extraction for Finance Manager ---")
    jd_signals = jd_parser.parse_jd(jd_text)
    
    print(f"✅ Extracted Role Family: {jd_signals.get('role_family')}")
    print(f"✅ Extracted Domains: {jd_signals.get('functional_domains')}")
    print(f"✅ Extracted Patterns: {jd_signals.get('experience_patterns')}")
    
    # Validation
    patterns = jd_signals.get('experience_patterns', [])
    if any(p in ["FP&A_Modeling", "KPI_Framework_Design", "Profit_Projection_Analysis"] for p in patterns):
        print("\n🎉 Verification SUCCESS: Finance patterns correctly identified!")
    else:
        print("\n❌ Verification FAILED: Finance patterns missing or misclassified.")

if __name__ == "__main__":
    verify_finance_extraction()
