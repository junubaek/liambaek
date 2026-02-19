import sys
print("Starting Test...")
try:
    import json
    import urllib.request
    print("Standard libs OK")
    
    from connectors.notion_api import NotionClient
    from connectors.pinecone_api import PineconeClient
    from connectors.openai_api import OpenAIClient
    print("Imports OK")

    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    print("Secrets loaded")

    n = NotionClient(secrets["NOTION_API_KEY"])
    p = PineconeClient(secrets["PINECONE_API_KEY"], "https://example.com")
    o = OpenAIClient(secrets["OPENAI_API_KEY"])
    print("Clients initialized")
    
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
