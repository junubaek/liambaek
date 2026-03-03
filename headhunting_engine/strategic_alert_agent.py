
import json
import os
import sys
import sqlite3
from datetime import datetime

class StrategicAlertAgent:
    def __init__(self, notion_db, analytics_db):
        self.notion = notion_db
        self.db = analytics_db

    def check_elite_depletion(self):
        """Compares current S/A counts with previous snapshots."""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*), strftime('%Y-%m-%d', timestamp) as day 
                FROM candidate_snapshots 
                WHERE experience_years >= 10
                GROUP BY day 
                ORDER BY day DESC LIMIT 2
            """)
            rows = cursor.fetchall()
            
            if len(rows) < 2:
                return None
            
            latest, day_latest = rows[0]
            prev, day_prev = rows[1]
            change = (latest - prev) / prev if prev > 0 else 0
            
            if change < -0.10:
                return f"Elite Depletion detected: {prev} -> {latest} (-{abs(change)*100:.1f}%) since {day_prev}"
            return None

    def find_jd_drifts(self):
        """Checks all active JDs for success rate drifts."""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT jd_id FROM jd_snapshots")
            jd_ids = [r[0] for r in cursor.fetchall()]
            
            alerts = []
            for jid in jd_ids:
                cursor.execute(
                    "SELECT success_rate, timestamp FROM jd_snapshots WHERE jd_id = ? ORDER BY timestamp DESC LIMIT 2",
                    (jid,)
                )
                rows = cursor.fetchall()
                if len(rows) >= 2:
                    diff = rows[0][0] - rows[1][0]
                    if diff < -0.05:
                        alerts.append(f"JD Drift for {jid}: Success rate fell by {abs(diff)*100:.1f}%")
            return alerts

    def post_alerts(self):
        """Collects all alerts and posts them to Notion."""
        print("Running Strategic Alert Check...")
        elite_alert = self.check_elite_depletion()
        drift_alerts = self.find_jd_drifts()
        
        all_alerts = []
        if elite_alert: all_alerts.append(elite_alert)
        all_alerts.extend(drift_alerts)
        
        if not all_alerts:
            print("No strategic alerts found today.")
            return
            
        # For simulation, just print or post to a page
        for alert in all_alerts:
             print(f"🚨 [STRATEGIC ALERT] {alert}")
             # In production: self.notion.client.create_page(alert_db_id, {...})

if __name__ == "__main__":
    workspace_path = r"c:\Users\cazam\Downloads\안티그래비티"
    if workspace_path not in sys.path: sys.path.append(workspace_path)
    from connectors.notion_api import HeadhunterDB
    from headhunting_engine.data_core import AnalyticsDB
    
    n_db = HeadhunterDB(os.path.join(workspace_path, "secrets.json"))
    a_db = AnalyticsDB(os.path.join(workspace_path, "headhunting_engine/data/analytics.db"))
    
    agent = StrategicAlertAgent(n_db, a_db)
    agent.post_alerts()
