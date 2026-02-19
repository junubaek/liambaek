

import json
from connectors.pinecone_api import PineconeClient
from connectors.openai_api import OpenAIClient

def check_pinecone():
    try:
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
        
        # 1. Setup Pinecone
        pc_host = secrets.get("PINECONE_HOST", "")
        if not pc_host.startswith("https://"): pc_host = f"https://{pc_host}"
        pc = PineconeClient(secrets["PINECONE_API_KEY"], pc_host)
        
        # 2. Setup OpenAI
        openai = OpenAIClient(secrets["OPENAI_API_KEY"])
        
        print(f"Connecting to Host: {pc_host}")
        
        # 3. Real Semantic Query
        query_text = "AI Cloud Engineer Kubernetes Python Go"
        print(f"\n--- Embedding Query: '{query_text}' ---")
        
        query_vec = openai.embed_content(query_text)
        if not query_vec:
            print("❌ Failed to generate embedding.")
            return

        print(f"✅ Generated Vector (Dim: {len(query_vec)})")
        
        # 4. Search Pinecone
        print("\n--- Searching Top 20 Candidates ---")
        res = pc.query(vector=query_vec, top_k=20, namespace="ns1")
        
        if res and 'matches' in res:
            matches = res['matches']
            print(f"Found {len(matches)} matches.")
            
            for i, m in enumerate(matches):
                meta = m.get('metadata', {})
                name = meta.get('name', 'N/A')
                role = meta.get('role', 'N/A')
                score = m['score']
                print(f"[{i+1}] {name} | Role: {role} | Score: {score:.4f}")
        else:
            print("❌ Query returned None or invalid response.")
            print(res)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_pinecone()
