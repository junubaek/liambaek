
import json
import os
from connectors.pinecone_api import PineconeClient

def main():
    if not os.path.exists("secrets.json"):
        print("❌ secrets.json not found.")
        return
        
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
        
    pc_host = secrets.get("PINECONE_HOST", "")
    if not pc_host.startswith("https://"):
        pc_host = f"https://{pc_host}"
        
    client = PineconeClient(secrets["PINECONE_API_KEY"], pc_host)
    
    print("⚠️ WARNING: This will DELETE ALL VECTORS from the Pinecone Index.")
    confirm = input("Type 'DELETE' to confirm: ")
    
    if confirm == "DELETE":
        try:
            # Pinecone delete_all=True
            client.index.delete(delete_all=True)
            print("✅ Index Cleared.")
        except Exception as e:
            print(f"Error clearing index: {e}")
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    main()
