
import json
import time
from connectors.notion_api import HeadhunterDB
from connectors.notion_api import HeadhunterDB
from connectors.openai_api import OpenAIClient
from connectors.pinecone_api import PineconeClient

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
    
    # Fix Pinecone Host URL
    pc_host = secrets.get("PINECONE_HOST", "")
    if not pc_host.startswith("https://"):
        pc_host = f"https://{pc_host}"
    
    pinecone = PineconeClient(secrets["PINECONE_API_KEY"], pc_host)
    
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
                        import json
                        with open("secrets.json", "r") as f:
                            secrets = json.load(f)
                        _openai = OpenAIClient(secrets["OPENAI_API_KEY"])
                        globals()['parser_instance'] = ResumeParser(_openai)
                    
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
                
                # Update Notion
                props_update = {
                    "포지션": {"select": {"name": position}},
                    "Domain": {"multi_select": [{"name": d} for d in domain_list]},
                    "Role Cluster": {"select": {"name": role_cluster}},
                    "AI_Generated": {"checkbox": True}
                }
                notion_db.update_candidate(cand_id, props_update)

                # 4. Upsert Vectors
                vectors_to_upsert = []
                import hashlib
                compact_id = hashlib.md5(name.encode()).hexdigest()[:10]
                
                # A. Summary Vector (Base Profile)
                domain_str = ", ".join(domain_list)
                summary_text = f"""
                Name: {name}
                Role: {position}
                Cluster: {role_cluster}
                Domain: {domain_str}
                Total Exp: {structured_data.get('total_years_experience', 0)} years
                Summary: {structured_data.get('summary', '')}
                Skills: {', '.join(skills)}
                Resume Body: {full_text[:3000]}
                """
                
                if not structured_data:
                    structured_data = {}

                emb_summary = openai.embed_content(summary_text)
                if emb_summary:
                    basics = structured_data.get("basics") or {}
                    
                    meta_summary = {
                        "candidate_id": cand_id, # Link to Notion ID
                        "name": name,
                        "type": "summary",
                        "position": position,
                        "role_cluster": role_cluster,
                        "domain": domain_list,
                        "summary": (structured_data.get("summary") or "")[:1000],
                        # [Phase 2] Rich Metadata for Filtering
                        "total_years": int(basics.get("total_years_experience") or 0),
                        "skills": (structured_data.get("skills") or [])[:50], 
                        "companies": [job.get("company") for job in (structured_data.get("work_experience") or []) if job.get("company")],
                        "degrees": [edu.get("degree") for edu in (structured_data.get("education") or []) if edu.get("degree")],
                        
                        # Legacy fields for backward compatibility with Scorer
                        "skill_score": float(cand.get('skill_score', 0) or 0),
                        "experience_bonus": float(cand.get('experience_bonus', 0) or 0)
                    }
                    vectors_to_upsert.append({
                        "id": compact_id,
                        "values": emb_summary,
                        "metadata": meta_summary
                    })
                
                # B. Experience Vectors
                work_exp = structured_data.get('work_experience') or []
                for idx_exp, exp in enumerate(work_exp):
                    exp_role = exp.get('role') or 'Unknown Role'
                    exp_company = exp.get('company') or 'Unknown Company'
                    
                    exp_text = f"Role: {exp_role}\nCompany: {exp_company}\nDescription: {exp.get('description') or ''}"
                    emb_exp = openai.embed_content(exp_text)
                    
                    if emb_exp:
                        meta_exp = {
                            "candidate_id": cand_id,
                            "name": name,
                            "type": "experience",
                            "position": position, 
                            "role_cluster": role_cluster,
                            "company": exp_company,
                            "exp_role": exp_role,
                            "duration": int(exp.get('duration_years') or 0)
                        }
                        vectors_to_upsert.append({
                            "id": f"{compact_id}_exp_{idx_exp}",
                            "values": emb_exp,
                            "metadata": meta_exp
                        })

                # Upsert remaining for this candidate (Inside TRY)
                if vectors_to_upsert:
                     pinecone.upsert(vectors_to_upsert)
                 
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
