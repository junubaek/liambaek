
import json
import urllib.request
import urllib.error
import time

class NotionClient:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def _request(self, method, endpoint, payload=None):
        url = f"https://api.notion.com/v1/{endpoint}"
        data = json.dumps(payload).encode('utf-8') if payload else None
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(f"Notion API Error {e.code}: {e.read().decode('utf-8')}")
            return None
        except Exception as e:
            print(f"Network Error: {e}")
            return None

    def create_page(self, parent_db_id, properties, children=None):
        """Creates a new page in the specified database."""
        payload = {
            "parent": {"database_id": parent_db_id},
            "properties": properties
        }
        if children:
            payload["children"] = children
            
        return self._request("POST", "pages", payload)

    def get_page(self, page_id):
        """Retrieves a Page object."""
        return self._request("GET", f"pages/{page_id}")

    def update_page_properties(self, page_id, properties):
        """Updates properties of an existing page."""
        payload = {"properties": properties}
        return self._request("PATCH", f"pages/{page_id}", payload)

    def archive_page(self, page_id):
        """Archives (deletes) a page in Notion."""
        payload = {"archived": True}
        return self._request("PATCH", f"pages/{page_id}", payload)

    def update_database(self, db_id, properties):
        """Updates database schema (e.g. adding properties)."""
        payload = {"properties": properties}
        return self._request("PATCH", f"databases/{db_id}", payload)

    def query_database(self, db_id, limit=None, filter_criteria=None):
        """Query database with pagination support."""
        all_results = []
        has_more = True
        next_cursor = None
        
        while has_more:
            payload = {}
            if limit and not has_more: 
                # Optimization: if limit reached in first page? No, let's keep it simple.
                # If limit is specified and we have enough, break?
                pass
            
            if filter_criteria:
                payload["filter"] = filter_criteria
                
            if next_cursor:
                payload["start_cursor"] = next_cursor
            
            # Use default page size (100) or limit if small
            if limit and limit < 100:
                payload["page_size"] = limit
            else:
                 payload["page_size"] = 100
                 
            res = self._request("POST", f"databases/{db_id}/query", payload)
            if not res:
                break
                
            results = res.get('results', [])
            all_results.extend(results)
            
            if limit and len(all_results) >= limit:
                all_results = all_results[:limit]
                break
                
            has_more = res.get('has_more', False)
            next_cursor = res.get('next_cursor')
            
        return {"results": all_results}

    def search_db_by_name(self, name):
        """Finds a database ID by its title."""
        payload = {
            "query": name,
            "filter": {
                "value": "database",
                "property": "object"
            }
        }
        res = self._request("POST", "search", payload)
        if res and res.get('results'):
            # 1. Try Exact Match
            for result in res['results']:
                try:
                    title_obj = result.get('title', [])
                    title_text = "".join([t.get('plain_text', '') for t in title_obj])
                    if title_text.strip() == name:
                        return result['id']
                except Exception:
                    continue
            
            # 2. Fallback: Return first result (Scanning heuristic)
            return res['results'][0]['id']
            
        return None

    def query_database(self, db_id, limit=None, filter_criteria=None):
        """Fetches pages from the database with pagination."""
        url = f"https://api.notion.com/v1/databases/{db_id}/query"
        results = []
        has_more = True
        cursor = None
        
        print(f"  [Notion] Querying DB {db_id}...")
        
        while has_more:
            payload = {"page_size": 100} # Max allowed by Notion API
            if cursor:
                payload["start_cursor"] = cursor
            
            if filter_criteria:
                payload["filter"] = filter_criteria
                
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=self.headers, method="POST")
            
            try:
                with urllib.request.urlopen(req) as response:
                    res_json = json.loads(response.read().decode('utf-8'))
                    results.extend(res_json.get('results', []))
                    
                    has_more = res_json.get('has_more', False)
                    cursor = res_json.get('next_cursor')
                    
                    if limit and len(results) >= limit:
                        results = results[:limit]
                        break
                        
                    # print(f"    - Fetched {len(results)} rows so far...")
                    
            except Exception as e:
                print(f"Notion Query Error: {e}")
                break
                
        return {"results": results}

    def get_page_full_text(self, page_id):
        """Fetches all text content from a page's blocks."""
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        req = urllib.request.Request(url, headers=self.headers, method="GET")
        
        full_text = []
        
        try:
            with urllib.request.urlopen(req) as response:
                res = json.loads(response.read().decode('utf-8'))
                blocks = res.get('results', [])
                
                for block in blocks:
                    btype = block['type']
                    text_content = ""
                    
                    # Extract text based on block type
                    if btype in ['paragraph', 'heading_1', 'heading_2', 'heading_3', 'bulleted_list_item', 'numbered_list_item', 'to_do', 'toggle']:
                        rich_text = block[btype].get('rich_text', [])
                        text_content = "".join([t['plain_text'] for t in rich_text])
                        
                    if text_content.strip():
                        full_text.append(text_content)
                        
            return "\n".join(full_text)
            
        except Exception as e:
            print(f"Error fetching page content for {page_id}: {e}")
            return ""

    def extract_properties(self, page):
        """Parses a Notion page into a simplified dictionary."""
        props = page.get('properties', {})
        data = {"id": page['id'], "url": page.get('url')}
        
        for name, prop in props.items():
            ptype = prop['type']
            value = None
            
            # Simple extraction logic for common types
            if ptype == 'title':
                value = "".join([t['plain_text'] for t in prop['title']])
            elif ptype == 'rich_text':
                value = "".join([t['plain_text'] for t in prop['rich_text']])
            elif ptype == 'select':
                value = prop['select']['name'] if prop['select'] else None
            elif ptype == 'number':
                value = prop['number']
            elif ptype == 'status':
                value = prop['status']['name'] if prop['status'] else None
            elif ptype == 'url':
                value = prop['url']
            elif ptype == 'email':
                value = prop['email']
            elif ptype == 'multi_select':
                value = [opt['name'] for opt in prop['multi_select']]
            elif ptype == 'checkbox':
                value = prop['checkbox']
            elif ptype == 'phone_number':
                value = prop['phone_number']

            # Normalize keys to snake_case
            clean_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
            data[clean_name] = value

        # Add Metadata (Outside loop)
        data['created_time'] = page.get('created_time')
        data['last_edited_time'] = page.get('last_edited_time')
            
        return data

