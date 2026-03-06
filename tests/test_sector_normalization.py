import sys
import os
sys.path.append(os.getcwd())
from scripts.batch_notion_score_sync import calculate_z_scores

def test_z_normalization():
    print("🧪 Running Sector-based Z-Normalization Mathematical Audit...")
    
    # Case 1: High variance group (Standard spread)
    scores_high = [10.0, 50.0, 90.0]
    norm_high = calculate_z_scores(scores_high)
    print(f"  - Group A (Full Range): {scores_high} -> {norm_high}")
    
    # Case 2: Elite group (Small variance at top)
    # 85 should be penalized RELATIVELY within this group
    scores_low = [85.0, 88.0, 90.0]
    norm_low = calculate_z_scores(scores_low)
    print(f"  - Group B (Elite Cluster): {scores_low} -> {norm_low}")
    
    # Case 3: Underperforming group
    # 30 should look good RELATIVELY in a very poor group
    scores_poor = [10.0, 15.0, 30.0]
    norm_poor = calculate_z_scores(scores_poor)
    print(f"  - Group C (Low Cluster): {scores_poor} -> {norm_poor}")
    
    # Case 4: Solo candidate (Automatic Peak)
    scores_solo = [75.0]
    norm_solo = calculate_z_scores(scores_solo)
    print(f"  - Group D (Solo Peak): {scores_solo} -> {norm_solo}")
    
    # Case 5: Zero variance (Flat mean)
    scores_same = [70.0, 70.0, 70.0]
    norm_same = calculate_z_scores(scores_same)
    print(f"  - Group E (Uniform Mean): {scores_same} -> {norm_same}")

    # Validation
    assert norm_high[0] < norm_high[1] < norm_high[2]
    assert norm_low[0] < norm_low[1] < norm_low[2]
    assert norm_solo[0] == 100.0
    assert norm_same[0] == 50.0

    print("✅ Z-Normalization Test Passed. Mathematical model is stable.")

if __name__ == "__main__":
    test_z_normalization()
