
import os
import json
import urllib.request
from connectors.notion_api import HeadhunterDB

def inspect_candidate(name_query):
    print(f"--- Inspecting Candidate: {name_query} ---")
    
    try:
        # Initialize helper just to get secrets
        db = HeadhunterDB()
        token = db.secrets["NOTION_API_KEY"]
        
        # Manually find DB ID (bypass helper issues)
        # We know the DB ID is likely the one in secrets.json or we can search
        db_id = db.client.search_db_by_name("Vector DB")
        if not db_id:
             db_id = db.client.search_db_by_name("DB")
        
        if not db_id:
            print("DB ID not found via search. Using secrets fallback if avail.")
            db_id = db.secrets.get("NOTION_DATABASE_ID")
        
        print(f"Target DB ID: {db_id}")

        # Direct API Call
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        payload = {
            "filter": {
                "property": "이름",
                "title": {
                    "contains": name_query
                }
            }
        }
        
        url = f"https://api.notion.com/v1/databases/{db_id}/query"
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode('utf-8'))
            results = res.get('results', [])
            print(f"\n[Notion] Found {len(results)} matches.")
            
            for page in results:
                props = page.get('properties', {})
                # Name
                title_list = props.get('이름', {}).get('title', [])
                name = title_list[0]['plain_text'] if title_list else "Unknown"
                
                # Check for URL
                page_url = page.get('url') # Standard Notion Link
                
                # Check for ANY property that might hold the external link?
                # Usually we don't store the link in a property, we store the file in valid pages.
                
                print(f" - ID: {page['id']}")
                print(f"   Name: {name}")
                print(f"   Notion Link: {page_url}")
                print(f"   Created Time: {page.get('created_time')}")
                
                # Check children count or content?
                has_content = "Unknown"
                # blocks_url = f"https://api.notion.com/v1/blocks/{page['id']}/children?page_size=1"
                # ... skip for now
                
    except Exception as e:
        print(f"[Error] {e}")

    # ---------------------------------------------------------
    # 2. Check Pinecone
    # ---------------------------------------------------------
    print("\n--- Checking Pinecone ---")
    try:
        from connectors.pinecone_api import PineconeClient
        from connectors.openai_api import OpenAIClient
        
        pc_key = db.secrets.get("PINECONE_API_KEY")
        pc_host = db.secrets.get("PINECONE_HOST")
        
        pc = PineconeClient(api_key=pc_key, host=pc_host)
        
        openai_key = db.secrets.get("OPENAI_API_KEY")
        openai = OpenAIClient(api_key=openai_key)
        
        # specific filter if possible, or just vector search
        # Pinecone free tier might not support metadata filtering fully without vector?
        # Let's try vector search with the name
        
        print(f"Generating embedding for: {name_query}")
        vector = openai.embed_content(name_query)
        if vector:
            print(f"Vector generated. Querying Pinecone...")
            
            # Manual Query since PineconeClient might lack it
            url = f"{pc.host}/query"
            payload = {
                "vector": vector,
                "topK": 10,
                "includeMetadata": True,
                "namespace": "ns1" # Default namespace
            }
            
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=pc.headers, method="POST")
            
            with urllib.request.urlopen(req) as response:
                res = json.loads(response.read().decode('utf-8'))
                matches = res.get('matches', [])
            
            print(f"[Pinecone] Found {len(matches)} matches (Top-K).")
            
            for m in matches:
                mid = m['id']
                mname = m['metadata'].get('name', 'Unknown')
                murl = m['metadata'].get('url', 'None')
                print(f" - Vector ID: {mid}")
                print(f"   Name: {mname}")
                print(f"   URL: {murl}")
                print(f"   Score: {m['score']}")
                
                if name_query in mname:
                     print("   [!] Possible Match/Duplicate")
        else:
             print("[Error] Failed to generate embedding.")
                
                # Check consistency
                # If Notion found 1 ID, and this ID is different, it's stale.
                # Note: Notion ID usually IS the Vector ID in our pipeline.
    except Exception as e:
        print(f"[Pinecone Error] {e}")

if __name__ == "__main__":
    # Use full name to improve match probability
    inspect_candidate("오동현(온라인비지니스TFT)부문_원본")
