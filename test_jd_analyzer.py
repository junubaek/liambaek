
import json
import os
from connectors.openai_api import OpenAIClient
from jd_analyzer import JDAnalyzer

def main():
    # 1. Load Secrets
    if not os.path.exists("secrets.json"):
        print("❌ secrets.json not found.")
        return
        
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
        
    api_key = secrets.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in secrets.")
        return

    # 2. Init Analyzer
    print("🚀 Initializing JD Analyzer...")
    client = OpenAIClient(api_key)
    analyzer = JDAnalyzer(client)
    
    # 3. Test Data
    sample_jd = """
    We are looking for a Senior Python Backend Engineer to join our Fintech team.
    You will build high-performance APIs using FastAPI and Django.
    
    Requirements:
    - 5+ years of experience in Python development.
    - Strong knowledge of AWS, Docker, and Kubernetes.
    - Experience with PostgreSQL and Redis.
    - Experience in the financial domain is a plus.
    """
    
    print(f"\n📄 Analyzing Sample JD ({len(sample_jd)} chars)...")
    print("-" * 40)
    print(sample_jd.strip())
    print("-" * 40)
    
    # 4. Run Analysis
    try:
        result = analyzer.analyze(sample_jd)
        
        print("\n✅ Analysis Complete!")
        print(f"Confidence Score: {result.get('confidence_score')}%")
        print(f"Ambiguous: {result.get('is_ambiguous')}")
        print(f"Strategy: {result.get('search_strategy', {}).get('mode', 'Unknown').upper()}")
        print("\n[Extracted Data]")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")

if __name__ == "__main__":
    main()
