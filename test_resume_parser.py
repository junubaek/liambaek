
import json
import os
from connectors.openai_api import OpenAIClient
from resume_parser import ResumeParser

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

    # 2. Init Parser
    print("🚀 Initializing Resume Parser...")
    client = OpenAIClient(api_key)
    parser = ResumeParser(client)
    
    # 3. Test Data (Sample Resume Text)
    sample_resume = """
    John Doe
    Software Engineer
    john.doe@example.com | (555) 123-4567
    
    Summary:
    Experienced Python Developer with 6 years of expertise in building scalable backend systems.
    Proficient in Django, FastAPI, and Cloud Infrastructure.
    
    Experience:
    Senior Backend Engineer | TechCorp (2020 - Present)
    - Designed microservices architecture using FastAPI.
    - Optimized database queries reducing latency by 40%.
    - Mentored junior developers.
    
    Software Developer | StartUp Inc (2018 - 2020)
    - Developed REST APIs for mobile applications.
    - Implemented CI/CD pipelines using Jenkins.
    
    Education:
    B.S. Computer Science | University of Technology (2014 - 2018)
    
    Skills:
    Python, SQL, Docker, Kubernetes, AWS, Git
    """
    
    print(f"\n📄 Parsing Sample Resume ({len(sample_resume)} chars)...")
    print("-" * 40)
    print(sample_resume.strip())
    print("-" * 40)
    
    # 4. Run Analysis
    try:
        result = parser.parse(sample_resume)
        
        print("\n✅ Parsing Complete!")
        # Validate critical fields
        basics = result.get("basics", {})
        skills = result.get("skills", [])
        exp = result.get("work_experience", [])
        
        print(f"Name: {basics.get('name')}")
        print(f"Total Years: {basics.get('total_years_experience')}")
        print(f"Skills Extracted: {len(skills)}")
        print(f"Experience Entries: {len(exp)}")

        print("\n[Structured JSON Output]")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Error during parsing: {e}")

if __name__ == "__main__":
    main()
