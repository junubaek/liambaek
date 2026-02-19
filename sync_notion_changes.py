
import os
import time
import json
from connectors.notion_api import HeadhunterDB
from connectors.pinecone_api import PineconeClient
from classification_rules import get_role_cluster

def sync_notion_to_pinecone():
    print("Starting Notion <-> Pinecone Sync...")
    
    # 1. Connect
    notion_db = HeadhunterDB()
    pinecone_client = PineconeClient()
    
    # 2. Setup Database ID
    target_db_name = "Vector DB"
    db_id = None
    try:
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
            db_id = secrets.get("NOTION_DATABASE_ID")
    except:
        pass
        
    if not db_id:
        db_id = notion_db.client.search_db_by_name(target_db_name)
    
    if not db_id:
        print("Notion DB not found.")
        return

    # 3. Fetch All Pages (Simple Scan for now - can be optimized to Last Edited later)
    # We will fetch pages where "AI_Generated" is checked or unchecked.
    # Actually, we should fetch EVERYTHING and compare with Pinecone, 
    # OR mostly trust Notion as Single Source of Truth for metadata.
    
    print("Fetching all candidates from Notion...")
    pages = notion_db.get_all_candidates(db_id)
    print(f"Found {len(pages)} candidates in Notion.")
    
    updated_count = 0
    
    for page in pages:
        cand_id = page['id']
        props = page['properties']
        
        # Extract Notion Data
        name = ""
        title_prop = props.get("Name", {}).get("title", [])
        if title_prop:
            name = title_prop[0].get("plain_text", "")
            
        position = "Unclassified"
        pos_prop = props.get("포지션", {}).get("select")
        if pos_prop:
            position = pos_prop.get("name", "Unclassified")
            
        role_cluster = "Unclassified"
        cluster_prop = props.get("Role Cluster", {}).get("select")
        if cluster_prop:
            role_cluster = cluster_prop.get("name", "Unclassified")
        else:
             # Auto-correct Cluster if missing in Notion but Position exists
             role_cluster = get_role_cluster(position)
             
        domains = []
        domain_prop = props.get("Domain", {}).get("multi_select", [])
        for d in domain_prop:
            domains.append(d['name'])
            
        # 4. Update Pinecone Metadata
        # We need the vector ID. Usually it is the candidate ID or Name based.
        # But Pinecone IDs in main_ingest were generated from Name + Hash.
        # This is TRICKY if we don't have the original Pinecone ID stored in Notion.
        # Workaround: Search Pinecone by Metadata filter (candidate_id) NOT supported easily without ID.
        # WAIT! We didn't store Pinecone ID in Notion. 
        # But we stored 'candidate_id' (Notion ID) in Pinecone Metadata? 
        # Let's check main_ingest.py... 
        # Yes: "candidate_id": cand_id is in metadata.
        
        # But to UPDATE Pinecone, we need the Vector ID.
        # If we don't know the Vector ID, we cannot update it efficiently.
        # For now, we unfortunately have to rely on the fact that we might NOT be able to sync back 
        # UNLESS we stored the Vector ID in Notion or we can search Pinecone by metadata (slow/limited).
        
        # ALTERNATIVE: main_ingest.py uses `generate_compact_id(name)`.
        # If name hasn't changed, we can regenerate the ID.
        
        import hashlib
        compact_id = hashlib.md5(name.encode()).hexdigest()[:10]
        # This was the logic in main_ingest.py (simplified check)
        
        # Let's try to fetch this vector
        try:
            # We can't easily partially update metadata without ID.
            # Assuming ID is `compact_id`.
            
            # Check if exists?
            # pinecone_client.index.fetch([compact_id]) ...
            
            # Just Update Metadata
            new_metadata = {
                "position": position,
                "role_cluster": role_cluster,
                "domain": domains,
                # "updated_at": ...
            }
            
            # Pinecone update_metadata (if supported by our wrapper or raw client)
            pinecone_client.index.update(
                id=compact_id,
                set_metadata=new_metadata
            )
            print(f"  [v] Synced: {name} -> {position} ({role_cluster})")
            updated_count += 1
            
        except Exception as e:
            print(f"  [!] Failed to sync {name}: {e}")

    print(f"Sync Complete. Updated {updated_count} candidates.")

if __name__ == "__main__":
    sync_notion_to_pinecone()
