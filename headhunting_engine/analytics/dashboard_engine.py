
import json
from typing import List, Dict

class DashboardEngine:
    def __init__(self, scarcity_snapshot_path: str, dictionary_path: str):
        with open(scarcity_snapshot_path, 'r', encoding='utf-8') as f:
            self.scarcity_snapshot = json.load(f)
        
        with open(dictionary_path, 'r', encoding='utf-8') as f:
            self.dictionary = json.load(f)
            self.role_families = self.dictionary.get("role_families", {})
            self.clusters = self.dictionary.get("capability_clusters", {})
            
            # Map skills to clusters for domain equity
            self.skill_to_cluster = {}
            for node, data in self.dictionary.get("canonical_skill_nodes", {}).items():
                self.skill_to_cluster[node] = data.get("cluster")

    def calculate_enterprise_kpis(self, pool: List[Dict], scarcity_engine=None) -> Dict:
        """
        [v3] Enterprise Talent Capital Analytics
        """
        if not pool: return {}

        # 1. Talent Capital Stats
        total_n = len(pool)
        equity_by_role = {k: 0 for k in self.role_families.keys()}
        equity_by_domain = {k: 0 for k in self.clusters.keys()}
        
        total_applied = 0
        total_arch = 0
        rare_skills_count = 0
        total_skills_mapped = 0
        s_count = 0
        a_count = 0
        
        sum_raw = 0
        total_ascending = 0

        for c in pool:
            grade = c.get("career_path_grade")
            if grade == "S": s_count += 1
            elif grade == "A": a_count += 1
            
            sum_raw += c.get("base_talent_score", 50)
            if c.get("career_trajectory") == "Ascending":
                total_ascending += 1

            cand_clusters = set()
            for s in c.get("skills_depth", []):
                s_name = s.get("name")
                depth = s.get("depth", "Mentioned")
                weight = 1 if depth == "Applied" else (2 if depth == "Architected" else 0)
                
                if weight > 0:
                    cluster = self.skill_to_cluster.get(s_name)
                    if cluster:
                        equity_by_domain[cluster] = equity_by_domain.get(cluster, 0) + weight
                        cand_clusters.add(cluster)
                
                if depth == "Applied": total_applied += 1
                elif depth == "Architected": total_arch += 1
                
                # Check rarity from snapshot data
                rarity_data = self.scarcity_snapshot.get("skill_data", {}).get(s_name, {})
                s_val = rarity_data.get("final_scarcity", 0) if isinstance(rarity_data, dict) else 0
                if s_val > 0.8: rare_skills_count += 1
                total_skills_mapped += 1

            if cand_clusters:
                # Map clusters to roles
                cluster_to_role = {
                    "Backend_Systems": "SW_Backend", "Model_Development": "AI_Engineering",
                    "System_Optimization": "Embedded_Systems", "Data_Infrastructure": "DATA_Engineering",
                    "Infra_Cloud": "SW_Platform"
                }
                for clus in cand_clusters:
                    role = cluster_to_role.get(clus)
                    if role: equity_by_role[role] = equity_by_role.get(role, 0) + 1

        # 2. Capital Health
        elite_cands = [c for c in pool if c.get('career_path_grade') in ['S', 'A']]
        elite_ratio = len(elite_cands) / len(pool)
        
        rare_utility = 0.0
        heatmap = {}
        top_gaps = []
        if scarcity_engine:
            rare_utility = scarcity_engine.calculate_rare_talent_utility(pool)
            heatmap = scarcity_engine.generate_scarcity_heatmap(self.skill_to_cluster)
            top_gaps = scarcity_engine.get_strategic_gaps_summary(top_n=10)

        return {
            "tier_1_health": {
                "raw_mean": round(sum_raw / total_n, 2),
                "applied_ratio_pct": round(total_applied / max(1, total_skills_mapped) * 100, 1),
                "ascending_ratio_pct": round(total_ascending / total_n * 100, 1)
            },
            "tier_2_capital": {
                "total_equity": total_applied + (total_arch * 2),
                "elite_counts": {"S": s_count, "A": a_count},
                "elite_ratio_pct": round((s_count + a_count) / total_n * 100, 1),
                "rare_utility": round(rare_skills_count / max(1, total_skills_mapped), 2),
                "equity_by_role": equity_by_role,
                "equity_by_domain": equity_by_domain
            },
            "tier_3_intelligence": {
                "scarcity_heatmap": heatmap,
                "strategic_gaps": scarcity_engine.get_strategic_gaps_summary() if scarcity_engine else []
            }
        }
