import json
from connectors.notion_api import NotionClient

def find_db():
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    
    client = NotionClient(secrets["NOTION_API_KEY"])
    page_id = "2ce225671b6f80848f00f20994eae35e"
    
    # Check page children for databases
    res = client._request("GET", f"blocks/{page_id}/children")
    if res:
        print("Page Blocks:")
        for block in res.get('results', []):
            print(f" - Type: {block['type']}, ID: {block['id']}")
            if block['type'] == 'child_database':
                print(f"!!! FOUND DATABASE: {block['child_database']['title']} (ID: {block['id']})")
    else:
        print("Failed to fetch page blocks.")

if __name__ == "__main__":
    find_db()
