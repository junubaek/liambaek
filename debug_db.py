import sqlite3
import json

db_path = "headhunting_engine/data/analytics.db"

def debug():
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM candidate_snapshots")
        count = cursor.fetchone()[0]
        print(f"Total Candidates: {count}")
        
        cursor.execute("SELECT notion_id, data_json FROM candidate_snapshots")
        rows = cursor.fetchall()
        
        found_content = False
        print("\nScanning for candidates with text content...")
        text_keys = ["resume_text", "summary", "skills", "experience", "이력서", "경력", "자기소개"]
        
        for notion_id, data_json in rows:
            data = json.loads(data_json)
            has_text = any(k in data and data[k] and len(str(data[k])) > 50 for k in text_keys)
            if has_text:
                print(f"Found candidate with text! ID: {notion_id}")
                print("Keys with content:")
                for k in text_keys:
                    if k in data and data[k]:
                        print(f" - {k}: {len(str(data[k]))} chars")
                found_content = True
                break
        
        if not found_content:
            print("No candidates with significant text content found in entire DB.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug()
