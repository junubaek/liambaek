from connectors.openai_api import OpenAIClient
from .extractor import JDExtractor
from .normalizer import JDNormalizer
from .inferencer import JDInferencer

class JDPipeline:
    def __init__(self):
        # Load secrets
        import json
        try:
            with open("secrets.json", "r") as f:
                secrets = json.load(f)
                api_key = secrets.get("OPENAI_API_KEY")
        except:
            api_key = None
            
        self.client = OpenAIClient(api_key)
        self.extractor = JDExtractor(self.client)
        self.normalizer = JDNormalizer()
        self.inferencer = JDInferencer(self.client)
        
    def parse(self, jd_text: str) -> dict:
        # Stage 1: Extract
        s1 = self.extractor.extract(jd_text)
        if not s1: s1 = {}

        
        # Stage 2: Normalize
        s2 = self.normalizer.normalize(s1)
        
        # Stage 3: Infer
        s3 = self.inferencer.infer(s2)
        
        # Merge results
        result = {**s2, **s3} 
        
        # [Fix] Propagate Failure Status from Extractor (V2)
        if s1.get("analysis_status"):
            result["analysis_status"] = s1["analysis_status"]
        if s1.get("reason"):
            result["reason"] = s1["reason"]
            
        return result
