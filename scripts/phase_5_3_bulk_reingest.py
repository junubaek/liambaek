import json
import os
import sys
import sqlite3
from typing import List, Dict

# Ensure app is importable
sys.path.append(os.getcwd())

from app.connectors.openai_api import OpenAIClient
from app.utils.candidate_role_classifier import CandidateRoleClassifier
from app.utils.candidate_extractor import CandidatePatternExtractor
from headhunting_engine.data_core import AnalyticsDB
from resume_parser import ResumeParser
from headhunting_engine.connectors.qdrant_connector import QdrantConnector

def bulk_reingest_v5_3():
    print("🔋 [Phase 5.3] Starting Bulk Candidate Hardening...")
    
    # 1. Load Secrets & Init
    with open("secrets.json", "r") as f:
        secrets = json.load(f)
    openai = OpenAIClient(secrets["OPENAI_API_KEY"])
    db = AnalyticsDB()
    try:
        qdrant = QdrantConnector()
        qdrant.ensure_collection()
    except Exception as qe:
        print(f"⚠️ Vector DB (Qdrant) not available: {qe}. Proceeding with SQL Index only.")
        qdrant = None
    
    role_classifier = CandidateRoleClassifier(openai)
    pattern_extractor = CandidatePatternExtractor()
    resume_parser = ResumeParser(openai)
    
    tenant_id = secrets.get("TENANT_ID", "default")
    
    # 2. Fetch ALL candidates for full-scale intelligence hardening [v5.3 Full Match]
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT notion_id, name, data_json FROM candidate_snapshots")
        candidates = cursor.fetchall()
    
    total = len(candidates)
    print(f"📦 Found {total} candidates to process.")
    
    # [v5.3 Recovery] Get list of already indexed IDs
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT candidate_id FROM candidate_patterns")
        processed_ids = {r[0] for r in cursor.fetchall()}
    
    print(f"🔄 Checkpoint: {len(processed_ids)} already indexed. Skipping...")
    sys.stdout.flush()
    
    for i, (notion_id, name, data_json) in enumerate(candidates):
        if notion_id in processed_ids:
            continue
            
        print(f"[{i+1}/{total}] Processing {name} ({notion_id})...")
        sys.stdout.flush()
        try:
            cand_data = json.loads(data_json)
            # Fetch full text from storage if possible, else use what's in JSON
            combined_text = cand_data.get("summary", "") + "\n" + str(cand_data.get("skills", ""))
            # If resume_text is available in data_json, use it.
            resume_text = cand_data.get("resume_text", combined_text)
            
            # A. Update Role Classification
            role = role_classifier.classify_candidate(resume_text)
            db.update_candidate_role(notion_id, role, tenant_id=tenant_id)
            
            # B. Extract & Index Patterns
            # We re-parse to ensure we capture the new ontology patterns
            structured_data = resume_parser.parse(resume_text)
            indexable_patterns = pattern_extractor.extract_indexable_patterns(structured_data)
            db.save_candidate_patterns(notion_id, indexable_patterns, tenant_id=tenant_id)
            
            # C. Update Vector Search Index (Optional)
            if qdrant:
                try:
                    summary_vec_text = f"Candidate: {name}\nRole: {role}\nPatterns: {json.dumps(indexable_patterns)}"
                    emb = openai.embed_content(summary_vec_text)
                    if emb:
                        meta = {
                            "name": name,
                            "role_cluster": role,
                            "tenant_id": tenant_id
                        }
                        qdrant.upsert_candidate(notion_id, emb, meta, tenant_id=tenant_id)
                except Exception as ve:
                     print(f"  ⚠️ Vector Update Failed: {ve}")
                
            print(f"  -> ✅ Role: {role} | Patterns: {len(indexable_patterns)}")
            
        except Exception as e:
            print(f"  ❌ Failed {name}: {e}")

    print("\n🏁 Bulk Hardening Complete!")

if __name__ == "__main__":
    bulk_reingest_v5_3()
