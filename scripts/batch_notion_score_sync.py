import os
import sqlite3
import json
import time
import math
import sys
from typing import Dict, List

sys.path.append(os.getcwd())
from connectors.notion_api import NotionClient

# Configuration
# Note: Real Notion DB ID from previous turns
NOTION_DB_ID = "31a22567-1b6f-8177-86da-ff626bb1e66c"
DB_PATH = "headhunting_engine/data/analytics.db"

def calculate_z_scores(scores: List[float]) -> List[float]:
    """
    Calculates Z-normalized scores mapped to a 0-100 scale.
    Formula: Score = 50 + (Z * 16.6) -> roughly 3 sigma spread.
    """
    if not scores: return []
    if len(scores) == 1: return [100.0]
    
    mean = sum(scores) / len(scores)
    variance = sum((x - mean) ** 2 for x in scores) / len(scores)
    std_dev = math.sqrt(variance)
    
    if std_dev == 0: return [50.0] * len(scores)
    
    normalized = []
    for s in scores:
        z = (s - mean) / std_dev
        # T-score style mapping to 0-100
        n_score = 50 + (z * 16.6)
        normalized.append(max(0.0, min(100.0, round(float(n_score), 1))))
    return normalized

def batch_calibrate_and_sync():
    print("🚀 Starting Periodic Score Calibration & Notion Batch Sync (v6.2.1)...")
    
    if not os.path.exists("secrets.json"):
        print("❌ Error: secrets.json not found.")
        return

    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    
    if "NOTION_API_KEY" not in secrets:
        print("❌ Error: NOTION_API_KEY missing in secrets.json")
        return

    notion = NotionClient(secrets["NOTION_API_KEY"])
    
    # 1. Fetch current Notion scores (for Diff Check)
    print("📋 Fetching current Notion state for Diff Check...")
    notion_state = {} # name -> {id: str, score: float}
    try:
        n_res = notion.query_database(NOTION_DB_ID)
        for row in n_res.get('results', []):
            props = row['properties']
            # Try potential title keys: '이름' or 'Name'
            name_list = props.get('이름', {}).get('title', []) or props.get('Name', {}).get('title', [])
            if name_list:
                name = name_list[0]['plain_text']
                score_data = props.get('v6.2 Score', {}).get('number')
                notion_state[name] = {"id": row['id'], "score": float(score_data or 0)}
    except Exception as e:
        print(f"❌ Error querying Notion: {e}")
        return

    print(f"    -> Found {len(notion_state)} candidates in Notion.")

    # 2. Fetch Local data and group by Sector
    print("🔍 Fetching local analytics data...")
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: {DB_PATH} not found.")
        return

    sector_groups = {} # sector -> [ {name, raw_score} ]
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT data_json FROM candidate_snapshots")
        rows = cursor.fetchall()
        
        for (djson,) in rows:
            data = json.loads(djson)
            name = data.get("이름") or data.get("name")
            if not name: continue
            
            # Extract v6.2 intelligence
            v62_data = data.get("v6_2_data")
            if not v62_data: continue
            
            raw_score = v62_data.get("career_path_quality", {}).get("career_path_score", 0)
            sector = v62_data.get("candidate_profile", {}).get("primary_sector", "Unclassified")
            
            if sector not in sector_groups: sector_groups[sector] = []
            sector_groups[sector].append({"name": name, "raw_score": float(raw_score)})
        conn.close()
    except Exception as e:
        print(f"❌ Error reading local DB: {e}")
        return

    # 3. Calculate Relative Scores per Sector
    print(f"⚖️ Calculating Sector-based Z-Scores for {len(sector_groups)} sectors...")
    updates_needed = []
    
    for sector, members in sector_groups.items():
        if not members: continue
        raw_scores = [m['raw_score'] for m in members]
        calibrated_scores = calculate_z_scores(raw_scores)
        
        for idx, member in enumerate(members):
            new_score = calibrated_scores[idx]
            name = member['name']
            
            # Delta Check
            if name in notion_state:
                old_score = notion_state[name]['score']
                if abs(new_score - old_score) >= 1.0: # threshold for update
                    updates_needed.append({
                        "id": notion_state[name]['id'],
                        "name": name,
                        "old": old_score,
                        "new": new_score,
                        "sector": sector
                    })

    print(f"📊 Calibration Summary:")
    for sector, members in sector_groups.items():
        print(f"  - {sector:15}: {len(members)} candidates")
    print(f"\n⚖️ Delta Check: {len(updates_needed)} candidates require Notion updates.")

    # 4. Patch Notion with Rate Limiting (3 req/sec)
    if not updates_needed:
        print("✅ No significant score drifts detected. Cloud is in sync.")
        return

    print(f"🔄 Executing Delta Sync (Rate Limit: 350ms delay)...")
    for i, up in enumerate(updates_needed):
        try:
            notion.update_page_properties(up['id'], {
                "v6.2 Score": {"number": up['new']}
            })
            print(f"  [{i+1}/{len(updates_needed)}] Updated {up['name']} ({up['sector']}): {up['old']} -> {up['new']}")
            time.sleep(0.35)
        except Exception as e:
            print(f"  ❌ Failed to update {up['name']}: {e}")

    print("\n✨ Batch Calibration & Sync Finished.")

if __name__ == "__main__":
    batch_calibrate_and_sync()