# Wrapper for specific business logic
class HeadhunterDB:
    def __init__(self, secrets_path="secrets.json"):
        with open(secrets_path, "r") as f:
            self.secrets = json.load(f)
        self.client = NotionClient(self.secrets["NOTION_API_KEY"])
        
    def fetch_candidates(self, limit=50, filter_criteria=None):
        # Prefer "Vector DB" for clean slate, fallback to "DB"
        db_id = self.client.search_db_by_name("Vector DB")
        if not db_id:
             db_id = self.client.search_db_by_name("DB")
             
        if not db_id:
            print("Database 'Vector DB' or 'DB' not found.")
            return []
            
        print(f"Fetching candidates from DB ({db_id})...")
        # Use query_database (now supports pagination)
        # Pass a large limit if we want all, e.g. 5000 or None for all
        res = self.client.query_database(db_id, limit=limit, filter_criteria=filter_criteria)
        candidates = []
        if res and 'results' in res:
            for page in res['results']:
                candidates.append(self.client.extract_properties(page))
        return candidates

    def fetch_history(self, limit=100):
        db_id = self.client.search_db_by_name("PROGRAM")
        if not db_id:
            print("Database 'PROGRAM' not found.")
            return []
            
        print(f"Fetching history from PROGRAM ({db_id})...")
        res = self.client.query_database(db_id, limit)
        history = []
        if res:
            for page in res['results']:
                history.append(self.client.extract_properties(page))
        return history

    def fetch_candidate_details(self, page_id):
        """Fetches full text content for a specific candidate."""
        return self.client.get_page_full_text(page_id)

    def update_candidate(self, page_id, properties):
        """Updates candidate metadata in Notion."""
        return self.client.update_page_properties(page_id, properties)

    def search_db_id(self, name_or_id):
        # Wrapper to find ID by name or just verify ID
        # ... logic if needed, or just let main leverage client directly ...
        # For now, just exposing client methods via db.client is enough for main_ingest.
        pass

if __name__ == "__main__":
    # Test block
    db = HeadhunterDB()
    # cands = db.fetch_candidates(limit=5)
    # print(json.dumps(cands, indent=2, ensure_ascii=False))
    hist = db.fetch_history(limit=5)
    print(json.dumps(hist, indent=2, ensure_ascii=False))
