
import json
import urllib.request
import urllib.error
import time

class OpenAIClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.openai.com/v1/embeddings"
        self.model = "text-embedding-3-small"
        # CRITICAL: Match Pinecone's 768 dimension (User's current setup)
        # Default for 3-small is 1536, but it supports shortening.
        self.dimensions = 768 

    def embed_content(self, text):
        """
        Generates embedding for the given text using OpenAI.
        Returns a list of floats (vector).
        """
        if not text:
            return None
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # OpenAI API Payload
        payload = {
            "input": text,
            "model": self.model,
            "dimensions": self.dimensions
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(self.url, data=data, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                # Extract embedding values from first element
                if result.get("data"):
                    return result["data"][0]["embedding"]
                return None
                
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8')
            print(f"[OpenAI API Error] {e.code}: {err_body}")
            return None
    def get_chat_completion(self, system_prompt, user_message):
        """
        Generates a chat completion using OpenAI.
        Useful for generating reasons/summaries.
        """
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "gpt-4o-mini", # Fast and cheap
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 2000,
            "temperature": 0.5
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get("choices"):
                    return result["choices"][0]["message"]["content"]
                return None
        except Exception as e:
            print(f"[OpenAI Chat Error] {e}")
            return None

    def get_chat_completion_json(self, system_prompt, user_message=None):
        """
        Generates a chat completion forcing JSON output.
        Handles both single prompt (in system_prompt) or system+user.
        """
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Helper: If user_message is None, treat system_prompt as the main instruction
        messages = []
        if user_message:
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_message})
        else:
            messages.append({"role": "user", "content": system_prompt})

        payload = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "response_format": {"type": "json_object"},  # Force JSON
            "max_tokens": 2000,
            "temperature": 0.3
        }
        
        data = json.dumps(payload).encode('utf-8')
        import urllib.request
        req = urllib.request.Request(url, data=data, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get("choices"):
                    content = result["choices"][0]["message"]["content"]
                    return json.loads(content) # Return parsed dict
                return None
        except Exception as e:
            print(f"[OpenAI JSON Error] {e}")
            return None

if __name__ == "__main__":
    # Test block
    try:
        with open("../secrets.json", "r") as f:
            secrets = json.load(f)
        client = OpenAIClient(secrets["OPENAI_API_KEY"])
        vec = client.embed_content("Hello OpenAI")
        if vec:
            print(f"Success! Vector Dim: {len(vec)}")
        else:
            print("Failed.")
    except Exception as e:
        print(f"Test failed: {e}")
