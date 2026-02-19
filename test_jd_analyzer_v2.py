import sys
import os
from connectors.openai_api import OpenAIClient
from jd_analyzer_v2 import JDAnalyzerV2

# 1. Setup
try:
    # Load secrets
    import json
    if os.path.exists("secrets.json"):
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
            api_key = secrets.get("OPENAI_API_KEY")
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in secrets.json or env vars.")
        sys.exit(1)

    openai = OpenAIClient(api_key)
    analyzer = JDAnalyzerV2(openai)
    print("✅ JDAnalyzerV2 Initialized")
except Exception as e:
    print(f"❌ Initialization Failed: {e}")
    sys.exit(1)

# 2. Test Cases
test_cases = [
    {
        "id": "TOSS_PM",
        "jd": """
        [Product Owner (Internal Platform)]
        - 내부 개발자 도구 기획 및 운영
        - 개발자들과 긴밀한 협업 필요
        - B2B SaaS 제품 로드맵 수립
        - 데이터 기반 의사결정
        """,
        "expected_role_keywords": ["Product Owner", "PO", "프로덕트 오너", "기획자", "PM"],
        "expected_discriminator": True
    },
    {
        "id": "NPU_ENG",
        "jd": """
        [NPU Compiler Engineer]
        - NPU 하드웨어에 최적화된 컴파일러 백엔드 개발
        - LLVM/GCC 기반 최적화
        - C/C++ 숙련자
        - 컴퓨터 구조에 대한 깊은 이해
        """,
        "expected_role_keywords": ["Compiler", "System", "NPU", "시스템"],
        "expected_discriminator": True
    }
]

# 3. Execution & Verification
failures = []

for case in test_cases:
    print(f"\n🧪 Testing Case: {case['id']}...")
    try:
        result = analyzer.analyze(case['jd'])
        
        # A. Check Structure
        required_keys = ["inferred_role", "role_cluster", "wrong_roles", "confidence_score", "negative_signals"]
        for k in required_keys:
            if k not in result:
                failures.append(f"[{case['id']}] Missing key: {k}")
        
        # B. Check Discriminator (Critical)
        wrong_roles = result.get("wrong_roles", [])
        if not wrong_roles or len(wrong_roles) < 1:
            failures.append(f"[{case['id']}] Discriminator Failed: 'wrong_roles' is empty!")
        else:
            print(f"   ✅ Discriminator works: {wrong_roles}")

        # C. Check Inferred Role
        inferred = result.get("inferred_role", "")
        print(f"   ℹ️ Inferred Role: {inferred}")
        print(f"   ℹ️ Role Cluster: {result.get('role_cluster')}")
        
        match = any(k.lower() in inferred.lower() for k in case['expected_role_keywords'])
        if not match:
            failures.append(f"[{case['id']}] Inferred Role '{inferred}' does not match keywords {case['expected_role_keywords']}")

        # D. Check Confidence
        conf = result.get("confidence_score", 0)
        print(f"   ℹ️ Confidence: {conf}")
        if conf < 60:
            failures.append(f"[{case['id']}] Confidence too low: {conf}")

    except Exception as e:
        failures.append(f"[{case['id']}] Exception: {e}")

# 4. Final Report
print("\n" + "="*30)
if failures:
    print("❌ Verification FAILED with issues:")
    for f in failures:
        print(f" - {f}")
    sys.exit(1)
else:
    print("✅ ALL TESTS PASSED! V2 Logic Verified.")
    sys.exit(0)
