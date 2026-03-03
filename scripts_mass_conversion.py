import os
import win32com.client
import pythoncom
import time

def convert_doc_to_docx(source_dir, target_dir):
    """
    Mass converts .doc files to .docx using Word COM automation.
    """
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # Initialize Word
    pythoncom.CoInitialize()
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False

    doc_files = []
    for root, dirs, files in os.walk(source_dir):
        for f in files:
            if f.lower().endswith(".doc") and not f.startswith("~$"):
                doc_files.append(os.path.join(root, f))

    print(f"📂 Found {len(doc_files)} .doc files to convert.")
    
    success_count = 0
    fail_count = 0

    for i, doc_path in enumerate(doc_files):
        try:
            filename = os.path.basename(doc_path)
            # Create subfolder structure in target if needed, or flatten
            # Here we flatten for easy batch parsing later
            target_name = os.path.splitext(filename)[0] + ".docx"
            target_path = os.path.join(target_dir, target_name)

            if os.path.exists(target_path):
                # print(f"[{i+1}/{len(doc_files)}] Skipped (Exists): {filename}")
                continue

            print(f"[{i+1}/{len(doc_files)}] Converting: {filename}...")
            
            abs_source = os.path.abspath(doc_path)
            abs_target = os.path.abspath(target_path)

            doc = word.Documents.Open(abs_source)
            # FileFormat=16 is for .docx
            doc.SaveAs2(abs_target, FileFormat=16) 
            doc.Close()
            
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to convert {filename}: {e}")
            fail_count += 1
        
        # Periodic sleep to prevent Word from hanging
        if (i + 1) % 50 == 0:
            time.sleep(1)

    word.Quit()
    print(f"\n✅ Conversion Finished. Success: {success_count}, Fail: {fail_count}")

if __name__ == "__main__":
    SOURCE = r"C:\Users\cazam\Downloads\02_resume 전처리"
    TARGET = r"C:\Users\cazam\Downloads\02_resume_converted_docx"
    convert_doc_to_docx(SOURCE, TARGET)
