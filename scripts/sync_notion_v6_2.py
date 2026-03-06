import json
import sqlite3
import time
import os
import sys
sys.path.append(os.getcwd())
from connectors.notion_api import NotionClient

def sync_notion_v6_2():
    print("🚀 Starting Notion v6.2 Intelligence Sync...")
    
    # Configuration
    DB_ID = "2ce22567-1b6f-80cc-a8e8-c78730a0c505"
    DB_PATH = "headhunting_engine/data/analytics.db"
    SECRETS_PATH = "secrets.json"
    
    if not os.path.exists(SECRETS_PATH):
        print("❌ secrets.json not found.")
        return

    with open(SECRETS_PATH, "r") as f:
        secrets = json.load(f)
    
    client = NotionClient(secrets["NOTION_API_KEY"])
    
    # 1. Update Database Schema (Add v6.2 Properties)
    print("🛠️ Updating Notion Database Schema...")
    new_properties = {
        "v6.2 Score": {"number": {"format": "number"}},
        "Experience Patterns": {"multi_select": {}},
        "Trajectory Grade": {"select": {}},
        "Impact Level": {"select": {}},
        "Cross-Sector Flag": {"checkbox": {}},
        "Primary Sector": {"select": {}}
    }
    client.update_database(DB_ID, new_properties)
    time.sleep(2) # Wait for schema update to propagate
    
    # 2. Clear Existing Data (RE-ENABLED BY USER REQUEST)
    print("🧹 Clearing existing data from Notion DB...")
    res = client.query_database(DB_ID)
    items = res.get('results', [])
    print(f"  -> Found {len(items)} items to archive.")
    for i, item in enumerate(items):
        client.archive_page(item['id'])
        if i % 10 == 0:
            print(f"    - Archived {i+1}/{len(items)}...")
        time.sleep(0.1) # Minimum sleep to avoid too many requests but stay active
    
    # 3. Upload v6.2 Intelligence from Local DB
    print("📤 Uploading v6.2 Intelligence from Local DB...")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Fetch only candidates with v6.2 intelligence data
        cursor.execute("SELECT notion_id, data_json FROM candidate_snapshots WHERE data_json LIKE '%v6_2_data%'")
        rows = cursor.fetchall()
        
    print(f"  -> Found {len(rows)} candidates with v6.2 data.")
    
    success_count = 0
    for notion_id, data_json in rows:
        try:
            data = json.loads(data_json)
            name = data.get("이름") or data.get("name") or "Unknown"
            v62 = data["v6_2_data"]
            profile = v62.get("candidate_profile", {})
            quality = v62.get("career_path_quality", {})
            patterns = v62.get("patterns", [])
            
            # Prepare individual properties
            pattern_names = [{"name": p["pattern"]} for p in patterns[:10]] # Safety limit
            trajectory = quality.get("trajectory_grade", "Neutral")
            
            # Calculate a sample Score (or use pre-calculated if exists)
            # For sync, we use the raw_data's score or a default
            raw_score = quality.get("career_path_score", 0)

            props = {
                "이름": {"title": [{"text": {"content": name or "Unknown"}}]},
                "Primary Sector": {"select": {"name": profile.get("primary_sector", "Unclassified")}},
                "Experience Patterns": {"multi_select": pattern_names},
                "Trajectory Grade": {"select": {"name": trajectory}},
                "Cross-Sector Flag": {"checkbox": profile.get("cross_sector_flag", False)},
                "v6.2 Score": {"number": raw_score},
                "구글드라이브 링크": {"url": data.get("구글드라이브_링크") or "https://drive.google.com"}
            }
            
            res = client.create_page(DB_ID, props)
            if res:
                success_count += 1
                print(f"  ✅ Uploaded {name} ({success_count}/{len(rows)})")
            
            time.sleep(0.5) # Rate limit protection
            
        except Exception as e:
            print(f"  ❌ Error uploading {name}: {e}")

    print(f"\n✨ Sync Complete. {success_count} candidates uploaded to Notion Hub.")

if __name__ == "__main__":
    sync_notion_v6_2()
