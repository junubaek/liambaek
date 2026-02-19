
import json
import urllib.request
import urllib.error

def check_stats():
    print("--- 📊 Pinecone Index Stats Checker ---")
    
    # Load Secrets
    try:
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
        api_key = secrets.get("PINECONE_API_KEY")
        host = secrets.get("PINECONE_HOST")
        
        if not api_key or not host:
            print("❌ Secrets missing API Key or Host")
            return

        print(f"URL: {host}/describe_index_stats")
        
        url = f"{host}/describe_index_stats"
        headers = {
            "Api-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        req = urllib.request.Request(url, method="POST", headers=headers) # Stats is usually POST or GET? Logic says POST for pinecone
        # Pinecone API Ref: GET /describe_index_stats if using the legacy controller, but data plane is POST?
        # Actually it's usually POST /describe_index_stats for serverless/pod index data plane.
        # Let's try POST with empty body.
        
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                print("\n✅ Stats Response:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
        except urllib.error.HTTPError as e:
            print(f"❌ HTTP Error {e.code}: {e.read().decode('utf-8')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_stats()
