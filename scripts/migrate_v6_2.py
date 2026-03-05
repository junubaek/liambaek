import json
import sqlite3
import os
import sys
sys.path.append(os.getcwd())
from resume_parser import ResumeParser
from connectors.openai_api import OpenAIClient

def migrate_v6_2():
    """
    [v6.2] Data Migration Script
    - Fetches all candidates from SQLite.
    - Re-parses their data using ResumeParser v6.2.
    - Updates candidate_snapshots and candidate_patterns tables.
    """
    db_path = "headhunting_engine/data/analytics.db"
    secrets_path = "secrets.json"
    
    if not os.path.exists(secrets_path):
        print("❌ secrets.json not found.")
        return

    with open(secrets_path, "r") as f:
        secrets = json.load(f)
    
    openai_client = OpenAIClient(secrets["OPENAI_API_KEY"])
    parser = ResumeParser(openai_client)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Fetch Candidates
        cursor.execute("SELECT notion_id, data_json FROM candidate_snapshots")
        candidates = cursor.fetchall()
        print(f"🔄 Migrating {len(candidates)} candidates to v6.2...")
        
        for notion_id, data_json in candidates:
            try:
                data = json.loads(data_json)
                resume_text = data.get("resume_text", "") # Assuming resume_text is stored in JSON
                
                if not resume_text:
                    # Try to fetch from other fields if possible? 
                    # For now, skip if no text.
                    print(f"⚠️ No resume text for {notion_id}, skipping.")
                    continue
                
                print(f"  -> Parsing {notion_id}...")
                new_parsed_data = parser.parse(resume_text)
                
                if not new_parsed_data:
                    print(f"❌ Failed to parse {notion_id}.")
                    continue
                
                # 2. Update candidate_snapshots (Update data_json with new v6.2 schema)
                data["v6_2_data"] = new_parsed_data
                cursor.execute(
                    "UPDATE candidate_snapshots SET data_json = ? WHERE notion_id = ?",
                    (json.dumps(data), notion_id)
                )
                
                # 3. Update candidate_patterns
                # Clear old patterns first
                cursor.execute("DELETE FROM candidate_patterns WHERE candidate_id = ?", (notion_id,))
                
                for p in new_parsed_data.get("patterns", []):
                    cursor.execute(
                        "INSERT INTO candidate_patterns (candidate_id, pattern, depth, impact) VALUES (?, ?, ?, ?)",
                        (notion_id, p["pattern"], p.get("depth_weight", 0.2), 0.5) # Impact placeholder
                    )
                
                print(f"✅ Migrated {notion_id}")
                
            except Exception as e:
                print(f"❌ Error migrating {notion_id}: {e}")
        
        conn.commit()
    print("✨ Migration complete.")

if __name__ == "__main__":
    migrate_v6_2()
