import os
import sqlite3
import json
import time
import sys
import requests

# Load Secrets
with open("c:/Users/cazam/Downloads/안티그래비티/secrets.json", "r") as f:
    secrets = json.load(f)

NOTION_TOKEN = secrets["NOTION_API_KEY"]
DATABASE_ID = "31a22567-1b6f-8177-86da-ff626bb1e66c"
DB_PATH = "c:/Users/cazam/Downloads/안티그래비티/headhunting_engine/data/analytics.db"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_hub_page_ids():
    """Fetch all page IDs from the active Notion Hub."""
    page_ids = set()
    has_more = True
    next_cursor = None
    while has_more:
        payload = {"page_size": 100}
        if next_cursor: payload["start_cursor"] = next_cursor
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        resp = requests.post(url, headers=HEADERS, json=payload).json()
        for p in resp.get('results', []):
            page_ids.add(p['id'].replace("-", ""))
        has_more = resp.get('has_more', False)
        next_cursor = resp.get('next_cursor')
        print(f"Fetched {len(page_ids)} pages from Hub...")
    return page_ids

def purge_old_ids(correct_ids):
    """NULLify notion_id in SQLite if it's not in the active Hub."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, notion_id FROM candidate_snapshots WHERE notion_id IS NOT NULL")
    records = cursor.fetchall()
    
    count = 0
    for rid, nid in records:
        clean_nid = nid.replace("-", "")
        if clean_nid not in correct_ids:
            cursor.execute("UPDATE candidate_snapshots SET notion_id = NULL WHERE id = ?", (rid,))
            count += 1
    
    conn.commit()
    conn.close()
    print(f"🧹 Purged {count} stale Notion IDs from SQLite.")

def run_recovery():
    print("🚀 Starting Notion Sync Recovery (v6.2.4)...")
    
    # 1. Update Schema in Notion
    print("🛠️ Updating Notion Schema: Adding '경력 Summary' & '구글드라이브 링크' & Optimizing 'Primary Sector'...")
    schema_update = {
        "경력 Summary": {"rich_text": {}},
        "구글드라이브 링크": {"url": {}},
        "Primary Sector": {"multi_select": {}},
        "Experience Patterns": {"rich_text": {}}
    }
    resp = requests.patch(f"https://api.notion.com/v1/databases/{DATABASE_ID}", headers=HEADERS, json={"properties": schema_update})
    if resp.status_code != 200:
        print(f"  ❌ Schema Update Failed: {resp.text}")
        return

    # 2. Reconcile IDs
    hub_ids = get_hub_page_ids()
    purge_old_ids(hub_ids)

    # 3. Identify Candidates needing Update or Creation
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Query: Missing from Notion OR Missing v6.2.4 Summary in local DB
    cursor.execute("""
        SELECT id, name, data_json, notion_id 
        FROM candidate_snapshots 
        WHERE notion_id IS NULL 
           OR data_json NOT LIKE '%experience_summary%'
           OR data_json NOT LIKE '%drive_link%'
    """)
    missing = cursor.fetchall()
    print(f"🔍 Identified {len(missing)} candidates needing sync/upgrade.")

    # 4. Sync with Forced Re-Parsing & GDrive Upload
    sys.path.append("c:/Users/cazam/Downloads/안티그래비티")
    from connectors.notion_api import NotionClient
    from resume_parser import ResumeParser
    from connectors.openai_api import OpenAIClient
    from connectors.gdrive_api import GDriveConnector
    from unified_rebuild_and_sync import extract_text, GDRIVE_FOLDER_ID

    # Rebuild file_map for recovery (name -> path)
    DIR_RAW = r"C:\Users\cazam\Downloads\02_resume 전처리"
    DIR_CONV = r"C:\Users\cazam\Downloads\02_resume_converted_docx"
    file_map = {}
    for f in os.listdir(DIR_RAW):
        if f.lower().endswith(('.pdf', '.docx')) and not f.startswith("~$"):
            file_map[os.path.splitext(f)[0]] = os.path.join(DIR_RAW, f)
    for f in os.listdir(DIR_CONV):
        if f.lower().endswith(('.docx')) and not f.startswith("~$"):
            file_map[os.path.splitext(f)[0]] = os.path.join(DIR_CONV, f)

    parser = ResumeParser(OpenAIClient(secrets["OPENAI_API_KEY"]))
    nc = NotionClient(NOTION_TOKEN)
    gdrive = GDriveConnector()

    for i, (rid, name, djson, nid) in enumerate(missing):
        try:
            data = json.loads(djson)
            profile = data.get("candidate_profile", {})
            
            # [v6.2.4 Forced Intelligence Update]
            # If summary is missing, re-parse from file
            if "experience_summary" not in profile:
                print(f"[{i+1}/{len(missing)}] 🔄 Re-parsing {name} for v6.2.4 signals...")
                filepath = file_map.get(name) or file_map.get(name.replace("_원본", "").replace(".doc", "").replace(".pdf", ""))
                if filepath:
                    text = extract_text(filepath)
                    new_data = parser.parse(text)
                    if new_data:
                        data = new_data
                        profile = data.get("candidate_profile", {})
                else:
                    print(f"  ⚠️ File not found for {name}, skipping intelligence upgrade.")

            summary = profile.get("experience_summary", "Summary details pending...")
            if isinstance(summary, list):
                summary = "\n".join(summary)

            # [v6.2.4 GDrive Sync]
            # Ensure drive_link exists in JSON or re-upload
            drive_link = profile.get("drive_link") or data.get("drive_link")
            if not drive_link:
                filepath = file_map.get(name) or file_map.get(name.replace("_원본", "").replace(".doc", "").replace(".pdf", ""))
                if filepath:
                    print(f"  📤 Uploading to GDrive: {name}...")
                    _, drive_link = gdrive.upload_file(filepath, GDRIVE_FOLDER_ID)
                    data["drive_link"] = drive_link # Save to subscription data
                else:
                    print(f"  ⚠️ File not found for GDrive upload: {name}")

            # [v6.3.2 Sector & Pattern Optimization]
            # 1. Split merged sector strings (e.g., "TECH_SW | DATA_AI" -> ["TECH_SW", "DATA_AI"])
            raw_sector = profile.get("primary_sector", "Unclassified")
            clean_sectors = [s.strip() for s in raw_sector.replace("|", ",").replace("/", ",").split(",") if s.strip()]
            
            # 2. Format patterns as Rich Text string (Functional-Only v6.3.3)
            # Filter matches from ontology and format as bulleted list
            patterns_list = [p["pattern"] for p in data.get("patterns", [])[:15]]
            rich_patterns = "\n".join([f"• {p}" for p in patterns_list])

            # Property Mapping
            props = {
                "이름": {"title": [{"text": {"content": name}}]},
                "Primary Sector": {"multi_select": [{"name": s} for s in clean_sectors[:3]]},
                "Experience Patterns": {"rich_text": [{"text": {"content": rich_patterns}}]},
                "Trajectory Grade": {"select": {"name": data.get("career_path_quality", {}).get("trajectory_grade", "Neutral")}},
                "v6.2 Score": {"number": data.get("career_path_quality", {}).get("career_path_score", 0)},
                "경력 Summary": {"rich_text": [{"text": {"content": summary}}]},
                "구글드라이브 링크": {"url": drive_link}
            }
            
            # Create or Update in Notion
            if not nid:
                # Case A: Create Page
                new_page = nc.create_page(DATABASE_ID, props)
                if new_page:
                    nid = new_page['id']
                    cursor.execute("UPDATE candidate_snapshots SET notion_id = ?, data_json = ? WHERE id = ?", (nid, json.dumps(data), rid))
                    print(f"[{i+1}/{len(missing)}] ✅ Created {name} (Hub v6.2.4)")
            else:
                # Case B: Update Existing Page
                resp = nc.update_page_properties(nid, props)
                if resp:
                    cursor.execute("UPDATE candidate_snapshots SET data_json = ? WHERE id = ?", (json.dumps(data), rid))
                    print(f"[{i+1}/{len(missing)}] 🆙 Updated {name} (Hub v6.2.4)")
            
            conn.commit()
            time.sleep(0.3) # Avoid Notion rate limits
            
        except Exception as e:
            print(f"  ❌ Error syncing {name}: {e}")

    conn.close()
    print("✨ Sync Recovery & Up-Parsing Complete.")

if __name__ == "__main__":
    run_recovery()
