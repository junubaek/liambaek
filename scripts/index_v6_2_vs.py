import os
import sys
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

# Path Setup
sys.path.append(os.getcwd())
from connectors.pinecone_api import PineconeClient
from connectors.openai_api import OpenAIClient

NOTION_DB_ID = "31a22567-1b6f-8177-86da-ff626bb1e66c"
NAMESPACE = "v6.2-vs"

def generate_semantic_profile(data: dict) -> str:
    """
    Constructs a dense semantic profile for embedding.
    Combines structured intelligence with key pattern context.
    """
    profile = []
    
    # 1. Identity & Role
    basics = data.get('candidate_profile', {})
    profile.append(f"Candidate: {basics.get('name', 'Unknown')}")
    profile.append(f"Sector: {basics.get('primary_sector', 'Unclassified')}")
    
    # 2. Trajectory
    traj = data.get('career_path_quality', {})
    profile.append(f"Trajectory: {traj.get('trajectory_grade', 'Neutral')} (Score: {traj.get('career_path_score', 50)})")
    
    # 3. Patterns & Depth
    patterns = data.get('patterns', [])
    pattern_strs = []
    for p in patterns[:15]: # Top 15 patterns
        p_str = f"{p['pattern']} ({p.get('depth', 'Mentioned')})"
        if p.get('impact_type') == 'Quantitative':
            p_str += " [High Impact]"
        pattern_strs.append(p_str)
    
    if pattern_strs:
        profile.append("Experience Patterns: " + ", ".join(pattern_strs))
    
    # 4. Summary Context
    profile.append(f"Context: {data.get('summary', '')}")
    
    return "\n".join(profile)

import hashlib

def get_ascii_id(text: str) -> str:
    """Generates a stable ASCII ID (hash) for non-ASCII candidate names."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:32]

def index_candidates_to_pinecone():
    print(f"🚀 Starting Mass Indexing for v6.2-VS (Namespace: {NAMESPACE})...")
    
    CHECKPOINT_FILE = "scripts/indexing_checkpoint.json"
    processed_ids = []
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            processed_ids = json.load(f)
        print(f"🔄 Resuming from checkpoint. {len(processed_ids)} already indexed.")

    # 1. Init Clients
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    
    pc_host = secrets.get("PINECONE_HOST", "").rstrip("/")
    if not pc_host.startswith("https://"): pc_host = f"https://{pc_host}"
    
    pc = PineconeClient(secrets["PINECONE_API_KEY"], pc_host)
    oa = OpenAIClient(secrets["OPENAI_API_KEY"])
    
    # 2. Fetch processed candidates from SQLite
    db_path = 'headhunting_engine/data/analytics.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, data_json FROM candidate_snapshots")
    rows = cursor.fetchall()
    conn.close()
    
    vectors_to_upsert = []
    batch_size = 30
    
    for i, (name, data_json) in enumerate(rows):
        if name in processed_ids: continue

        try:
            data = json.loads(data_json)
            profile_text = generate_semantic_profile(data)
            
            # Generate Embedding
            embedding = oa.embed_content(profile_text)
            if not embedding:
                continue
                
            # Prepare Metadata
            metadata = {
                "name": name, # Original name for retrieval
                "primary_sector": data.get('candidate_profile', {}).get('primary_sector', 'Unclassified'),
                "trajectory_grade": data.get('career_path_quality', {}).get('trajectory_grade', 'Neutral'),
                "v6.2_score": float(data.get('career_path_quality', {}).get('career_path_score', 0)),
                "summary": data.get('summary', '')[:500]
            }
            
            vectors_to_upsert.append({
                "id": get_ascii_id(name),
                "values": embedding,
                "metadata": metadata
            })
            processed_ids.append(name)
            
            if len(vectors_to_upsert) >= batch_size:
                print(f"  📤 Upserting batch... ({i+1}/{len(rows)})")
                pc.upsert(vectors_to_upsert, namespace=NAMESPACE)
                vectors_to_upsert = []
                # Save Checkpoint
                with open(CHECKPOINT_FILE, "w") as f:
                    json.dump(processed_ids, f)
                time.sleep(0.5)
                
        except Exception as e:
            print(f"  ❌ Error processing {name}: {e}")

    if vectors_to_upsert:
        pc.upsert(vectors_to_upsert, namespace=NAMESPACE)
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(processed_ids, f)
        
    print(f"✨ Indexing Complete. Total unique IDs in checkpoint: {len(processed_ids)}")

if __name__ == "__main__":
    index_candidates_to_pinecone()
