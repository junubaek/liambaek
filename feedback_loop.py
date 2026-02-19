
import json
import hashlib
from datetime import datetime
from connectors.notion_api import HeadhunterDB

class FeedbackLoop:
    def __init__(self):
        self.db = HeadhunterDB()
        self.history_cache = []

    def load_history(self):
        """Fetches and caches the 'PROGRAM' history."""
        # print("Loading Matching History from Notion...")
        # In a real app, we might filter by 'Status'='Pass'/'Hired' inside the Notion Query
        # Here we fetch all and filter in memory for simplicity
        raw_history = self.db.fetch_history(limit=100)
        
        self.history_cache = []
        for record in raw_history:
            # User mentioned 'PROGRAM' has: Date, Company, Position, Stage, Resume
            # We assume 'Stage' or 'Status' indicates success.
            # Example stages: 'Document Pass', 'Interview Pass', 'Offer', 'Hired'
            stage = str(record.get('stage', '') or record.get('status', '')).lower()
            
            is_successful = any(keyword in stage for keyword in ['pass', 'hired', 'offer', '합격', '성공'])
            
            if is_successful:
                # Need to link 'Resume' (Relation or Title) to Candidate ID if possible.
                # Since we don't have direct Relation ID -> Page ID mapping easily without more API calls,
                # we will rely on Name Matching for this MVP.
                
                # 'Resume' field in PROGRAM DB might be the candidate's name.
                resume_val = record.get('resume') or record.get('이력서') or "Unknown"
                
                self.history_cache.append({
                    "jd_name": record.get('position', 'Unknown Position'),
                    "company": record.get('company', 'Unknown Company'),
                    "candidate_name": resume_val, 
                    "stage": stage
                })
        
        # print(f"Loaded {len(self.history_cache)} successful matches from history.")

    def find_successful_profiles_for_jd(self, jd_title):
        """
        Returns a list of successful candidate profiles for a similar JD.
        Simple logic: Keyword match on JD Title. 
        Advanced: Vector search on JD description (future improvement).
        """
        # Lazy load
        if not self.history_cache:
            self.load_history()
            
        matches = []
        keywords = jd_title.lower().split()
        
        for record in self.history_cache:
            hist_jd = record['jd_name'].lower()
            # Simple overlap check
            if any(k in hist_jd for k in keywords if len(k) > 2):
                matches.append(record)
                
        return matches


    def log_feedback(self, jd_text, candidate_name, candidate_id, feedback_type, comments=""):
        """Logs user feedback with ID support."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "context_id": hashlib.md5(jd_text.encode()).hexdigest(),
            "candidate": candidate_name,
            "candidate_id": candidate_id, # ID-based tracking
            "type": feedback_type,
            "comments": comments
        }
        # In a real app, append to JSON or DB
        try:
             import os
             history = []
             if os.path.exists("feedback_log.json"):
                 with open("feedback_log.json", "r", encoding="utf-8") as f:
                     history = json.load(f)
             history.append(entry)
             with open("feedback_log.json", "w", encoding="utf-8") as f:
                 json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error logging feedback: {e}")

if __name__ == "__main__":
    # Test
    loop = FeedbackLoop()
    loop.load_history()
    
    test_jd = "Ethernet Firmware"
    print(f"\nSearching success cases for '{test_jd}'...")
    success_cases = loop.find_successful_profiles_for_jd(test_jd)
    for case in success_cases:
        print(f" - Found: {case['candidate_name']} (Stage: {case['stage']}) at {case['company']}")
