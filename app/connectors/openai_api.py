
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
        self.max_retries = 5

    def _request_with_retry(self, url, payload, headers):
        """
        [v1.3] Internal helper for robust OpenAI API requests with exponential backoff.
        """
        data = json.dumps(payload).encode('utf-8')
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as response:
                    return json.loads(response.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                if e.code == 429: # Too Many Requests
                    wait_time = (2 ** attempt) + 1
                    print(f"⚠️ [OpenAI 429] Rate limited. Retrying in {wait_time}s... (Attempt {attempt+1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                err_body = e.read().decode('utf-8')
                print(f"❌ [OpenAI HTTP Error] {e.code}: {err_body}")
                return None
            except Exception as e:
                print(f"❌ [OpenAI Request Error] {e}")
                return None
        return None

    def embed_content(self, text):
        """
        Generates embedding for the given text using OpenAI.
        """
        if not text: return None
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {"input": text, "model": self.model, "dimensions": self.dimensions}
        result = self._request_with_retry(self.url, payload, headers)
        if result and result.get("data"):
            return result["data"][0]["embedding"]
        return None
    def get_chat_completion(self, system_prompt, user_message):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
            "max_tokens": 2000, "temperature": 0.5
        }
        result = self._request_with_retry(url, payload, headers)
        if result and result.get("choices"):
            return result["choices"][0]["message"]["content"]
        return None

    def get_chat_completion_json(self, system_prompt, user_message=None):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        messages = [{"role": "user", "content": system_prompt}]
        if user_message:
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]

        payload = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "response_format": {"type": "json_object"},
            "max_tokens": 2000, "temperature": 0.3
        }
        result = self._request_with_retry(url, payload, headers)
        if result and result.get("choices"):
            content = result["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except:
                return None
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
