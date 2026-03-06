import sys
import os
import sqlite3
import json

# Add project root to sys.path
sys.path.append(os.getcwd())

from headhunting_engine.matching.scorer import Scorer

def main():
    print("🚀 AI Talent Intelligence OS v6.2 Engine Starting...")
    
    # Check DB status
    db_path = "headhunting_engine/data/analytics.db"
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM candidate_snapshots WHERE data_json LIKE '%v6_2_data%'")
        migrated_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM candidate_snapshots")
        total_count = cursor.fetchone()[0]
        
    print(f"📊 Database Status: {migrated_count}/{total_count} candidates migrated to v6.2")
    
    print("\n--- Available Commands ---")
    print("1. [Test] Run Scorer Validation (verification script)")
    print("2. [Search] Run Search Pipeline (pipeline_v4)")
    print("3. [Migrate] Run Data Migration (remigrate any pending data)")
    print("exit. Exit")
    
    while True:
        cmd = input("\nSelect command: ").strip().lower()
        if cmd == "1":
            os.system("python tests/test_v6_2_scoring.py")
        elif cmd == "2":
            os.system("python search_pipeline_v4.py")
        elif cmd == "3":
            os.system("python scripts/migrate_v6_2.py")
        elif cmd in ["exit", "q"]:
            break
        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()
