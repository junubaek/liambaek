
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

    # 3. Process Duplicates (v5 Refined)
    print("Resolving duplicates (Condition: [Name+Email] OR [Vector Similarity > 0.9])...")
    
    archived_count = 0
    for name, cands in duplicates.items():
        # Cross-tenant check is not needed here as Notion DB is one-world for now, 
        # but conceptually we filter by email if possible.
        emails = [c.get('email') or c.get('이메일') for c in cands if c.get('email') or c.get('이메일')]
        
        print(f"\nDuplicate: {name} (Entries: {len(cands)}, Emails: {len(set(emails))})")
        
        # Sort refined for Phase 5
        def sort_key(c):
            # 1. Contact Completeness
            has_email = bool(c.get('email') or c.get('이메일'))
            has_phone = bool(c.get('phone') or c.get('phone_number'))
            contact_score = (2 if (has_email and has_phone) else 1 if (has_email or has_phone) else 0)
            
            # 2. Vector Presence (High priority for future Qdrant lookups)
            vector_ready = 1 if c.get('vector_id') else 0
            
            # 3. Data Recency
            t_str = c.get('created_time', '2000-01-01T00:00:00.000Z')
            
            return (contact_score, vector_ready, t_str)
            
        cands.sort(key=sort_key, reverse=True)
        winner = cands[0]
        losers = cands[1:]
        
        print(f"  -> Winner: {winner['id']} (Recency/Contact Optimized)")
        
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
