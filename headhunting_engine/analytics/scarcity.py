import json
import os
from typing import Dict, List, Set

class ScarcityEngine:
    """
    Calculates Skill Scarcity based on snapshot-based candidate pool frequency.
    Snapshot-based calculation ensures stability in RPL and difficulty metrics.
    """
    def __init__(self, snapshot_path: str = None):
        self.skill_frequency = {} # node_id -> internal scarcity (0.0 - 1.0)
        self.market_proxy = {}    # node_id -> market scarcity (0.0 - 1.0)
        self.snapshot = {}        # node_id -> full stats (v3/v4)
        self.total_candidates = 0
        
        # [v1.3.1.2] Market Scarcity Proxies (Default/Simulated)
        # 1.0 = Extremely Rare in Market, 0.0 = Abundant
        self.default_market_proxies = {
            "Language_Python": 0.2,
            "Language_Java": 0.3,
            "Cloud_AWS": 0.4,
            "DL_Framework": 0.7,
            "Embedded_C": 0.8,
            "MLOps": 0.9,
            "Language_C_Plus_Plus": 0.5,
            "DB_SQL": 0.3
        }
        
        if snapshot_path:
            self.load_snapshot(snapshot_path)

    def create_snapshot(self, candidates: List[Dict], output_path: str, canonical_ids: Set[str] = None):
        """
        [v4] Market Domination Radar
        Scarcity = (1-DB_Coverage)*0.5 + (Depth_Ratio)*0.3 + (Market_Proxy)*0.2
        """
        self.total_candidates = len(candidates)
        raw_counts = {}
        weighted_counts = {}
        
        depth_multipliers = {"Mentioned": 0.5, "Applied": 1.0, "Architected": 1.5}

        for c in candidates:
            skills = c.get("skills_depth", [])
            seen_in_cand = set()
            
            for s in skills:
                node = s["name"]
                if canonical_ids and node not in canonical_ids and not node.startswith("__TEMP__"):
                    node = f"__TEMP__{node}"
                
                depth = s.get("depth", "Mentioned")
                weight = depth_multipliers.get(depth, 1.0)
                
                if node not in seen_in_cand:
                    raw_counts[node] = raw_counts.get(node, 0) + 1
                    seen_in_cand.add(node)
                
                weighted_counts[node] = weighted_counts.get(node, 0) + weight
        
        snapshot_data = {}
        for node in set(raw_counts.keys()):
            coverage_rate = raw_counts.get(node, 0) / self.total_candidates
            depth_ratio = (weighted_counts.get(node, 0) / raw_counts.get(node, 1)) / 1.5 # Normalized by max depth
            market_proxy = self.default_market_proxies.get(node, 0.5) 
            
            # Phase 4 Hybrid Formula
            final_scarcity = ((1.0 - coverage_rate) * 0.5) + ((1.0 - depth_ratio) * 0.3) + (market_proxy * 0.2)
            final_scarcity = round(max(0.0, min(1.0, final_scarcity)), 4)
            
            self.skill_frequency[node] = final_scarcity
            snapshot_data[node] = {
                "coverage_rate": round(coverage_rate, 4),
                "depth_ratio": round(depth_ratio, 4),
                "market_proxy": market_proxy,
                "final_scarcity": final_scarcity
            }
        
        snapshot = {
            "snapshot_date": "ISO_DATE",
            "total_candidates": self.total_candidates,
            "skill_data": snapshot_data,
            "skill_frequency": self.skill_frequency
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2)

    def load_snapshot(self, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.skill_frequency = data.get("skill_frequency", {})
            self.total_candidates = data.get("total_candidates", 0)

    def get_scarcity(self, node_id: str, canonical_ids: Set[str] = None) -> float:
        """
        [v1.3.1.2] Returns StrategicScarcity = Internal*0.6 + MarketProxy*0.4
        """
        lookup_node = node_id
        if canonical_ids is not None and node_id not in canonical_ids and not node_id.startswith("__TEMP__"):
            lookup_node = f"__TEMP__{node_id}"
            
        internal_scarcity = self.skill_frequency.get(lookup_node, 1.0)
        
        # Get Market Proxy (Use default or simulate for unknowns)
        market_scarcity = self.default_market_proxies.get(node_id)
        if market_scarcity is None:
            # Simulate: If internally very rare and not in proxy, market scarcity is likely high too
            market_scarcity = min(0.95, internal_scarcity * 1.1)
        
        # Combined Strategic Scarcity
        strategic_scarcity = (internal_scarcity * 0.6) + (market_scarcity * 0.4)
        return round(max(0.0, min(1.0, strategic_scarcity)), 4)

    def identify_strategic_gaps(self, threshold: float = 0.9, use_internal_only: bool = False) -> List[Dict]:
        """
        Returns skills with high scarcity. 
        Returns list of dicts with internal/market/strategic breakdown.
        """
        gaps = []
        for node in self.skill_frequency.keys():
            internal = self.skill_frequency.get(node, 1.0)
            strategic = self.get_scarcity(node)
            
            target_val = internal if use_internal_only else strategic
            if target_val >= threshold:
                gaps.append({
                    "node": node,
                    "internal": round(internal, 4),
                    "strategic": round(strategic, 4),
                    "is_market_rare": self.default_market_proxies.get(node, 0) > 0.7
                })
        
        return sorted(gaps, key=lambda x: x["strategic"], reverse=True)

    def load_snapshot(self, path: str):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.snapshot = json.load(f)
            # Backward compatibility: populate skill_frequency from snapshot
            for node_id, data in self.snapshot.items():
                # If it's the old format, it might be just a dict of scores
                if isinstance(data, dict):
                    self.skill_frequency[node_id] = data.get("final_scarcity", data.get("scarcity_score", 0.5))
                else:
                    self.skill_frequency[node_id] = data
        
    def calculate_depth_weighted_scarcity(self, skill_name: str, impact_weight: float = 1.0) -> float:
        """
        [v4] Effective Supply = Σ (DepthWeight × ImpactWeight)
        Scarcity = 1 - (Effective Supply / Weighted Capacity)
        """
        node = self.snapshot.get(skill_name, {})
        depth_weights = {"Mentioned": 0.3, "Executed": 0.7, "Led": 1.0, "Architected": 1.3}
        
        if not node: 
            return self.skill_frequency.get(skill_name, 0.8)
        
        dist = node.get("depth_distribution", {})
        total_weighted_supply = 0
        for depth, count in dist.items():
            total_weighted_supply += count * depth_weights.get(depth, 0.3) * impact_weight
        
        role_pool_size = node.get("role_pool_size", self.total_candidates or 100)
        weighted_capacity = role_pool_size * 1.3 # Max capacity assuming all are Architected
        
        scarcity = 1.0 - (total_weighted_supply / weighted_capacity)
        return round(max(0.0, min(1.0, scarcity)), 4)

    def calculate_jd_scarcity(self, must_skills: List[str]) -> float:
        """
        [v3.1] Unified JD Scarcity Calculation
        """
        if not must_skills: return 0.0
        return round(sum(self.calculate_depth_weighted_scarcity(s) for s in must_skills) / len(must_skills), 4)

    def calculate_rare_talent_utility(self, pool: List[Dict]) -> float:
        """
        [v3.1] Ratio of candidates with Scarcity > 0.8 and Depth >= Applied
        """
        rare_count = 0
        if not pool: return 0.0
        for cand in pool:
            has_rare = False
            for s in cand.get("skills_depth", []):
                sc = self.calculate_depth_weighted_scarcity(s["name"])
                if sc > 0.8 and s.get("depth") in ["Applied", "Architected"]:
                    has_rare = True
                    break
            if has_rare:
                rare_count += 1
        
        return round(rare_count / len(pool), 4)

    def generate_scarcity_heatmap(self, clusters: Dict[str, str] = None) -> Dict:
        """
        [v3.1] Domain x Average Scarcity Heatmap with fallback
        """
        if not clusters:
            # Try to use clusters from snapshot if available
            domains = set()
            for v in self.snapshot.values():
                if isinstance(v, dict) and v.get('cluster'):
                    domains.add(v['cluster'])
            
            if not domains: return {}
            
            return {domain: self.calculate_jd_scarcity([s for s, v in self.snapshot.items() if isinstance(v, dict) and v.get('cluster') == domain]) 
                    for domain in domains}
        
        heatmap = {}
        for skill_name, cluster in clusters.items():
            sc = self.calculate_depth_weighted_scarcity(skill_name)
            if cluster not in heatmap: heatmap[cluster] = []
            heatmap[cluster].append(sc)
            
        return {k: round(sum(v)/len(v), 4) for k, v in heatmap.items() if v}

    def calculate_cross_scarcity(self, skill_a: str, skill_b: str, role_pool: List[Dict]) -> float:
        """
        [v3.1] 1 - (Candidates with Skill A AND Skill B / Total Role Pool)
        """
        if not role_pool: return 1.0
        match_count = sum(1 for c in role_pool if 
                          any(s["name"] == skill_a for s in c.get("skills_depth", [])) and
                          any(s["name"] == skill_b for s in c.get("skills_depth", [])))
        return round(1.0 - (match_count / len(role_pool)), 4)

    def get_strategic_gaps_summary(self, top_n=10) -> List[Dict]:
        """
        [v3.1] Sorted list of highest scarcity skills
        """
        gaps = []
        source = self.snapshot if self.snapshot else self.skill_frequency
        for s in source:
            gaps.append({"skill": s, "scarcity": self.calculate_depth_weighted_scarcity(s)})
        
        gaps.sort(key=lambda x: x["scarcity"], reverse=True)
        return gaps[:top_n]
