
from jd_parser.pipeline import JDPipeline
import json

def test_jd_parser():
    print("Initializing JD Parser Pipeline...")
    pipeline = JDPipeline()
    
    sample_jd = """
    We are looking for a Senior Backend Engineer to join our Payment Team.
    You will be responsible for building high-performance APIs using Python and FastAPI.
    Experience with AWS and MySQL is required.
    Ideally, you have 5+ years of experience in the Fintech industry.
    Knowledge of CI/CD and Docker is a plus.
    """
    
    print("\n[Input JD]")
    print(sample_jd.strip())
    
    print("\nRunning Analysis...")
    result = pipeline.parse(sample_jd)
    
    print("\n[Analysis Result]")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_jd_parser()
