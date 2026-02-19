from connectors.notion_api import HeadhunterDB
import json

def inspect():
    try:
        db = HeadhunterDB()
        print("Fetching 1 candidate to inspect structure...")
        candidates = db.fetch_candidates(limit=1)
        if candidates:
            print(json.dumps(candidates[0], indent=2, ensure_ascii=False))
        else:
            print("No candidates found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
