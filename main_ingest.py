
import json
import time
from connectors.notion_api import HeadhunterDB
from connectors.notion_api import HeadhunterDB
from connectors.openai_api import OpenAIClient
from headhunting_engine.connectors.qdrant_connector import QdrantConnector
from headhunting_engine.data_core import AnalyticsDB
from app.utils.candidate_extractor import CandidatePatternExtractor

from classification_rules import ALLOWED_ROLES, ALLOWED_DOMAINS, get_role_cluster, validate_role, validate_domains

def setup_database(notion_db, db_id):
    """Ensures the database has necessary properties."""
    print(f"Verifying Database Schema for {db_id}...")
    props = {
        "AI_Generated": {"checkbox": {}},
        "Role Cluster": {"select": {}},
        "Domain": {"multi_select": {}}
    }
    try:
        notion_db.client.update_database(db_id, props)
        print("  -> Schema Verified (AI_Generated, Role Cluster).")
    except Exception as e:
        print(f"  [!] Schema Update Failed: {e}")

def analyze_candidate_with_llm(openai_client, text_content):
    roles_str = "\n".join([f"- {r}" for r in ALLOWED_ROLES])
    domains_str = "\n".join([f"- {d}" for d in ALLOWED_DOMAINS])
    
    prompt = f"""
    You are an expert Headhunter AI. Analyze the resume text and classify the candidate.
    
    [ALLOWED_ROLES]
    {roles_str}

    [ALLOWED_DOMAINS]
    {domains_str}
    
    [RULES]
    1. Position (Role): 
       - You MUST select exactly ONE role from the [ALLOWED_ROLES] list above.
       - Do NOT invent new role names.
       - If multiple fits, choose the PRIMARY role.
       - If none fit perfectly, choose the closest one.
       
    2. Domain (Industry): 
       - Select ONE or MORE domains from [ALLOWED_DOMAINS].
       - Do NOT invent new domains.
       - Focus on the Industry/Problem Space (e.g. Automotive, Fintech).
       - Ignore technologies (e.g. C++ is NOT a domain).
       
    3. Skills: 
       - Extract key technical skills.
    
    [RESUME PARTIAL]
    {text_content[:4000]}
    
    [OUTPUT_FORMAT_JSON]
    {{
        "position": "String (Must be from ALLOWED_ROLES)",
        "domain": ["String", "String"],
        "skills": ["String", "String", ...]
    }}
    """
    try:
        response = openai_client.get_chat_completion("You are a strict JSON extractor.", prompt)
        clean_json = response.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        return data
    except Exception as e:
        print(f"  [!] AI Analysis Failed: {e}")
        return {"position": "Unclassified", "domain": [], "skills": []}

