import sys
import os
import json
from connectors.openai_api import OpenAIClient
from jd_parser.pipeline import JDPipeline
from jd_parser.extractor import JDExtractor
from jd_analyzer import JDAnalyzer
from jd_analyzer_v2 import JDAnalyzerV2

# 1. Load Secrets
try:
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
        api_key = secrets.get("OPENAI_API_KEY")
    print(f"DEBUG: API Key Loaded: {'Yes' if api_key else 'No'}")
except Exception as e:
    print(f"DEBUG: Failed to load secrets: {e}")
    api_key = None

# 2. Mimic App.py Patching Logic
print("\n--- Applying Patch Logic ---")
pipeline = JDPipeline()
# Inject Key if missing
if not pipeline.client.api_key and api_key:
    pipeline.client.api_key = api_key
    print("DEBUG: Injected API Key into Pipeline Client")

# Initialize Analyzers
analyzer_instance = JDAnalyzer(pipeline.client)
analyzer_instance_v2 = JDAnalyzerV2(pipeline.client)

# Mock JD Content (Exact User Case)
mock_jd_text = """
[Job Title]
Product Owner (Fintech)

[Requirements]
- 고객 중심 사고, 프로젝트 관리, 협업 경험, 문제 해결 능력

[Preferred]
- 정보보안 지식, 보험 산업 이해, 데이터 분석 능력

[Context]
- 스타트업 마인드셋을 가진 분
- 신속한 실행력
- 고객 경험 개선에 대한 열정
"""

print("\n--- Starting Test Parse (V2 Explicit Call) ---")
try:
    # Directly test V2 first to see raw output
    v2_result = analyzer_instance_v2.analyze(mock_jd_text)
    print("\n[V2 Raw Output]")
    print(json.dumps(v2_result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"\n[V2 Exception] {e}")

print("\n--- Starting Test Parse (Pipeline Integration) ---")
# Patch Extractor to use V2 for this test
def test_extract_v2(self, text):
    return analyzer_instance_v2.analyze(text)

JDExtractor.extract = test_extract_v2
print("DEBUG: JDExtractor patched to use V2")

pipeline_result = pipeline.parse(mock_jd_text)
print("\n[Pipeline Output]")
print(json.dumps(pipeline_result, indent=2, ensure_ascii=False))


# Check data structure for App.py
print("\n--- App.py Compatibility Check ---")
raw = pipeline_result.get("raw_extracted", {})
domain_check = pipeline_result.get("domains")
print(f"raw_extracted present: {bool(raw)}")
print(f"domains type: {type(domain_check)} -> {domain_check}")
print(f"analysis_status: {pipeline_result.get('analysis_status')}")


print("\n--- Verification Output (Critical Fields from RAW) ---")
raw = pipeline_result.get("raw_extracted", {})
print(f"Inferred Role: {raw.get('inferred_role')}")
print(f"Primary Role: {raw.get('primary_role')}")
print(f"Must Skills: {raw.get('must_skills')}")
print(f"Nice Skills: {raw.get('nice_skills')}")


print(f"Negative Signals: {raw.get('negative_signals')}")
print(f"Search Contract: {json.dumps(raw.get('search_contract'), indent=2, ensure_ascii=False)}")
print(f"Confidence: {raw.get('confidence_score')}")

print("\n--- Testing Search Pipeline Filtering (Stage 2 & 3) ---")
from search_pipeline import SearchPipeline
from unittest.mock import MagicMock

# Mock Clients
mock_pc = MagicMock()
mock_ai = MagicMock()

# Mock Candidates
mock_candidates = [
    {
        "id": "cand_1", 
        "score": 0.9, 
        "metadata": {
            "title": "Senior Service Planner", 
            "role_cluster": "Planning", 
            "total_years": 7, 
            "summary": "Expert in Service Planning and JIRA. Insurance domain experience.",
            "skills": ["Service Planning", "JIRA", "SQL"]
        }
    },
    {
        "id": "cand_2", 
        "score": 0.85, 
        "metadata": {
            "title": "Junior Developer", 
            "role_cluster": "Engineering", 
            "total_years": 1, 
            "summary": "React developer.",
            "skills": ["React"]
        }
    },
    {
        "id": "cand_3", 
        "score": 0.88, 
        "metadata": {
            "title": "Marketing Manager", 
            "role_cluster": "Marketing", 
            "total_years": 5, 
            "summary": "Marketing expert.",
            "skills": ["Marketing"]
        }
    }
]

# Mock Pinecone Query Response
mock_pc.query.return_value = {
    'matches': mock_candidates
}

# Initialize Pipeline
sp = SearchPipeline(mock_pc, mock_ai)

# Prepare Context from Analysis Result
# Ensure raw_extracted has search_contract
ctx = pipeline_result.copy()
if "search_contract" not in ctx and "raw_extracted" in ctx:
    ctx["search_contract"] = ctx["raw_extracted"].get("search_contract")
    ctx["negative_signals"] = ctx["raw_extracted"].get("negative_signals")

# Inject explicit negative signal for test if not present
if not ctx.get("negative_signals"):
    print("DEBUG: Injecting 'Marketing' as negative signal for testing")
    if not ctx.get("search_contract"): ctx["search_contract"] = {}
    ctx["search_contract"]["negative_signals"] = ["Marketing"]

# Run Pipeline
filtered_results, logs = sp.run(ctx, "test query", top_k=3)

print("\n[Filtered Results]")
for c in filtered_results:
    print(f"- {c['id']} ({c['data']['title']}) Score: {c.get('matrix_score')} Reasons: {c.get('matrix_reasons')}")

print("\n[Pipeline Logs]")
for log in logs:
    print(log)

print("------------------------------------------------")
