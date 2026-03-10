import os
import sqlite3
import json
import time
import sys
import PyPDF2
from docx import Document
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.getcwd())
from resume_parser import ResumeParser
from connectors.openai_api import OpenAIClient
from connectors.notion_api import NotionClient
from connectors.gdrive_api import GDriveConnector

# Configuration
DIR_RAW = r"C:\Users\cazam\Downloads\02_resume 전처리"
DIR_CONV = r"C:\Users\cazam\Downloads\02_resume_converted_docx"
GDRIVE_FOLDER_ID = "1VzJEeoXG239PVR3IoJM5jC28KccMdkth"
NOTION_DB_ID = "31a22567-1b6f-8177-86da-ff626bb1e66c"
DB_PATH = "headhunting_engine/data/analytics.db"

def extract_text(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    text = ""
    try:
        if ext == '.pdf':
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
        elif ext == '.docx':
            doc = Document(filepath)
            text = "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"Error extracting {filepath}: {e}")
    return text.strip()

def is_meaningless(text, filepath):
    # Filter 1: Empty or very short
    if not text or len(text) < 150: return True
    # Filter 2: Temp files
    if os.path.basename(filepath).startswith("~$"): return True
    # Filter 3: Tiny size
    if os.path.getsize(filepath) < 2000: return True
    return False

def unified_process():
    print("🛡️ Starting Unified v6.2 Restoration & Sync...")
    
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    
    # Initialize Clients
    openai_client = OpenAIClient(secrets["OPENAI_API_KEY"])
    parser = ResumeParser(openai_client)
    notion_client = NotionClient(secrets["NOTION_API_KEY"])
    gdrive = GDriveConnector()
    
    # 0. Update Database Schema (New properties for v6.2)
    print("🛠️ Orchestrating Notion Database Schema...")
    schema_update = {
        "v6.2 Score": {"number": {"format": "number"}},
        "Experience Patterns": {"multi_select": {}},
        "Trajectory Grade": {"select": {}},
        "Primary Sector": {"select": {}},
        "구글드라이브 링크": {"url": {}}
    }
    notion_client.update_database(NOTION_DB_ID, schema_update)
    time.sleep(2)
    
    # 1. Deduplicate & Map Files
    print("🔍 Mapping local files (Deduplicating Raw vs Converted)...")
    file_map = {} # name -> best_local_path
    
    # Process Raw first
    for f in os.listdir(DIR_RAW):
        if f.lower().endswith(('.pdf', '.docx')) and not f.startswith("~$"):
            name_base = os.path.splitext(f)[0]
            file_map[name_base] = os.path.join(DIR_RAW, f)
            
    # Overwrite with Converted if exists
    for f in os.listdir(DIR_CONV):
        if f.lower().endswith(('.docx')) and not f.startswith("~$"):
            # Check for name match even if raw was .pdf
            # e.g. "김철수.pdf" in raw vs "김철수.docx" in converted
            name_base = os.path.splitext(f)[0]
            # Handle potential suffix from conversion like "(원본)"? 
            # If user said it's same, we match by base.
            file_map[name_base] = os.path.join(DIR_CONV, f)
            
    print(f"💡 Found {len(file_map)} unique candidate files after deduplication.")

    # 2. Connect DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch existing metadata from analytics.db to find matches
    cursor.execute("SELECT notion_id, data_json FROM candidate_snapshots")
    db_candidates = cursor.fetchall()
    
    # Create Name -> NotionID map
    db_map = {}
    for nid, djson in db_candidates:
        data = json.loads(djson)
        name = data.get("이름") or data.get("name")
        if name: db_map[name] = nid

    # 3. Processing Loop
    success_count = 0
    start_time = time.time()
    
    # 3b. Pre-fetch Notion entries with Drive links to enable resumability
    print("📋 Checking for already synced candidates in Notion...")
    synced_map = {} # name -> drive_link
    try:
        n_res = notion_client.query_database(NOTION_DB_ID)
        for item in n_res.get('results', []):
            p = item.get('properties', {})
            t_list = p.get('이름', {}).get('title', [])
            if t_list:
                c_name = t_list[0].get('plain_text')
                d_link = p.get('구글드라이브 링크', {}).get('url')
                if d_link: synced_map[c_name] = d_link
        print(f"    -> Found {len(synced_map)} candidates already synced.")
    except Exception as e:
        print(f"    -> Error pre-fetching Notion: {e}")

    all_names = list(file_map.keys())
    print(f"🔄 Starting processing loop for {len(all_names)} candidates...")

    for i, name_base in enumerate(all_names):
        try:
            # Resumable Check: Does this candidate exist in the NEW Hub?
            current_notion_id = None
            # Check synced_map (populated from NEW database)
            if name_base in synced_map:
                print(f"[{i+1}/{len(all_names)}] ⏭️ Skipping {name_base}: Already exists in NEW Hub.")
                success_count += 1
                continue

            filepath = file_map[name_base]
            
            # Step A: Text Extraction & Filter
            text = extract_text(filepath)
            if is_meaningless(text, filepath):
                print(f"  ⏭️ Skipping {name_base}: Meaningless or too small.")
                continue

            # Step B: Google Drive Upload
            print(f"[{i+1}/{len(all_names)}] 📤 Uploading {name_base} to GDrive...")
            drive_id, drive_link = gdrive.upload_file(filepath, GDRIVE_FOLDER_ID)

            # Step C: v6.2 AI Parsing
            print(f"  🧠 Parsing v6.2 Intelligence...")
            v62_data = parser.parse(text)
            if not v62_data:
                print(f"  ❌ Failed to parse {name_base}.")
                continue

            # Step D: Sync to Notion (Consolidated Hub v6.3.3)
            # Format patterns as Rich Text (Functional-Only)
            patterns_text = "\n".join([f"• {p['pattern']}" for p in v62_data.get("patterns", [])[:15]])
            
            props = {
                "이름": {"title": [{"text": {"content": name_base}}]},
                "Primary Sector": {"select": {"name": v62_data.get("candidate_profile", {}).get("primary_sector", "Unclassified")}},
                "Experience Patterns": {"rich_text": [{"text": {"content": patterns_text}}]},
                "Trajectory Grade": {"select": {"name": v62_data.get("career_path_quality", {}).get("trajectory_grade", "Neutral")}},
                "v6.2 Score": {"number": v62_data.get("career_path_quality", {}).get("career_path_score", 0)},
                "구글드라이브 링크": {"url": drive_link}
            }

            # Strategy: Always creating in the new Hub unless we have a specific ID in it
            # But the 'resumable check' already handled 'if name_base in synced_map'
            # So if we are here, we MUST create it in the new Hub.
            notion_client.create_page(NOTION_DB_ID, props)
            print(f"  ✅ Created Notion Entry: {name_base} (v6.2 Hub)")

            # Step E: Update Local DB cache
            # (Optional: implementation depends on if current candidate is in DB)
            
            success_count += 1
            
            # Progress reporting
            elapsed = time.time() - start_time
            avg_time = elapsed / success_count
            remaining = (len(all_names) - i) * avg_time
            print(f"  🕒 Progress: {success_count} success. Est. remaining: {remaining/60:.1f} min.")
            
            # if success_count >= 10: 
            #     print("\n🛑 Proof of Concept (10) Complete. Pausing for user review.")
            #     break

        except Exception as e:
            print(f"  ❌ Fatal error for {name_base}: {e}")

    print(f"\n✨ Unified Process Finished. Total Success: {success_count}.")

if __name__ == "__main__":
    unified_process()
