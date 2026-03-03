
import json
import os
from headhunting_engine.analytics.dashboard_engine import DashboardEngine
from headhunting_engine.analytics.scarcity import ScarcityEngine

def generate_kpis_v4():
    pool_path = "headhunting_engine/analytics/reparsed_pool_v1.3_elite.json"
    scarcity_path = "headhunting_engine/analytics/scarcity_snapshot.json"
    dict_path = "headhunting_engine/dictionary/canonical_dictionary_v1.json"
    
    if not os.path.exists(pool_path) or not os.path.exists(scarcity_path):
        print("❌ Error: Elite Pool or Scarcity snapshot not found.")
        return

    # 1. Initialize Engines
    se = ScarcityEngine(scarcity_path)
    de = DashboardEngine(scarcity_path, dict_path)
    
    # 2. Load Pool
    with open(pool_path, 'r', encoding='utf-8') as f:
        pool = json.load(f)
    
    # 3. Calculate Tiered KPIs
    kpis = de.calculate_enterprise_kpis(pool, scarcity_engine=se)
    
    t1 = kpis["tier_1_health"]
    t2 = kpis["tier_2_capital"]
    t3 = kpis["tier_3_intelligence"]

    # 4. Generate Markdown Report
    report = [
        "# 💎 Phase 4: Market Domination Strategic Report",
        f"Generated from pool of {len(pool)} candidates.",
        
        "\n## 🟢 Tier 1: Operational Health (엔진 및 데이터 무결성)",
        f"- **Raw Mean Intensity**: {t1['raw_mean']} (보수적 하드닝 유지 상태)",
        f"- **Applied Skill Ratio**: {t1['applied_ratio_pct']}% (실제 구현 기술 비중)",
        f"- **Career Momentum (Ascending)**: {t1['ascending_ratio_pct']}% (성장 가도 후보 비중)",
        
        "\n## 🔵 Tier 2: Talent Capital (인재 자산 분석)",
        f"- **Total Technical Equity**: **{t2['total_equity']}** (Applied/Arch 가중치 합산 가치)",
        f"- **Elite Layer Ratio**: **{t2['elite_ratio_pct']}%** (상위 S/A 등급 비중)",
        f"- **Elite Counts**: S등급({t2['elite_counts']['S']}) / A등급({t2['elite_counts']['A']})",
        f"- **Rare Talent Utility**: {t2['rare_utility']} (희소 기술 활용도)",
        
        "\n### 2.1 Equity by Role Family (역할군별 자산 집중도)",
    ]
    
    for role, val in t2['equity_by_role'].items():
        if val > 0: report.append(f"- **{role}**: {val}")

    report.append("\n### 2.2 Equity by Domain (기술 도메인별 자산 집중도)")
    for domain, val in t2['equity_by_domain'].items():
        if val > 0: report.append(f"- **{domain}**: {val}")

    report.extend([
        "\n## 🔴 Tier 3: Market Intelligence (시장 지능 및 희소성)",
        "### 3.1 Domain Scarcity Heatmap (기술 도메인별 시장 희소성 - 높을수록 귀함)",
    ])
    
    for domain, heat in t3['scarcity_heatmap'].items():
        report.append(f"- **{domain}**: {heat}")

    report.append("\n### 3.2 Strategic Gaps (Top 10 전략적 공백 기술)")
    for gap in t3['strategic_gaps']:
        node = gap["node"]
        report.append(f"- **{node}**: Scarcity {gap['final_scarcity']} (DB Coverage: {gap['coverage_rate']})")

    report.append("\n## 🚀 Conclusion")
    report.append(f"현재 당신의 DB는 {t2['total_equity']}의 기술 자본을 보유하고 있으며, 특히 {max(t2['equity_by_domain'], key=t2['equity_by_domain'].get)} 분야에서 강한 우위를 점하고 있습니다.")

    report_path = "headhunting_engine/analytics/enterprise_kpi_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
    
    # Save raw JSON
    with open("headhunting_engine/analytics/enterprise_kpi_data_v4.json", 'w', encoding='utf-8') as f:
        json.dump(kpis, f, indent=2, ensure_ascii=False)

    print(f"✅ Phase 4 Enterprise KPIs generated at {report_path}")

if __name__ == "__main__":
    generate_kpis_v4()
