
import sys
import os
import win32com.client
import pythoncom

def test_doc(file_path):
    print(f"Testing extraction for: {file_path}")
    try:
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        abs_path = os.path.abspath(file_path)
        doc = word.Documents.Open(abs_path)
        text = doc.Range().Text
        doc.Close()
        word.Quit()
        print("Success! Extracted text length:", len(text))
        print("Preview:", text[:100])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_doc(sys.argv[1])
    else:
        print("Usage: python test_doc.py <file_path>")
