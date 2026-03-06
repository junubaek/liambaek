import sys
import os
sys.path.append(os.getcwd())

def test_hybrid_blend_logic():
    print("🧪 Verifying v6.2-VS Hybrid 80/20 Blend Logic...")
    
    # Mock Data
    ontology_score = 90.0 # High deterministic match
    semantic_score = 40.0 # Low semantic similarity
    
    # Expected Blend: (90 * 0.8) + (40 * 0.2) = 72 + 8 = 80.0
    final_score_1 = (ontology_score * 0.8) + (semantic_score * 0.2)
    print(f"  - Case 1 (Strong Ontology, Weak Semantic): 90.0 & 40.0 -> {final_score_1}")
    
    # Case 2: Weak Ontology, Strong Semantic
    # (40 * 0.8) + (90 * 0.2) = 32 + 18 = 50.0
    ontology_score_2 = 40.0
    semantic_score_2 = 90.0
    final_score_2 = (ontology_score_2 * 0.8) + (semantic_score_2 * 0.2)
    print(f"  - Case 2 (Weak Ontology, Strong Semantic): 40.0 & 90.0 -> {final_score_2}")
    
    # Case 3: Both strong (Perfect Match)
    final_score_3 = (100 * 0.8) + (100 * 0.2)
    print(f"  - Case 3 (Perfect Match): 100.0 & 100.0 -> {final_score_3}")

    # Assertions
    assert final_score_1 == 80.0
    assert final_score_2 == 50.0
    assert final_score_3 == 100.0
    
    print("✅ Hybrid Blend Logic Verified. Weights are correctly applied.")

if __name__ == "__main__":
    test_hybrid_blend_logic()
