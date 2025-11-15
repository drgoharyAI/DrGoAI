"""
Financial Risk Analyzer
"""
from typing import Dict, Any, List
from loguru import logger
from app.models.fhir_models import ParsedClinicalData
from app.models.response_models import ServiceDecision

class FinancialRiskAnalyzer:
    def __init__(self):
        # Average costs for procedures (would be loaded from database)
        self.procedure_avg_costs = {
            "27447": 45000,  # TKR
            "27130": 50000,  # THR
            "33510": 150000,  # CABG
            "92928": 80000,  # PCI
        }
        self.outlier_threshold = 2.0  # 2x average
        logger.info("✓ Financial Risk Analyzer initialized")
    
    def analyze_financial_risk(self, clinical_data: ParsedClinicalData, service_decisions: List[ServiceDecision]) -> Dict[str, Any]:
        """Analyze financial risk of the request"""
        result = {
            "risk_flags": [],
            "risk_score": 0.0,
            "risk_level": "LOW",
            "cost_analysis": {},
            "requires_review": False
        }
        
        if not clinical_data.total_cost:
            return result
        
        total_cost = clinical_data.total_cost
        
        # Check total cost threshold
        if total_cost > 100000:
            result["risk_flags"].append("high_total_cost")
            result["risk_score"] += 0.3
        
        # Check individual service costs
        for service in clinical_data.services:
            service_cost = service.get("net_amount", 0)
            service_code = service.get("code", "")
            
            if service_code in self.procedure_avg_costs:
                avg_cost = self.procedure_avg_costs[service_code]
                
                if service_cost > avg_cost * self.outlier_threshold:
                    result["risk_flags"].append(f"cost_outlier_{service_code}")
                    result["risk_score"] += 0.2
                    
                    result["cost_analysis"][service_code] = {
                        "requested": service_cost,
                        "average": avg_cost,
                        "ratio": service_cost / avg_cost
                    }
        
        # Determine risk level
        if result["risk_score"] >= 0.5:
            result["risk_level"] = "HIGH"
            result["risk_flags"].append("requires_financial_review")
            result["requires_review"] = True
        elif result["risk_score"] >= 0.3:
            result["risk_level"] = "MEDIUM"
            result["requires_review"] = True
        
        return result

financial_risk_analyzer = FinancialRiskAnalyzer()
