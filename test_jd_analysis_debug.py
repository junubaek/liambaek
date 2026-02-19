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

def safe_extract_full(extractor_self, jd_text: str) -> dict:
    print("DEBUG: Inside patched 'safe_extract_full'")
    try:
        # Toggle test: V1 by default
        use_v2 = False 
        # You can change this to True to test V2
        
        if use_v2:
            print("DEBUG: Delegating to JDAnalyzerV2")
            return analyzer_instance_v2.analyze(jd_text)
        else:
            print("DEBUG: Delegating to JDAnalyzer (V1)")
            return analyzer_instance.analyze(jd_text)
    except Exception as e:
        print(f"DEBUG: Analyzer Error: {e}")
        return {}

# Apply Patch
JDExtractor.extract = safe_extract_full
print("DEBUG: JDExtractor.extract patched.")

# 3. Test Execution
jd_text = """
We are looking for a Product Manager for our fintech platform.
Responsibilities:
- Define product roadmap
- Work with engineering team
- Analyze user data (SQL)
Requirements:
- 3+ years experience
- Fintech background preferred
"""

print("\n--- Starting Test Parse ---")
result = pipeline.parse(jd_text)

print("\n--- Result ---")
print(json.dumps(result, indent=2, ensure_ascii=False))

if not result or result == {}:
    print("\n[FAILURE] Result is empty.")
else:
    print("\n[SUCCESS] Result is not empty.")
