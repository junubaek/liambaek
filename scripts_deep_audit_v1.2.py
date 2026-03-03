import json
import statistics
import os
from collections import Counter

def run_deep_audit():
    reparsed_json_path = r"headhunting_engine\analytics\reparsed_pool_v1.2.json"
    dictionary_path = r"headhunting_engine\dictionary\canonical_dictionary_v1.json"
    
    if not os.path.exists(reparsed_json_path):
        print(f"❌ Reparsed JSON not found: {reparsed_json_path}")
        return

    with open(reparsed_json_path, 'r', encoding='utf-8') as f:
        candidates = json.load(f)
    
    with open(dictionary_path, 'r', encoding='utf-8') as f:
        dictionary = json.load(f)
    
    total_count = len(candidates)
    print(f"🔍 Deep Audit: Analysing {total_count} candidates...")
    
    # 1. Base Score Distribution
    raw_scores = [c.get("base_talent_score") for c in candidates]
    scores = [s for s in raw_scores if s is not None]
    avg_score = statistics.mean(scores) if scores else 0
    median_score = statistics.median(scores) if scores else 0
    
    grades = Counter()
    for s in scores:
        if s >= 85: grades['S'] += 1
        elif s >= 75: grades['A'] += 1
        elif s >= 65: grades['B'] += 1
        elif s >= 50: grades['C'] += 1
        else: grades['D'] += 1
        
    grade_ratio = {k: f"{(v/total_count)*100:.1f}%" for k, v in grades.items()}

    # 2. Career Path Grade Distribution
    career_grades = Counter([c.get("career_path_grade", "Unknown") for c in candidates])
    career_ratio = {k: f"{(v/total_count)*100:.1f}%" for k, v in career_grades.items()}

    # 3. Skill Coverage
    skill_counts = [len(c.get("canonical_skill_nodes", [])) for c in candidates]
    avg_skills = statistics.mean(skill_counts) if skill_counts else 0
    
    all_skills = []
    for c in candidates:
        all_skills.extend(c.get("canonical_skill_nodes", []))
    top_skills = Counter(all_skills).most_common(20)
    
    # 4. Domain / Position Distribution (Bias Check)
    positions = Counter([c.get("position", "Unclassified") for c in candidates])
    
    # 5. Gate Condition Check
    gate_ok = avg_skills >= 3.0
    
    report = {
        "summary": {
            "total_candidates": total_count,
            "avg_base_score": round(avg_score, 2),
            "median_base_score": median_score,
            "avg_skills_per_candidate": round(avg_skills, 2)
        },
        "grade_distribution": {
            "counts": dict(grades),
            "ratios": grade_ratio
        },
        "career_path_distribution": dict(career_ratio),
        "top_20_skills": dict(top_skills),
        "domain_bias_check": {
            "unique_positions": len(positions),
            "top_10_positions": dict(positions.most_common(10))
        },
        "gate_status": {
            "avg_skills_ge_3": gate_ok,
            "current_status": "WARM (Partially Visible)" if gate_ok else "COLD (Still in Blackout)"
        }
    }
    
    # Save to report
    report_path = "headhunting_engine/analytics/deep_audit_v1.2_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    print("\n--- ❄️ Cold Evaluation Results ---")
    print(f"Avg Base Score: {report['summary']['avg_base_score']} (Median: {report['summary']['median_base_score']})")
    print(f"Grade Ratios: {report['grade_distribution']['ratios']}")
    print(f"Career Ratios: {report['career_path_distribution']}")
    print(f"Avg Skills: {report['summary']['avg_skills_per_candidate']} (Gate: 3.0)")
    print(f"Top 5 Skills: {list(report['top_20_skills'].keys())[:5]}")
    print(f"Status: {report['gate_status']['current_status']}")

if __name__ == "__main__":
    run_deep_audit()
