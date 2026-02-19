
import json
import collections
from connectors.notion_api import HeadhunterDB

def main():
    print("--- Notion Duplicate Remover ---")
    db = HeadhunterDB()
    
    # 1. Fetch All Candidates (Names and IDs)
    print("Fetching all candidates to check for duplicates...")
    candidates = db.fetch_candidates(limit=None)
    
    # 2. Group by Name
    name_map = collections.defaultdict(list)
    for c in candidates:
        name = c.get('name') or c.get('이름') or c.get('title')
        if name:
            name_map[name].append(c)
            
    duplicates = {name: cands for name, cands in name_map.items() if len(cands) > 1}
    
    print(f"\nFound {len(duplicates)} sets of duplicates.")
    
    if not duplicates:
        print("No duplicates found! 🎉")
        return

    # 3. Process Duplicates
    print("Resolving duplicates (Keeping the one with 'AI_Generated'=True or URL)...")
    
    archived_count = 0
    for name, cands in duplicates.items():
        print(f"\nDuplicate: {name} ({len(cands)} entries)")
        
        # Sort criteria: 
        # 1. Has Contact Info (Email/Phone) - High Priority
        # 2. Created Time (Newer is better) - High Priority
        # 3. AI Generated (Bonus to avoid re-processing if all else equal)
        
        def score(c):
            s = 0
            
            # 1. Contact Info Check
            has_email = bool(c.get('email') or c.get('이메일'))
            has_phone = bool(c.get('phone') or c.get('phone_number') or c.get('연락처') or c.get('전화번호'))
            
            if has_email or has_phone:
                s += 2000  # Major priority
            if has_email and has_phone:
                s += 500   # Both is even better

            # 2. Recency (Timestamp)
            # Use timestamp as a tie-breaker (convert to seconds, scale down to fractional or small int)
            # But here just adding a component. 
            # Better strategy: Sort by tuple key.
            return s

        # Tuple Sort: (Has Contact, Timestamp, AI Generated)
        def sort_key(c):
            # 1. Contact
            has_email = bool(c.get('email') or c.get('이메일'))
            has_phone = bool(c.get('phone') or c.get('phone_number') or c.get('연락처') or c.get('전화번호'))
            contact_score = (2 if (has_email and has_phone) else 1 if (has_email or has_phone) else 0)
            
            # 2. Time
            from datetime import datetime
            t_str = c.get('created_time', '2000-01-01T00:00:00.000Z')
            try:
                # Basic parsing, ISO format usually
                timestamp = t_str
            except:
                timestamp = "0"
                
            # 3. AI
            ai = 1 if c.get('ai_generated') else 0
            
            return (contact_score, timestamp, ai)
            
        cands.sort(key=sort_key, reverse=True)
        
        winner = cands[0]
        losers = cands[1:]
        
        print(f"  -> Keeping: ID={winner['id']} (Score: {score(winner)})")
        
        # Archive losers
        for loser in losers:
            print(f"  -> Archiving: ID={loser['id']}")
            try:
                # To archive in Notion, update 'archived': True property on the page endpoint, 
                # but notion_api might generally use filtering. 
                # Actually Notion API allows archiving via Update Page endpoint with "archived": true
                
                # Check if client has archive method?
                # If not, implement raw request
                url = f"https://api.notion.com/v1/pages/{loser['id']}"
                import urllib.request
                
                payload = json.dumps({"archived": True}).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers=db.client.headers, method="PATCH")
                with urllib.request.urlopen(req) as res:
                    if res.status == 200:
                        print("     [Archived successfully]")
                        archived_count += 1
            except Exception as e:
                print(f"     [Error archiving] {e}")

    print(f"\nCreation Complete. Archived {archived_count} duplicate pages.")

if __name__ == "__main__":
    main()
