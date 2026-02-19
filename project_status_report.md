# Project Status Report (2026-02-19)

## 1. Project Overview
**Goal**: Automate resume recruiting pipeline (PDF -> Notion -> AI Analysis -> Search Dashboard).
**Current State**: Fully functional ingestion pipeline with deduplication and incremental update support.

## 2. Core Scripts (Keep These)
| File | Purpose | Status |
| :--- | :--- | :--- |
| `pdf_to_notion.py` | Uploads local PDF/DOC files to Notion. Checks for duplicates by filename. | **Active** (Incremental) |
| `main_ingest.py` | Fetches candidates from Notion, analyzes with LLM, and indexes in Pinecone. | **Active** (Incremental via `AI_Generated` flag) |
| `deduplicate_notion.py` | Finds duplicates in Notion and archives the older/less complete ones. | **Active** (Run periodically) |
| `app.py` | Streamlit Search Dashboard for recruiters. | **Active** |
| `matcher.py` | Core search and matching logic (Hybrid search). | **Active** |
| `interactive_search.py` | CLI tool for testing search logic. | **Utility** |

## 3. Library/Config Files (Keep These)
- `connectors/` (Folder): Contains API wrappers for Notion, Pinecone, OpenAI.
- `secrets.json`: API Keys and Database IDs. **(CRITICAL)**
- `requirements.txt`: Python dependencies.

## 4. Cleanup Candidates (Safe to Delete/Archive)
The following files were created for features that are no longer used (Google Drive Auto-Upload).
- `google_drive_uploader.py`: Script for OAuth Google Drive upload. (User opted for manual upload).
- `client_secret.json`: Google OAuth Credentials.
- `token.pickle`: Google OAuth Token.
- `create_db_for_user.py`: Utility used once to set up Notion DB. (Can keep for reference or delete).
- `clear_pinecone.py`: Utility to wipe the vector DB. (Keep only if you need to reset often).

## 5. Recent Logic Updates
1.  **Incremental Ingestion**: `main_ingest.py` now defaults to processing only candidates where `AI_Generated` is unchecked.
2.  **Deduplication**: `deduplicate_notion.py` prioritizes candidates with **Contact Info (Email/Phone)** and then **Recency**.
3.  **PDF Parsing**: Improved text extraction from `.doc` and `.docx` files.

## 6. How to Run
1.  **Upload New Files**: `python pdf_to_notion.py`
2.  **Analyze & Index**: `python main_ingest.py`
3.  **Remove Duplicates**: `python deduplicate_notion.py`
4.  **Launch App**: `streamlit run app.py`
