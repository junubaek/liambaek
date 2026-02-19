
import os
import streamlit as st
from connectors.pinecone_api import PineconeClient
import random

def debug_pinecone():
    print("--- 🕵️‍♂️ Pinecone Connection & Data Debugger ---")
    
    # 1. Initialize Client
    # Load Secrets
    import json
    try:
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
        api_key = secrets.get("PINECONE_API_KEY") or secrets.get("pinecone_api_key")
        host = secrets.get("PINECONE_HOST") or secrets.get("pinecone_environment") or "https://index-host" # adjustments may be needed
        
        # Adjust for PineconeClient signature
        # Check app.py for how it's used.
        # It seems app.py uses st.secrets.
        # Let's assume PineconeClient(api_key, host)
        
        if not api_key:
            print("❌ PINECONE_API_KEY not found in secrets.json")
            return
            
        pc = PineconeClient(api_key=api_key, host=host)
        print("✅ PineconeClient initialized with keys from secrets.json.")
    except Exception as e:
        print(f"❌ Failed to load secrets or initialize: {e}")
        return

    # 2. Check Index Stats
    try:
        # Access the underlying index object if possible, or use the client method if available
        # Looking at previous files, pc.index seems to be the way, or pc.pc.Index(...)
        # Let's try to access the index directly.
        if hasattr(pc, 'index'):
            stats = pc.index.describe_index_stats()
            print(f"\n📊 Index Stats:\n{stats}")
        else:
            print("⚠️ 'index' attribute not found on PineconeClient.")
            # Try to query to see if it works implies connection
    except Exception as e:
        print(f"❌ Failed to fetch index stats: {e}")

    # 3. Test Vector Search (Dummy Vector)
    print("\n🧪 Testing Vector Search with Random Vector...")
    dummy_vec = [random.random() for _ in range(1536)] # Assume 1536 dim
    
    namespaces_to_test = ["", None, "resumes", "avengers"] # Commonly used namespaces
    
    for ns in namespaces_to_test:
        print(f"\nQUERYING Namespace: '{ns}'")
        try:
            # Note: PineconeClient.query might wrap the verify logic, let's use the index directly if possible
            # or use the wrapper method.
            # Wrapper: query(self, vector, top_k=10, filter_meta=None, namespace="ns1")
            # It internally sets includeMetadata=True
            
            results = pc.query(
                vector=dummy_vec,
                top_k=5,
                namespace=ns
            )
            
            # Check results structure
            if results and 'matches' in results:
                count = len(results['matches'])
                print(f"  👉 Found {count} matches.")
                if count > 0:
                    print(f"  ✅ SUCCESS! First match ID: {results['matches'][0]['id']}")
            else:
                print(f"  ⚠️ No 'matches' key in response or empty: {results}")
                
        except Exception as e:
            print(f"  ❌ Query Failed for namespace '{ns}': {e}")

if __name__ == "__main__":
    # Mock Streamlit Secrets if needed (for local run)
    # in this environment, we rely on the system already having keys or the class handling it.
    debug_pinecone()
