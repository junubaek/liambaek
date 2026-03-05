
import json
import os
from typing import Dict, List, List

from headhunting_engine.analytics.risk_engine import JDRiskEngine

class StrategicScout:
    def __init__(self, scorer, scarcity_engine, risk_engine, pool_v13_path: str):
        self.scorer = scorer
        self.scarcity_engine = scarcity_engine
        self.risk_engine = risk_engine
        self.pool_path = pool_v13_path
        with open(pool_v13_path, 'r', encoding='utf-8') as f:
            self.pool = json.load(f)

    def diagnose_jd(self, must: List[str], nice: List[str] = None) -> Dict:
        """
        [v2] Integrated JD Risk Forecast
        """
        return self.risk_engine.predict_risk(must, nice)

    def match_and_analyze(self, must: List[str], nice: List[str] = None, top_n: int = 10) -> Dict:
        """
        [v2] Elite Candidate Analysis
        """
        results = []
        for cand in self.pool:
            score, details = self.scorer.calculate_score(
                cand.get("skills_depth", []), 
                set(must), 
                set(nice or []), 
                cand
            )
            if score > 0:
                results.append({"cand": cand, "score": score})
        
        results.sort(key=lambda x: x["score"], reverse=True)
        top_matches = results[:top_n]
        
        # Elite Stats
        s_count = sum(1 for r in top_matches if r["cand"].get("career_path_grade") == "S")
        a_count = sum(1 for r in top_matches if r["cand"].get("career_path_grade") == "A")
        
        # Gap Pattern Analysis
        missing_skills = {}
        for node in must:
            found_count = 0
            for r in top_matches:
                if any(s["name"] == node for s in r["cand"].get("skills_depth", [])):
                    found_count += 1
            missing_skills[node] = (top_n - found_count) / top_n if top_n > 0 else 1.0

        major_gaps = [k for k, v in missing_skills.items() if v > 0.5]
        
        return {
            "top_candidate_count": len(top_matches),
            "elite_availability": {"S": s_count, "A": a_count},
            "top_candidates": [{"name": r["cand"]["name"], "score": r["score"], "grade": r["cand"].get("career_path_grade")} for r in top_matches],
            "major_skill_gaps": major_gaps,
            "potential_risk": "Candidate pool thin for requested 'Must' skills" if len(top_matches) < 5 else "Healthy pool"
        }

    def generate_strategic_script(self, diagnosis: Dict, matches: List[Dict]) -> str:
        """
        [v4.2.1] Master Domination Strategic Script with 4-Tier Validation Dashboard
        """
        forecast = diagnosis.get("forecast", {})
        transparency = diagnosis.get("transparency_layer", {})
        
        # 1. Tier 1 - Risk Core
        risk_core = {
            "relevant_pool": transparency.get("relevant_pool_size", 0),
            "elite_matched": transparency.get("elite_matched_count", 0),
            "elite_density": transparency.get("elite_density", 0),
            "avg_must_coverage": transparency.get("avg_must_coverage", 0),
            "scarcity_index": transparency.get("scarcity_index", 0),
            "difficulty_score": forecast.get("difficulty_score", 0),
            "success_rate": forecast.get("success_probability", 0)
        }
        
        # 2. Tier 2 - Scarcity Breakdown (v3)
        rare_utility = self.scarcity_engine.calculate_rare_talent_utility(self.pool)
        scarcity_breakdown = {
            "rare_talent_utility": rare_utility,
            "depth_weighted": True,
            "top_gaps": self.scarcity_engine.get_strategic_gaps_summary(3)
        }
        
        # 3. Tier 3 - Elite Layer
        match_list = matches.get("top_candidates", [])
        s_matched = len([m for m in match_list if m.get("grade") == "S"])
        a_matched = len([m for m in match_list if m.get("grade") == "A"])
        
        # 4. Consistency Alerts
        alerts = transparency.get("consistency_alerts", [])
        alert_str = "\n".join([f"> {a}" for a in alerts]) if alerts else "> ✅ All mathematical constraints satisfied."

        script = f"""
## 💎 [AI Talent Capital Strategic Insight]
- **난이도 판정**: {forecast.get('difficulty_level')} (Score: {forecast.get('difficulty_score')})
- **예상 성공률**: {int(forecast.get('success_probability', 0) * 100)}%
- **예상 소요**: {forecast.get('expected_sourcing_weeks')}주
- **연봉 압력**: {forecast.get('salary_pressure_index')}

## 📊 [Validation Dashboard: 4-Tier Transparency]

### 📐 Tier 1 — Risk Transparency Panel
```json
{json.dumps(risk_core, indent=2)}
```

### 🧠 Tier 2 — Scarcity Breakdown Panel
```json
{json.dumps(scarcity_breakdown, indent=2, ensure_ascii=False)}
```

### 🏆 Tier 3 — Elite Matched Layer
- **Validated S-Grade Pool**: {s_matched}명
- **Validated A-Grade Pool**: {a_matched}명
- **Sourcing Focus**: 핵심 필수 기술 {int(transparency.get('scarcity_index', 0)*100)}% 희소성 대응 타겟팅 후보군 확보.

### ⚖️ Tier 4 — Consistency Guard
{alert_str}

## 🎯 [Sourcing Strategy]
- 현재 DB 내 검증된 엘리트 인재가 {s_matched + a_matched}명 확보되어 있어 즉시 컨택이 가능합니다.
- **성공 확률 {int(forecast.get('success_probability', 0) * 100)}%**를 고려할 때, S등급 최정예 타겟팅과 동시에 A등급 인재에게 +10% 이상의 연봉 프리미엄을 제안하는 'Aggressive Sourcing' 전략이 필요합니다.

---
*본 리포트는 Phase 4.2.1 Mathematical Validation Framework (White-box Engine)에 의해 산출되었습니다.*
"""
        return script
