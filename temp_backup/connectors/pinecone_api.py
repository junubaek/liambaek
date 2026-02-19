
import json
import urllib.request
import urllib.error

class PineconeClient:
    def __init__(self, api_key, host):
        self.api_key = api_key
        self.host = host
        self.headers = {
            "Api-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def upsert(self, vectors, namespace="ns1"):
        """
        Upserts vectors to Pinecone.
        vectors: List of dicts [{'id': 'id1', 'values': [0.1, ...], 'metadata': {...}}]
        """
        url = f"{self.host}/vectors/upsert"
        
        payload = {
            "vectors": vectors,
            "namespace": namespace
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=self.headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(f"Pinecone Upsert Error {e.code}: {e.read().decode('utf-8')}")
            return None

    def query(self, vector, top_k=10, filter_meta=None, namespace="ns1"):
        """
        Queries the index.
        """
        url = f"{self.host}/query"
        
        payload = {
            "vector": vector,
            "topK": top_k,
            "includeMetadata": True,
            "namespace": namespace
        }
        
        if filter_meta:
            payload["filter"] = filter_meta
            
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=self.headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(f"Pinecone Query Error {e.code}: {e.read().decode('utf-8')}")
            return None

    def fetch(self, ids, namespace="ns1"):
        """
        Fetches vectors by ID.
        """
        url = f"{self.host}/vectors/fetch?ids={','.join(ids)}&namespace={namespace}"
        
        req = urllib.request.Request(url, headers=self.headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(f"Pinecone Fetch Error {e.code}: {e.read().decode('utf-8')}")
            return None

    def delete(self, ids=None, delete_all=False, namespace="ns1"):
        """
        Deletes vectors by ID or Delete All.
        """
        url = f"{self.host}/vectors/delete"
        
        payload = {"namespace": namespace}
        if delete_all:
            payload["deleteAll"] = True
        elif ids:
            payload["ids"] = ids
        else:
            return None
            
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=self.headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(f"Pinecone Delete Error {e.code}: {e.read().decode('utf-8')}")
            return None

if __name__ == "__main__":
    # Test block
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    
    # Ensure host URL doesn't have trailing slash
    host = secrets.get("PINECONE_HOST", "").rstrip("/")
    if not host.startswith("https://"):
        host = f"https://{host}"
        
    client = PineconeClient(secrets["PINECONE_API_KEY"], host)
    
    # Check stats (describe_index_stats is different endpoint, skipping for now)
    # Just try a dummy query with zero vector if we knew dimension
    pass
