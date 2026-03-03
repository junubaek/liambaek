
import json
import os
from headhunting_engine.analytics.scarcity import ScarcityEngine

def update_scarcity():
    pool_path = "headhunting_engine/analytics/reparsed_pool_v1.2.json"
    snapshot_path = "headhunting_engine/analytics/scarcity_snapshot.json"
    dict_path = "headhunting_engine/dictionary/canonical_dictionary_v1.json"

    with open(pool_path, 'r', encoding='utf-8') as f:
        candidates = json.load(f)

    with open(dict_path, 'r', encoding='utf-8') as f:
        dictionary = json.load(f)
        canonical_ids = set(dictionary.get("canonical_skill_nodes", {}).keys())

    engine = ScarcityEngine()
    engine.create_snapshot(candidates, snapshot_path, canonical_ids=canonical_ids)
    print(f"✅ Scarcity Snapshot updated with {len(candidates)} candidates.")

if __name__ == "__main__":
    update_scarcity()
