import json
from typing import Dict, List

class JDIntelligenceLayer:
    """
    JD Intelligence Layer (v5): Monitors JD structural risks and pattern integrity.
    """
    def __init__(self, risk_engine):
        self.risk_engine = risk_engine

    def analyze_jd_risk(self, jd_signals: Dict) -> Dict:
        """Analyzes structural risks in a JD (Pattern Density, Constraint Severity)."""
        patterns = jd_signals.get("experience_patterns", [])
        constraints = jd_signals.get("hard_constraints", [])
        
        analysis = {
            "structural_status": "Healthy",
            "warnings": [],
            "severity_score": 0.0
        }
        
        # 1. Pattern Density Warning
        if len(patterns) > 5:
            analysis["warnings"].append("⚠️ [PATTERN DENSITY] JD requires too many execution patterns (>5). Risk of 'Unicorn JD'.")
            analysis["structural_status"] = "At Risk"
            
        # 2. Constraint Hardness
        severity = len(constraints) * 0.15 # 0.15 per hard constraint
        analysis["severity_score"] = round(min(1.0, severity), 2)
        if severity > 0.5:
            analysis["warnings"].append("❌ [CONSTRAINT HARDNESS] High number of hard constraints detected. Expected sourcing time will increase.")
            
        # 3. Predict Risk (Integrated with RiskEngine v4)
        risk_forecast = self.risk_engine.predict_risk(
            jd_signals.get("functional_domains", []), 
            patterns
        )
        
        analysis["forecast"] = risk_forecast["forecast"]
        analysis["transparency"] = risk_forecast["transparency_layer"]
        
        return analysis

if __name__ == "__main__":
    # Test stub
    pass
