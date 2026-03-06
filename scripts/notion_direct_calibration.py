import os
import sys
import json
import time
import math
sys.path.append(os.getcwd())
try:
    from connectors.notion_api import NotionClient
except ImportError:
    # Handle if running from different dir
    sys.path.append('c:/Users/cazam/Downloads/안티그래비티')
    from connectors.notion_api import NotionClient

NOTION_DB_ID = "31a22567-1b6f-8177-86da-ff626bb1e66c"

def calculate_z_scores(scores: list) -> list:
    if not scores: return []
    if len(scores) == 1: return [100.0]
    mean = sum(scores) / len(scores)
    variance = sum((x - mean) ** 2 for x in scores) / len(scores)
    std_dev = math.sqrt(variance)
    if std_dev == 0: return [50.0] * len(scores)
    
    normalized = []
    for s in scores:
        z = (s - mean) / std_dev
        n_score = 50 + (z * 16.6)
        normalized.append(max(0.0, min(100.0, round(float(n_score), 1))))
    return normalized

def run_cloud_calibration():
    print("🌐 Starting Direct Cloud Calibration (Notion-Only)...")
    with open('secrets.json') as f:
        secrets = json.load(f)
    client = NotionClient(secrets['NOTION_API_KEY'])
    
    print("1. Fetching all 1,209+ records from Notion...")
    res = client.query_database(NOTION_DB_ID)
    items = res.get('results', [])
    print(f"   -> Found {len(items)} items.")
    
    # 2. Group by Sector
    sector_data = {} # sector -> list of {id, name, score}
    for item in items:
        props = item['properties']
        name_list = props.get('이름', {}).get('title', [])
        name = name_list[0].get('plain_text', 'Unknown') if name_list else 'Unknown'
        sector = props.get('Primary Sector', {}).get('select', {}).get('name', 'Unclassified')
        score = props.get('v6.2 Score', {}).get('number') or 0.0
        
        if sector not in sector_data: sector_data[sector] = []
        sector_data[sector].append({"id": item['id'], "name": name, "score": score})
        
    # 3. Calibrate per Sector
    updates = []
    print("2. Calculating Relative Z-Scores...")
    for sector, members in sector_data.items():
        raw_scores = [m['score'] for m in members]
        new_scores = calculate_z_scores(raw_scores)
        
        for i, m in enumerate(members):
            if abs(m['score'] - new_scores[i]) >= 0.5: # tighter threshold for final calibration
                updates.append({"id": m['id'], "name": m['name'], "old": m['score'], "new": new_scores[i]})
                
    print(f"   -> {len(updates)} candidates require score updates.")
    
    # 4. Patch Notion
    if not updates:
        print("✅ Cloud scores are already perfectly calibrated.")
        return
        
    print(f"3. Patching Notion (with 350ms delay)...")
    for i, u in enumerate(updates):
        try:
            client.update_page_properties(u['id'], {"v6.2 Score": {"number": u['new']}})
            if (i+1) % 50 == 0 or i == 0:
                print(f"   [{i+1}/{len(updates)}] Updating {u['name']}...")
            time.sleep(0.35)
        except Exception as e:
            print(f"   ❌ Error updating {u['name']}: {e}")
            
    print("✨ Final Cloud Calibration Complete!")

if __name__ == "__main__":
    run_cloud_calibration()
