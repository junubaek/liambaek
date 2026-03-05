import sqlite3
import json
import os

def diagnose_db_v5_3():
    db_path = "headhunting_engine/data/analytics.db"
    if not os.path.exists(db_path):
        print(f"❌ DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    print("📊 --- [Database Diagnostic Report: Phase 5.3] ---")
    
    # 1. Row Counts
    c.execute("SELECT COUNT(*) FROM candidate_snapshots")
    snap_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM candidate_patterns")
    pattern_count = c.fetchone()[0]
    
    print(f"✅ Total Candidates (Data Lake): {snap_count}")
    print(f"✅ Total Indexed Patterns (Search Index): {pattern_count}")
    
    # 2. Role Distribution
    print("\n🎭 --- [Role Cluster Distribution] ---")
    c.execute("SELECT role, COUNT(*) as count FROM candidate_snapshots GROUP BY role ORDER BY count DESC")
    roles = c.fetchall()
    for role, count in roles:
        print(f" - {role or 'Unknown'}: {count}")
    
    # 3. Pattern Sample
    print("\n🧬 --- [Search Index Sample (Top 5)] ---")
    c.execute("SELECT candidate_id, pattern, depth, impact FROM candidate_patterns LIMIT 5")
    samples = c.fetchall()
    for s in samples:
        print(f" - ID: {s[0]} | Pattern: {s[1]} | Depth: {s[2]} | Impact: {s[3]}")
    
    # 4. JSON Structure Check (Data Lake)
    print("\n📦 --- [Data Lake (JSON) Integrity] ---")
    c.execute("SELECT data_json FROM candidate_snapshots LIMIT 1")
    sample_json = c.fetchone()
    if sample_json:
        keys = list(json.loads(sample_json[0]).keys())
        print(f" - Keys found in data_json: {keys}")

    conn.close()

if __name__ == "__main__":
    diagnose_db_v5_3()
