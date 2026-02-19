import os
import json
import time
import urllib.parse
from connectors.notion_api import HeadhunterDB
import PyPDF2
from docx import Document
import win32com.client
import pythoncom

RESUME_DIR = r"C:\Users\cazam\Downloads\02_resume 전처리"

def chunk_text(text, limit=1000): # Reduced limit for safety
    """Splits text into chunks of max 1000 characters for Notion blocks."""
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def extract_text_from_pdf(filepath):
    text = ""
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF {filepath}: {e}")
    return text

def extract_text_from_doc_using_win32(file_path):
    """Extracts text from .doc files using Word COM."""
    try:
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        abs_path = os.path.abspath(file_path)
        doc = word.Documents.Open(abs_path)
        text = doc.Range().Text
        doc.Close()
        word.Quit()
        return text
    except Exception as e:
        print(f"Error reading Word file {file_path}: {e}")
        return ""

def extract_text_from_docx(file_path):
    """Extracts text from .docx files using python-docx."""
    try:
        doc = Document(file_path)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        return '\n'.join(text)
    except Exception as e:
        print(f"Error reading DOCX {file_path}: {e}")
        return ""

def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    elif ext == '.doc':
        return extract_text_from_doc_using_win32(file_path)
    return ""

def main():
    print("Initializing Notion Uploader...")
    db = HeadhunterDB()
    client = db.client
    
    # 1. Find Target Database
    # Priority: secrets.json > Search by Name
    target_db_name = "Vector DB"
    db_id = None
    
    try:
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
            db_id = secrets.get("NOTION_DATABASE_ID")
    except Exception:
        pass
        
    if not db_id:
        print("No ID in secrets. Searching by name...")
        db_id = client.search_db_by_name(target_db_name)
    
    if not db_id:
        print(f"CRITICAL: Database '{target_db_name}' not found!")
        print("Please ensure you created a DATABASE (not just a page) named 'Vector DB' in Notion.")
        return

    print(f"Found Target DB: {target_db_name} ({db_id})")
    
    
    # 2. Check for Existing Files (Prevent Duplicates)
    print("Checking for existing pages to avoid duplicates...")
    existing_pages = set()
    
    # Use improved query_database which handles pagination
    res = client.query_database(db_id, limit=None)
    all_results = res.get('results', [])
    
    print(f"  Fetched {len(all_results)} existing pages from Notion.")
        
    for p in all_results:
        props = p.get('properties', {})
        # Check '이름' or 'Name' or 'title'
        for key, val in props.items():
            if val['type'] == 'title':
                if val['title']:
                    existing_pages.add(val['title'][0]['plain_text'])
    
    print(f"Found {len(existing_pages)} unique existing titles.")

    # 3. Scan Files (Recursive)
    files = []
    print(f"Scanning {RESUME_DIR} recursively...")
    for root, dirs, filenames in os.walk(RESUME_DIR):
        for f in filenames:
             if f.lower().endswith(('.pdf', '.docx', '.doc')):
                 files.append(os.path.join(root, f))

    print(f"Found {len(files)} resume files.")
    
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    for i, filepath in enumerate(files):
        filename = os.path.basename(filepath)
        
        # Check Duplicate
        name_check = os.path.splitext(filename)[0]
        if name_check in existing_pages:
             # print(f"[{i+1}/{len(files)}] Skipping (Already Exists): {filename}")
             skipped_count += 1
             continue
        print(f"[{i+1}/{len(files)}] Processing: {filename}...")
        
        # Extract Text
        content = ""
        if filename.lower().endswith('.pdf'):
            content = extract_text_from_pdf(filepath)
        elif filename.lower().endswith('.docx'):
            content = extract_text_from_docx(filepath)
            
        if not content.strip():
            print(f"  [!] No text extracted. Uploading with placeholder.")
            content = "Original File Content Not Extracted. Please check the attached link."
            # fail_count += 1
            # continue
            
        # Parse Filename and Generate Drive Link
        name_prop = filename.replace(".pdf", "").replace(".docx", "")
        drive_link = f"https://drive.google.com/drive/u/0/search?q={urllib.parse.quote(filename)}"
        
        # Prepare Notion Blocks
        children_blocks = []
        
        # 1. Add Link to Drive File (Callout Block)
        children_blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {
                        "type": "text", 
                        "text": { "content": f"📂 View Original File: {filename}", "link": {"url": drive_link} } 
                    }
                ],
                "icon": {"emoji": "📄"}
            }
        })

        chunks = chunk_text(content)
        
        # Limit to first 50 blocks (~100k chars) to avoid timeouts/limits
        if len(chunks) > 50:
             chunks = chunks[:50]
             chunks.append("... (Truncated)")
             
        for chunk in chunks:
            children_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{ "type": "text", "text": { "content": chunk } }]
                }
            })
            
        # Prepare Properties
        # Note: Adjust property names to match your Notion DB schema!
        # Guaranteed schema usually has 'Name' (title). 
        # Optional: 'Position', 'Domain', 'Summary'.
        properties = {
            "이름": {
                "title": [{"text": {"content": name_prop}}]
            },
            "Role Cluster": {
                "select": {"name": "Unclassified"}
            },
            "Domain": {
                 "multi_select": [{"name": "Unclassified"}]
            },
            "구글드라이브 링크": {
                "url": drive_link
            }
        }

        try:
            res = client.create_page(db_id, properties, children_blocks)
            if res:
                print("  -> Upload Success!")
                success_count += 1
            else:
                print("  -> Upload Failed (API Error).")
                fail_count += 1
        except Exception as e:
            print(f"  -> Upload Failed: {e}")
            fail_count += 1
            
        time.sleep(0.5) # Rate limit protection

    print("\n" + "="*30)
    print(f"Upload Complete. Success: {success_count}, Failed: {fail_count}, Skipped: {skipped_count}")

if __name__ == "__main__":
    main()
