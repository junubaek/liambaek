from connectors.notion_api import HeadhunterDB
import json

def inspect():
    try:
        db_instance = HeadhunterDB()
        db_id = db_instance.client.search_db_by_name("Vector DB") or db_instance.client.search_db_by_name("DB")
        print(f"Inspecting DB {db_id}...")
        res = db_instance.client.query_database(db_id, limit=1)
        if res['results']:
            print(json.dumps(res['results'][0]['properties'], indent=2, ensure_ascii=False))
        else:
            print("No candidates found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
