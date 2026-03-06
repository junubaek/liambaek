import os
import sqlite3
import json
import PyPDF2
from docx import Document
import sys
sys.path.append(os.getcwd())
from resume_parser import ResumeParser
from connectors.openai_api import OpenAIClient

RESUME_DIR = r"C:\Users\cazam\Downloads\02_resume 전처리"
DB_PATH = "headhunting_engine/data/analytics.db"

def extract_text_from_pdf(filepath):
    text = ""
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception: pass
    return text

def extract_text_from_docx(filepath):
    try:
        doc = Document(filepath)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception: return ""

def extract_text(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.pdf': return extract_text_from_pdf(filepath)
    elif ext == '.docx': return extract_text_from_docx(filepath)
    return ""

def main():
    print("🚀 Rebuilding Intelligence Layer v6.2 from Local Files...")
    
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    
    openai_client = OpenAIClient(secrets["OPENAI_API_KEY"])
    parser = ResumeParser(openai_client)
    
    # 1. Map Files
    print(f"Scanning {RESUME_DIR}...")
    file_map = {} # name_without_ext -> full_path
    for root, _, filenames in os.walk(RESUME_DIR):
        for f in filenames:
            if f.lower().endswith(('.pdf', '.docx')):
                name_base = os.path.splitext(f)[0]
                file_map[name_base] = os.path.join(root, f)
    
    print(f"Found {len(file_map)} local resume files.")
    
    # 2. Connect DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch candidates who haven't been migrated yet
    cursor.execute("SELECT notion_id, data_json FROM candidate_snapshots WHERE data_json NOT LIKE '%v6_2_data%'")
    rows = cursor.fetchall()
    
    candidates = []
    for notion_id, data_json in rows:
        data = json.loads(data_json)
        name = data.get("이름") or data.get("name")
        if name:
            candidates.append((notion_id, name, data_json))
            
    print(f"Candidates to process: {len(candidates)}")
    
    success_count = 0
    match_count = 0
    
    for notion_id, name, data_json in candidates:
        if name in file_map:
            match_count += 1
            filepath = file_map[name]
            print(f"[{match_count}] Processing Match: {name} ({notion_id})")
            
            # Extract Text
            resume_text = extract_text(filepath)
            if not resume_text or len(resume_text.strip()) < 100:
                print(f"  ⚠️ Skipping {name}: Insufficient text extracted.")
                continue
                
            # Parse v6.2
            try:
                print(f"  -> Parsing with GPT-4o-mini...")
                parsed_data = parser.parse(resume_text)
                if not parsed_data:
                    print(f"  ❌ Parsing failed for {name}")
                    continue
                
                # Update DB
                data = json.loads(data_json)
                data["v6_2_data"] = parsed_data
                data["resume_text"] = resume_text # Store text for future use!
                
                cursor.execute(
                    "UPDATE candidate_snapshots SET data_json = ? WHERE notion_id = ?",
                    (json.dumps(data, ensure_ascii=False), notion_id)
                )
                
                # Update patterns
                cursor.execute("DELETE FROM candidate_patterns WHERE candidate_id = ?", (notion_id,))
                for p in parsed_data.get("patterns", []):
                    cursor.execute(
                        "INSERT INTO candidate_patterns (candidate_id, pattern, depth, impact) VALUES (?, ?, ?, ?)",
                        (notion_id, p["pattern"], p.get("depth_weight", 0.2), 0.5)
                    )
                
                conn.commit()
                success_count += 1
                print(f"  ✅ Success! ({success_count} total)")
                
                if success_count >= 5: # Small batch for rapid proof
                    print("\n🛑 Proof-of-concept batch (5) reached. Stopping for user review.")
                    break
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                conn.rollback()
        else:
            # Optional: Log no match?
            pass

    conn.close()
    print(f"\n✨ Rebuild Done. Matches found: {match_count}. Successfully migrated: {success_count}.")

if __name__ == "__main__":
    main()
