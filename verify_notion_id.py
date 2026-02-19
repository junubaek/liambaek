
import json
from connectors.notion_api import HeadhunterDB
import sys

def check_id():
    # Load secrets to confirm what we are using
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    
    id_to_check = secrets.get("NOTION_DATABASE_ID")
    print(f"Loaded ID from secrets: {id_to_check}")
    
    if not id_to_check:
        print("ERROR: No ID in secrets.")
        return

    # Initialize Client
    try:
        db = HeadhunterDB()
        client = db.client
    except Exception as e:
        print(f"Error checking client: {e}")
        return

    print(f"Checking ID: {id_to_check}...")

    # 1. Try as Database
    print("1. Checking if it is a DATABASE...")
    res = client._request("GET", f"databases/{id_to_check}")
    if res and res.get("object") == "database":
        title_obj = res.get('title', [])
        title_text = "".join([t.get('plain_text', '') for t in title_obj])
        print(">>> SUCCESS: It is a DATABASE.")
        print(f"    Title: {title_text}")
        print("    (Connection Verified!)")
        return
    else:
        print("    [x] Not a Database or Access Denied (404).")

    # 2. Try as Page
    print("2. Checking if it is a PAGE...")
    res = client._request("GET", f"pages/{id_to_check}")
    if res and res.get("object") == "page":
        print(">>> SUCCESS: It is a PAGE.")
        print(f"    URL: {res.get('url')}")
        print("    NOTE: The Make_Resume integration is connected, BUT this is a PAGE, not a Database.")
        return
    else:
        print("    [x] Not a Page or Access Denied (404).")

    print("\n>>> CONCLUSION: The ID is inaccessible. The 'Make_Resume' integration is NOT invited to this page/db.")

if __name__ == "__main__":
    check_id()
