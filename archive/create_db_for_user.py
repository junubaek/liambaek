
from connectors.notion_api import HeadhunterDB
import json
import sys

def create_db():
    db = HeadhunterDB()
    client = db.client
    
    # 1. Get Parent Page ID from secrets (which currently holds the Page ID)
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
        
    parent_page_id = secrets.get("NOTION_DATABASE_ID")
    print(f"Target Parent Page: {parent_page_id}")
    
    # 2. Define Database Schema
    payload = {
        "parent": { "type": "page_id", "page_id": parent_page_id },
        "title": [ { "type": "text", "text": { "content": "Resume DB (Auto-Created)" } } ],
        "properties": {
            "이름": { "title": {} },
            "포지션": { "select": {} },
            "Domain": { "select": {} },
            "구글드라이브 링크": { "url": {} }
        }
    }

    # 3. Create Database
    print("Creating Database...")
    res = client._request("POST", "databases", payload)
    
    if res and res.get("id"):
        new_db_id = res["id"]
        print(f"SUCCESS: Created Database! ID: {new_db_id}")
        print(f"URL: {res.get('url')}")
        
        # 4. Update secrets.json
        secrets["NOTION_DATABASE_ID"] = new_db_id
        
        with open("secrets.json", "w") as f:
            json.dump(secrets, f, indent=4)
            
        print("Updated secrets.json with new DB ID.")
    else:
        print("Failed to create database. Check permissions (is 'Make_Resume' invited?).")

if __name__ == "__main__":
    create_db()
