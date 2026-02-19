
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path to allow imports from subdirectories
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from connectors.pinecone_api import PineconeClient
    from connectors.openai_api import OpenAIConnector
except ImportError as e:
    print(f"Import Error: {e}")
    # Try importing directly if package structure is different
    try:
        sys.path.append(os.path.join(os.getcwd(), 'connectors'))
        from pinecone_api import PineconeClient
        from openai_api import OpenAIConnector
    except ImportError as e2:
         print(f"Critical Import Error: {e2}")
         sys.exit(1)

def debug_pinecone():
    print("--- 🌲 Pinecone Connection Debugger ---", flush=True)
    
    # 1. Initialize Connector
    try:
        api_key = os.getenv("PINECONE_API_KEY")
        host = os.getenv("PINECONE_HOST") 
        
        if not api_key:
            print("❌ Error: PINECONE_API_KEY not found in .env", flush=True)
            return
            
        print(f"✅ API Key found: {api_key[:5]}...", flush=True)
        print(f"✅ Host: {host}", flush=True)
        
        pc = PineconeClient(api_key, host)
        print("✅ PineconeClient initialized.", flush=True)
    except Exception as e:
        print(f"❌ Failed to initialize PineconeClient: {e}", flush=True)
        return

    print("ℹ️ Custom Client detected. Skipping stats check.", flush=True)

    # 3. Test Vector Search (Raw)
    print("\n🔍 Testing Raw Vector Search...", flush=True)
    try:
        # Generate a dummy embedding
        print("   Initializing OpenAI...", flush=True)
        openai = OpenAIConnector()
        test_query = "Software Engineer Python"
        print(f"   Querying OpenAI for embedding: '{test_query}'...", flush=True)
        
        # Add timeout/error handling for OpenAI
        try:
             vector = openai.embed_content(test_query)
        except Exception as oe:
             print(f"❌ OpenAI Error: {oe}", flush=True)
             return

        if not vector:
             print("❌ Failed to get embedding from OpenAI.", flush=True)
             return
             
        print(f"   Generated embedding (len={len(vector)}). Sending query to Pinecone...", flush=True)
        
        # Query
        results = pc.query(
            vector=vector,
            top_k=5,
            namespace="" 
        )
        
        if not results:
             print("❌ Query failed or returned broken response.", flush=True)
             try:
                 print("   Retrying with namespace 'ns1'...", flush=True)
                 results = pc.query(vector=vector, top_k=5, namespace="ns1")
             except: pass
        
        matches = results.get('matches', [])
        print(f"✅ Check complete. Found {len(matches)} matches.", flush=True)
        
        for i, m in enumerate(matches):
            print(f"   [{i+1}] Score: {m['score']:.4f} | ID: {m['id']} | Metadata Name: {m['metadata'].get('name', 'N/A')}", flush=True)

    except Exception as e:
        print(f"❌ Search Test Failed: {e}", flush=True)

if __name__ == "__main__":
    debug_pinecone()
