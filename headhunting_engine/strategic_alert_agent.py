
import json
import os
import sys
import sqlite3
from datetime import datetime

class StrategicAlertAgent:
    def __init__(self, notion_db, analytics_db):
        self.notion = notion_db
        self.db = analytics_db

    def check_scarcity_spikes(self, current_scarcity_snapshot: Dict, prev_snapshot_path: str):
        """[v5] Detects >20% increase in JD Scarcity for active roles."""
        if not os.path.exists(prev_snapshot_path): return []
        
        with open(prev_snapshot_path, 'r', encoding='utf-8') as f:
            prev_snapshot = json.load(f).get("skill_frequency", {})
            
        alerts = []
        for skill, current_val in current_scarcity_snapshot.items():
            prev_val = prev_snapshot.get(skill)
            if prev_val and current_val > prev_val * 1.2:
                alerts.append(f"Scarcity Spike for {skill}: {prev_val:.2f} -> {current_val:.2f} (+{((current_val/prev_val)-1)*100:.1f}%)")
        return alerts

    def check_role_gaps(self, active_jds: List[Dict], scarcity_engine):
        """[v5] Identify patterns in high JD demand but low DB frequency."""
        demand_counts = collections.Counter()
        for jd in active_jds:
            for pattern in jd.get("experience_patterns", []):
                demand_counts[pattern] += 1
        
        gaps = []
        for pattern, count in demand_counts.items():
            scarcity = scarcity_engine.get_scarcity(pattern)
            if scarcity > 0.8 and count >= 2:
                gaps.append(f"Role Gap Detected: '{pattern}' has high demand ({count} active JDs) but critical scarcity ({scarcity:.2f})")
        return gaps

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

    def post_alerts(self, current_scarcity: Dict, prev_scarcity_path: str, active_jds: List[Dict], scarcity_engine):
        """Collects all alerts and posts them to Notion."""
        print("🚀 Running Phase 5 Strategic Alert Sweep...")
        
        scarcity_alerts = self.check_scarcity_spikes(current_scarcity, prev_scarcity_path)
        role_gap_alerts = self.check_role_gaps(active_jds, scarcity_engine)
        drift_alerts = self.find_jd_drifts()
        
        all_alerts = scarcity_alerts + role_gap_alerts + drift_alerts
        
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
