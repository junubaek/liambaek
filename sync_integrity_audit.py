import os
import sys
import json
sys.path.append(os.getcwd())
from connectors.notion_api import NotionClient
from connectors.gdrive_api import GDriveConnector

def run_audit():
    with open('secrets.json') as f:
        secrets = json.load(f)
    
    client = NotionClient(secrets['NOTION_API_KEY'])
    gdrive = GDriveConnector()
    
    FOLDER_ID = "1VzJEeoXG239PVR3IoJM5jC28KccMdkth"
    DB_ID = "31a22567-1b6f-8177-86da-ff626bb1e66c"
    
    print("📋 Starting Cloud Sync Integrity Audit...")
    
    # 1. Fetch all files from GDrive folder
    print("  - Fetching GDrive file list...")
    g_res = gdrive.service.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed = false",
        fields="files(id, name)"
    ).execute()
    g_files = {f['name']: f['id'] for f in g_res.get('files', [])}
    print(f"    -> Found {len(g_files)} files on Google Drive.")
    
    # 2. Fetch all entries from Notion DB
    print("  - Fetching Notion database entries...")
    n_res = client.query_database(DB_ID)
    n_items = n_res.get('results', [])
    n_names = set()
    for item in n_items:
        props = item.get('properties', {})
        title_list = props.get('이름', {}).get('title', [])
        if title_list:
            n_names.add(title_list[0].get('plain_text'))
    print(f"    -> Found {len(n_names)} entries in Notion.")
    
    # 3. Compare
    missing = []
    for g_name in g_files:
        # Match base name (excluding extension) if needed, but script uses base name as title
        if g_name.split('.')[0] not in n_names and g_name not in n_names:
            missing.append(g_name)
            
    if missing:
        print(f"⚠️ Found {len(missing)} desynced candidates (On GDrive but NOT in Notion):")
        for m in missing[:20]:
            print(f"   - {m}")
        if len(missing) > 20: print(f"   ... and {len(missing)-20} more.")
    else:
        print("✅ Integrity Check Passed! All GDrive uploads are represented in Notion.")

if __name__ == "__main__":
    run_audit()
