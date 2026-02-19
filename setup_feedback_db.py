import json
from connectors.notion_api import NotionClient

def setup_feedback_db():
    print("🚀 Setting up Notion Feedback Database...")
    
    # 1. Load Secrets
    try:
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
            token = secrets["NOTION_API_KEY"]
            parent_page_id = secrets.get("NOTION_PAGE_ID") # Optional, or we search for a parent
            
            # If no parent page ID, we can't create a DB easily via API without searching.
            # But we can try to find a page named "Antigravity" or similar.
            pass
    except Exception as e:
        print(f"❌ Error loading secrets.json: {e}")
        return

    client = NotionClient(token)
    
    # 2. Search for existing "Antigravity Feedback" DB
    print("🔍 Searching for existing 'Antigravity Feedback' database...")
    existing_db_id = client.search_db_by_name("Antigravity Feedback")
    
    if existing_db_id:
        print(f"✅ Found existing database! ID: {existing_db_id}")
        print("\n👉 Add this to your secrets.json:")
        print(f'   "NOTION_FEEDBACK_DB_ID": "{existing_db_id}"')
        return

    # 3. Create New DB (Requires a Parent Page)
    # Since we might not have a parent page ID, we will ask the user or try to find "Teamspace" or "Home"
    # Actually, the easiest way is to ask the user to provide a Parent Page ID in secrets or input.
    
    print("\n⚠️ To create a new database, we need a Parent Page ID.")
    parent_id = input("Enter the Page ID where you want to create the DB (or press Enter to search for 'Antigravity'): ").strip()
    
    if not parent_id:
        # Try to find a root page named 'Antigravity'
        parent_id = client.search_db_by_name("Antigravity") # This searches DBs, but create_page needs parent PAGE.
        # Notion API is tricky here. existing client.search_db_by_name uses "filter": {"value": "database"}
        # We need to search for a page.
        
        # Let's manual search
        print("  Using search to find a page named 'Antigravity'...")
        payload = {
             "query": "Antigravity",
             "filter": {"value": "page", "property": "object"}
        }
        res = client._request("POST", "search", payload)
        if res and res.get("results"):
            parent_id = res["results"][0]["id"]
            print(f"  Found page: {res['results'][0]['url']}")
        else:
            print("❌ Could not find a parent page. Please create an empty page named 'Antigravity' in Notion and try again.")
            return

    # 4. Create Database
    # Since NotionClient doesn't have create_database, we implement it here raw or add to client.
    # We will use raw _request
    print(f"🛠️ Creating 'Antigravity Feedback' database under page {parent_id}...")
    
    payload = {
        "parent": {"type": "page_id", "page_id": parent_id},
        "title": [{"type": "text", "text": {"content": "Antigravity Feedback"}}],
        "properties": {
            "Candidate": {"title": {}},
            "Type": {"select": {
                "options": [
                    {"name": "positive", "color": "green"},
                    {"name": "negative", "color": "red"}
                ]
            }},
            "Reason": {"rich_text": {}},
            "Context Hash": {"rich_text": {}},
            "Timestamp": {"rich_text": {}},
            "Candidate ID": {"rich_text": {}}
        }
    }
    
    res = client._request("POST", "databases", payload)
    
    if res and res.get("id"):
        new_db_id = res["id"]
        print(f"\n🎉 Database Created Successfully!")
        print(f"URL: {res.get('url')}")
        print(f"\n👉 Add this to your secrets.json:")
        print(f'   "NOTION_FEEDBACK_DB_ID": "{new_db_id}"')
    else:
        print("❌ Failed to create database.")
        print(res)

if __name__ == "__main__":
    setup_feedback_db()
