
import json
from headhunting_engine.analytics.scarcity import ScarcityEngine

def test_strategic_gaps():
    snapshot_path = "headhunting_engine/analytics/scarcity_snapshot.json"
    engine = ScarcityEngine(snapshot_path)
    
    gaps = engine.identify_strategic_gaps(threshold=0.95)
    
    print("\n🎯 [Strategic Gaps Identified (Scarcity > 0.95)]")
    for gap_info in gaps[:10]:
        node = gap_info["node"]
        print(f"- {node}: Scarcity {engine.get_scarcity(node)}")

if __name__ == "__main__":
    test_strategic_gaps()
