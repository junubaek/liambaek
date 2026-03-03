
import sqlite3
import json
import os
import sys
from datetime import datetime

# SSoT (Single Source of Truth) Definition:
# - Notion: Workflow & State (The "Live" data)
# - SQLite: Analytics & History (The "Memory" and "Intelligence" data)

class AnalyticsDB:
    def __init__(self, db_path="headhunting_engine/data/analytics.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # 1. Candidate Snapshots (To track profile attribute drifts)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS candidate_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notion_id TEXT,
                    name TEXT,
                    role TEXT,
                    experience_years REAL,
                    data_json TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 2. JD Snapshots (To track market difficulty/scarcity drifts)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jd_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jd_id TEXT,
                    role TEXT,
                    scarcity REAL,
                    difficulty REAL,
                    success_rate REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 3. Lifecycle Events (To calculate conversion rates)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS lifecycle_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id TEXT,
                    jd_id TEXT,
                    stage TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_candidate_snapshot(self, notion_id, name, role, exp, raw_data):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO candidate_snapshots (notion_id, name, role, experience_years, data_json) VALUES (?, ?, ?, ?, ?)",
                (notion_id, name, role, exp, json.dumps(raw_data))
            )
            conn.commit()

    def save_jd_snapshot(self, jd_id, role, scarcity, difficulty, success_rate):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO jd_snapshots (jd_id, role, scarcity, difficulty, success_rate) VALUES (?, ?, ?, ?, ?)",
                (jd_id, role, scarcity, difficulty, success_rate)
            )
            conn.commit()

    def log_lifecycle_event(self, candidate_id, jd_id, stage):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO lifecycle_events (candidate_id, jd_id, stage) VALUES (?, ?, ?)",
                (candidate_id, jd_id, stage)
            )
            conn.commit()

    def get_latest_jd_stats(self, jd_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT scarcity, difficulty, success_rate, timestamp FROM jd_snapshots WHERE jd_id = ? ORDER BY timestamp DESC LIMIT 1",
                (jd_id,)
            )
            return cursor.fetchone()

class DataSync:
    def __init__(self, notion_db, analytics_db):
        self.notion = notion_db
        self.db = analytics_db

    def sync_from_notion(self):
        """Pulls latest states from Notion and snapshots them in SQLite."""
        print("Starting Data Core Sync: Notion -> SQLite...")
        
        # 1. Sync Candidates (Vector DB / DB)
        candidates = self.notion.fetch_candidates(limit=None)
        for cand in candidates:
            self.db.save_candidate_snapshot(
                cand.get('id'),
                cand.get('name') or cand.get('이름'),
                cand.get('포지션'),
                cand.get('total_years'),
                cand
            )
        
        # 2. Sync JDs (SEARCH)
        searches = self.notion.fetch_searches(limit=100)
        for s in searches:
            # For analytics, we should calculate or fetch scarcity/difficulty here?
            # For now, snapshot the metadata.
            self.db.save_jd_snapshot(
                s.get('id'),
                s.get('포지션'),
                0.5, # Default Placeholder if not calculated
                0.5,
                0.1  # Default success rate
            )

        # 3. Sync Project Links (PROJECT)
        projects = self.notion.fetch_projects(limit=500)
        for p in projects:
            # Log as lifecycle events if possible
            cand_link = p.get('후보자') # Assuming it's a relation/title
            jd_link = p.get('포지션')
            status = p.get('전형단계') or p.get('status')
            if cand_link and jd_link:
                 self.db.log_lifecycle_event(str(cand_link), str(jd_link), str(status))
        
        print(f"Sync Complete: {len(candidates)} candidates, {len(searches)} JDs, {len(projects)} links.")

if __name__ == "__main__":
    # Test script
    workspace_path = r"c:\Users\cazam\Downloads\안티그래비티"
    if workspace_path not in sys.path:
        sys.path.append(workspace_path)
    
    from connectors.notion_api import HeadhunterDB
    
    notion_db = HeadhunterDB(os.path.join(workspace_path, "secrets.json"))
    analytics_db = AnalyticsDB(os.path.join(workspace_path, "headhunting_engine/data/analytics.db"))
    
    syncer = DataSync(notion_db, analytics_db)
    syncer.sync_from_notion()
