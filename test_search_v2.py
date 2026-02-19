
import json
import os
from matcher import search_candidates

def test_search():
    print("=== AntiGravity Search Tester (v2) ===")
    
    # Sample JD for testing (can be replaced with input)
    sample_jd = """
    We are looking for a Senior Backend Engineer with 5+ years of experience in Python and Django.
    Must have experience with AWS and Docker.
    Preferred: Knowledge of React and Kubernetes.
    Domain: Fintech or E-commerce.
    """
    
    print("\n[Input JD]")
    print(sample_jd.strip())
    print("-" * 50)
    
    try:
        results = search_candidates(sample_jd, limit=5)
        
        if results:
            print("\n[Search Results]")
            for i, res in enumerate(results):
                match = res['match']
                score = res['hybrid_score']
                meta = match['metadata']
                
                print(f"{i+1}. {meta.get('name')} | Score: {score:.2f} | Role: {meta.get('position')}")
                print(f"   Skills: {meta.get('skills')}")
                print(f"   Exp: {meta.get('total_years')} years | {meta.get('company')}")
                print("-" * 30)
        else:
            print("No results found.")
            
    except Exception as e:
        print(f"Error during search: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_search()
