import json
import sqlite3
import os
import sys
sys.path.append(os.getcwd())
from resume_parser import ResumeParser
from connectors.openai_api import OpenAIClient
from connectors.notion_api import HeadhunterDB

def migrate_v6_2():
    """
    [v6.2] Data Migration Script
    - Fetches all candidates from SQLite.
    - Re-parses their data using ResumeParser v6.2.
    - Updates candidate_snapshots and candidate_patterns tables.
    """
    db_path = os.path.abspath("headhunting_engine/data/analytics.db")
    secrets_path = "secrets.json"
    
    if not os.path.exists(secrets_path):
        print("❌ secrets.json not found.")
        return

    with open(secrets_path, "r") as f:
        secrets = json.load(f)
    
    openai_client = OpenAIClient(secrets["OPENAI_API_KEY"])
    parser = ResumeParser(openai_client)
    notion_db = HeadhunterDB()
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Fetch Candidates (Limit for testing)
        cursor.execute("SELECT notion_id, data_json FROM candidate_snapshots WHERE data_json NOT LIKE '%v6_2_data%' LIMIT 100")
        candidates = cursor.fetchall()
        print(f"🔄 Migrating {len(candidates)} candidates to v6.2 (via Notion Fallback)...")
        
        success_count = 0
        for notion_id, data_json in candidates:
            try:
                data = json.loads(data_json)
                
                # Robust extraction for v6.2 re-parsing
                resume_text = data.get("resume_text")
                if not resume_text:
                    parts = []
                    if data.get("experience"): parts.append(str(data.get("experience")))
                    if data.get("summary"): parts.append(str(data.get("summary")))
                    if data.get("skills"): parts.append(str(data.get("skills")))
                    resume_text = "\n\n".join(parts)
                
                if not resume_text or len(resume_text.strip()) < 50:
                    print(f"  ☁️ Fetching live text for {notion_id} from Notion...")
                    resume_text = notion_db.fetch_candidate_details(notion_id)
                
                if not resume_text or len(resume_text.strip()) < 50:
                    print(f"⚠️ Insufficient text for {notion_id}, skipping.")
                    continue
                
                print(f"  -> Parsing {notion_id} ({len(resume_text)} chars)...")
                new_parsed_data = parser.parse(resume_text)
                
                if not new_parsed_data:
                    print(f"❌ Failed to parse {notion_id}.")
                    continue
                
                # 2. Update candidate_snapshots
                data["v6_2_data"] = new_parsed_data
                cursor.execute(
                    "UPDATE candidate_snapshots SET data_json = ? WHERE notion_id = ?",
                    (json.dumps(data, ensure_ascii=False), notion_id)
                )
                
                # 3. Update candidate_patterns
                cursor.execute("DELETE FROM candidate_patterns WHERE candidate_id = ?", (notion_id,))
                for p in new_parsed_data.get("patterns", []):
                    cursor.execute(
                        "INSERT INTO candidate_patterns (candidate_id, pattern, depth, impact) VALUES (?, ?, ?, ?)",
                        (notion_id, p["pattern"], p.get("depth_weight", 0.2), 0.5)
                    )
                
                conn.commit() # COMMIT EACH ROW
                success_count += 1
                print(f"✅ Migrated {notion_id} ({success_count}/{len(candidates)})")
                
            except Exception as e:
                print(f"❌ Error migrating {notion_id}: {e}")
                conn.rollback()
    print("✨ Migration complete.")

if __name__ == "__main__":
    migrate_v6_2()
