import os
import json
import statistics
from collections import Counter

def run_audit():
    resume_dir = r"C:\Users\cazam\Downloads\02_resume 전처리"
    structured_json_path = r"headhunting_engine\analytics\processed_pool_notion.json"
    dictionary_path = r"headhunting_engine\dictionary\canonical_dictionary_v1.json"
    
    print("🔍 Starting DB Integrity & Asset Audit (Phase 2)...")
    
    # 1. Physical File Count
    file_stats = Counter()
    if os.path.exists(resume_dir):
        for root, dirs, files in os.walk(resume_dir):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in ['.doc', '.docx', '.pdf']:
                    file_stats[ext] += 1
    
    total_physical_files = sum(file_stats.values())
    print(f"📁 Total Physical Files Found: {total_physical_files}")
    for ext, count in file_stats.items():
        print(f"  - {ext}: {count}")

    # 2. Structured JSON Audit
    if not os.path.exists(structured_json_path):
        print(f"❌ Structured JSON not found: {structured_json_path}")
        return

    with open(structured_json_path, 'r', encoding='utf-8') as f:
        candidates = json.load(f)
    
    total_candidates = len(candidates)
    print(f"📊 Total Structured Candidates: {total_candidates}")
    
    # 3. Dictionary Coverage Audit
    with open(dictionary_path, 'r', encoding='utf-8') as f:
        dictionary = json.load(f)
    canonical_ids = set(dictionary.get("canonical_skill_nodes", {}).keys())
    
    # Metrics
    schema_compliance = []
    positions = []
    base_scores = []
    career_grades = []
    unmapped_skills = Counter()
    mapped_count = 0
    total_skill_instances = 0
    
    for c in candidates:
        # Schema Check
        has_skills = "canonical_skill_nodes" in c
        has_score = "base_talent_score" in c
        has_career = "career_path_grade" in c
        is_compliant = has_skills and has_score and has_career
        schema_compliance.append(is_compliant)
        
        # Position
        pos = c.get("position", "Unclassified")
        positions.append(pos)
        
        # Scores
        score = c.get("base_talent_score", 0)
        base_scores.append(score)
        
        # Career Grade
        grade = c.get("career_path_grade", "Neutral")
        career_grades.append(grade)
        
        # Skills Gap
        for skill in c.get("canonical_skill_nodes", []):
            total_skill_instances += 1
            if skill.startswith("__TEMP__"):
                unmapped_skills[skill.replace("__TEMP__", "")] += 1
            elif skill in canonical_ids:
                mapped_count += 1
            else:
                # Skill instance not prefixed but not in dict (anomaly)
                unmapped_skills[skill] += 1

    unique_positions = Counter(positions)
    grade_counter = Counter()
    for s in base_scores:
        if s >= 85: grade_counter['S'] += 1
        elif s >= 75: grade_counter['A'] += 1
        elif s >= 65: grade_counter['B'] += 1
        elif s >= 50: grade_counter['C'] += 1
        else: grade_counter['D'] += 1
        
    career_dist = Counter(career_grades)
    
    # Calculation
    compliance_rate = (sum(schema_compliance) / total_candidates) * 100 if total_candidates > 0 else 0
    unmapped_skill_rate = (len(unmapped_skills) / total_skill_instances * 100) if total_skill_instances > 0 else 0
    
    # Top Unmapped
    top_unmapped = unmapped_skills.most_common(50)
    
    report = {
        "summary": {
            "total_physical_files": total_physical_files,
            "total_structured": total_candidates,
            "schema_compliance_rate": f"{compliance_rate:.1f}%",
            "avg_base_score": round(statistics.mean(base_scores), 2) if base_scores else 0,
            "median_base_score": statistics.median(base_scores) if base_scores else 0,
        },
        "distributions": {
            "grades": dict(grade_counter),
            "career_path": dict(career_dist),
            "positions_count": len(unique_positions),
            "top_10_positions": dict(unique_positions.most_common(10))
        },
        "skill_gap": {
            "unmapped_skill_instances": sum(unmapped_skills.values()),
            "total_skill_instances": total_skill_instances,
            "gap_rate": f"{unmapped_skill_rate:.1f}%",
            "top_50_unmapped": top_unmapped
        }
    }
    
    # Output Report
    report_path = "headhunting_engine/analytics/db_integrity_report_v1.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n--- 📈 DB Integrity Audit Report ---")
    print(f"Compliance Rate: {report['summary']['schema_compliance_rate']}")
    print(f"Avg Base Score: {report['summary']['avg_base_score']} (Median: {report['summary']['median_base_score']})")
    print(f"Grade Dist: {report['distributions']['grades']}")
    print(f"Career Path Dist: {report['distributions']['career_path']}")
    print(f"Unique Positions: {report['distributions']['positions_count']}")
    print(f"Skill Gap Rate: {report['skill_gap']['gap_rate']}")
    print(f"Top 5 Unmapped Skills: {top_unmapped[:5]}")
    print(f"\n✅ Full report saved to: {report_path}")

if __name__ == "__main__":
    run_audit()
