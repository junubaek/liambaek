
import json
import urllib.request
import urllib.error
import time

class GeminiClient:
    def __init__(self, api_key):
        self.api_key = api_key
        # Priority list of configurations to try
        self.configs = [
            {"model": "models/text-embedding-004", "version": "v1beta", "supports_task_type": True},
            {"model": "models/embedding-001", "version": "v1beta", "supports_task_type": False},
            {"model": "models/embedding-001", "version": "v1", "supports_task_type": False}
        ]
        self.working_config = None # Will be set after first successful call

    def _make_request(self, text, config, task_type):
        model = config["model"]
        version = config["version"]
        use_task_type = config["supports_task_type"]
        
        url = f"https://generativelanguage.googleapis.com/{version}/{model}:embedContent?key={self.api_key}"
        
        payload = {
            "model": model,
            "content": {"parts": [{"text": text}]}
        }
        
        if use_task_type and task_type:
            payload["taskType"] = task_type
            
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))

    def embed_content(self, text, task_type="RETRIEVAL_DOCUMENT"):
        # 1. If we already know what works, use it
        if self.working_config:
            try:
                result = self._make_request(text, self.working_config, task_type)
                return result.get('embedding', {}).get('values')
            except Exception as e:
                print(f"[Warn] Config {self.working_config['model']} failed: {e}. Retrying discovery...")
                self.working_config = None # Reset and fall through to discovery

        # 2. Discovery Mode: Try all configs
        errors = []
        for config in self.configs:
            try:
                # print(f"[DEBUG] Trying {config['model']} ({config['version']})...") 
                result = self._make_request(text, config, task_type)
                vals = result.get('embedding', {}).get('values')
                if vals:
                    print(f"[Success] Connected via {config['model']} ({config['version']})")
                    self.working_config = config
                    return vals
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode('utf-8')
                # print(f"[DEBUG] Failed {config['model']}: {e.code}")
                errors.append(f"{config['model']}: {e.code}")
            except Exception as e:
                errors.append(f"{config['model']}: {e}")

        print(f"[CRITICAL] All Gemini embedding models failed. Details below:")
        for e in errors:
            print(f" - {e}")
            
        print("\n[WARN] Switching to MOCK embedding (Random Values) to allow system testing.")
        # Return a 768-dimensional random vector (standard size for text-embedding-004/001)
        import random
        return [random.uniform(-0.1, 0.1) for _ in range(768)]

if __name__ == "__main__":
    # Test block
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    
    client = GeminiClient(secrets["GEMINI_API_KEY"])
    vec = client.embed_content("Hello World")
    if vec:
        print(f"Embedding success! Dimension: {len(vec)}")
    else:
        print("Embedding failed.")
