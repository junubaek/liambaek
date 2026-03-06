import json
from connectors.notion_api import NotionClient

def inspect_db():
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    
    client = NotionClient(secrets["NOTION_API_KEY"])
    db_id = "2ce225671b6f80848f00f20994eae35e"
    
    db = client._request("GET", f"databases/{db_id}")
    if db:
        print(f"Database Title: {db.get('title', [{}])[0].get('plain_text', 'Unknown')}")
        print("\nProperties:")
        for name, prop in db.get('properties', {}).items():
            print(f" - {name}: {prop['type']}")
    else:
        print("Failed to fetch database information.")

if __name__ == "__main__":
    inspect_db()