def main():
    print("Starting AI Resume Ingestion Pipeline (Hardened Mode)...")
    
    # 1. Load Secrets
    try:
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
    except FileNotFoundError:
        print("secrets.json not found.")
        return

    # 2. Initialize Connectors
    notion_db = HeadhunterDB()
    openai = OpenAIClient(secrets["OPENAI_API_KEY"])
    
    qdrant = QdrantConnector()
    qdrant.ensure_collection()
    
    try:
        # 3. Fetch Candidates
        # Explicitly get DB ID to setup schema
        db_id = secrets.get("NOTION_DATABASE_ID")
        if db_id:
            setup_database(notion_db, db_id)
            
        # [Incremental Mode] Only fetch candidates not yet AI-generated
        # To force full re-ingest, set incremental=False
        incremental = False # [Phase 2] Force Full Re-ingestion to populate Metadata
        filter_criteria = None
        
        if incremental:
            print("[Mode] Incremental Ingestion: Fetching only unprocessed candidates...")
            filter_criteria = {
                "property": "AI_Generated",
                "checkbox": {
                    "equals": False
                }
            }
        else:
            print("[Mode] Full Ingestion: Fetching ALL candidates...")

        candidates = notion_db.fetch_candidates(limit=None, filter_criteria=filter_criteria)
        print(f"Fetched {len(candidates)} candidates from Notion.")
        

        # --- Parallel Processing Setup ---
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Define the worker function
        def process_candidate(cand_data):
            cand, idx, total = cand_data
            cand_id = cand.get('id')
            name = (cand.get('name') or cand.get('이름') or cand.get('title') or "Unknown")
            summary = cand.get('summary') or ""
            
            # Manual Override Check
            is_ai_generated = cand.get('ai_generated', False)
            current_position = cand.get('포지션')
            if current_position and current_position != "Unclassified" and is_ai_generated is False:
                print(f"[{idx+1}/{total}] Skipping {name} (Manually Verified)")
                return
            
            try:
                # 1. Fetch Body
                full_text = notion_db.fetch_candidate_details(cand_id)
                combined_text = f"{summary}\n\n{full_text}"
                
                # 2. Parse (Structure)
                # [Phase 2] Use robust ResumeParser
                try:
                    # [Fix] Initialize parser locally or use global if available (but global doesn't pickle well)
                    # For simplicity in ThreadPool, we can re-init or pass it. 
                    # Better: Init inside worker to avoid pickle issues with SSL usage in OpenAI client.
                    if 'parser_instance' not in globals():
                        from connectors.openai_api import OpenAIClient
                        from resume_parser import ResumeParser
                        from headhunting_engine.data_core import AnalyticsDB
                        from app.utils.candidate_extractor import CandidatePatternExtractor
                        import json
                        with open("secrets.json", "r") as f:
                            secrets = json.load(f)
                        _openai = OpenAIClient(secrets["OPENAI_API_KEY"])
                        globals()['parser_instance'] = ResumeParser(_openai)
                        globals()['analytics_db'] = AnalyticsDB()
                        from app.utils.candidate_role_classifier import CandidateRoleClassifier
                        globals()['pattern_extractor'] = CandidatePatternExtractor()
                        globals()['role_classifier'] = CandidateRoleClassifier(_openai)
                    
                    structured_data = globals()['parser_instance'].parse(combined_text)
                    # print(f"  -> Extracted {len(structured_data.get('skills', []))} skills")
                except Exception as e:
                    print(f"  [!] Parsing Failed for {name}: {e}")
                    structured_data = {}

                # 3. Classify (Legacy/Hybrid)
                # print(f"[{idx+1}/{total}] Classifying {name}...")
                ai_result = analyze_candidate_with_llm(openai, combined_text)
                
                # Validation
                raw_position = ai_result.get("position", "Unclassified")
                position = validate_role(raw_position, fallback="Unclassified")
                role_cluster = get_role_cluster(position)
                raw_domains = ai_result.get("domain", [])
                domain_list = validate_domains(position, raw_domains)
                skills = ai_result.get("skills", [])
                
                # 3. Quality Score & Metadata [v5]
                quality = globals()['parser_instance'].calculate_quality_score(structured_data)
                
                # Update Notion with Quality Score
                props_update = {
                    "포지션": {"select": {"name": position}},
                    "Domain": {"multi_select": [{"name": d} for d in domain_list]},
                    "Role Cluster": {"select": {"name": role_cluster}},
                    "AI_Generated": {"checkbox": True},
                    "Data Quality": {"select": {"name": quality["status"]}}
                }
                notion_db.update_candidate(cand_id, props_update)

                # 4. Pattern Indexing & Role Classification [v5.2]
                tenant_id = secrets.get("TENANT_ID", "default")
                
                # A. Pattern Extraction
                indexable_patterns = globals()['pattern_extractor'].extract_indexable_patterns(structured_data)
                globals()['analytics_db'].save_candidate_patterns(cand_id, indexable_patterns, tenant_id=tenant_id)
                
                # B. Role Classification (Symmetric to JD)
                role_cluster_v5 = globals()['role_classifier'].classify_candidate(combined_text)
                globals()['analytics_db'].update_candidate_role(cand_id, role_cluster_v5, tenant_id=tenant_id)
                
                print(f"  -> Indexed {len(indexable_patterns)} patterns | Role: {role_cluster_v5} for {name}")

                # 5. Upsert Multi-tenant Vectors (Qdrant)
                tenant_id = secrets.get("TENANT_ID", "default")
                
                # A. Summary Vector
                summary_text = f"Candidate: {name}\nRole: {position}\nPatterns: {json.dumps(structured_data.get('experience_patterns', []))}"
                emb_summary = openai.embed_content(summary_text)
                if emb_summary:
                    meta = {
                        "name": name,
                        "position": position,
                        "quality": quality["status"],
                        "tenant_id": tenant_id
                    }
                    qdrant.upsert_candidate(cand_id, emb_summary, meta, tenant_id=tenant_id)
                 
            except Exception as e:
                print(f"  [!] Error processing {name}: {e}")
                import traceback
                traceback.print_exc()

        # End of process_candidate

        # Execute Parallel Processing
        # We need to ensure candidates_data is available. 
        # In main(), 'candidates' is the list. 
        # We need to Wrap it with index: list(enumerate(candidates))?
        # See line 111: cand, idx, total = cand_data
        
        candidates_data = [(c, i, len(candidates)) for i, c in enumerate(candidates)]
        
        # Use ThreadPoolExecutor for parallel processing
        # Reduced workers to 2 to avoid OpenAI 429 Rate Limits
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(process_candidate, c): c for c in candidates_data}
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Worker Exception: {e}")
            
    except Exception as e:
        import traceback
        print("\n[CRITICAL ERROR] Script crashed!")
        traceback.print_exc()
        exit(1)
        
    print("\nIngestion Complete!")

if __name__ == "__main__":
    main()
