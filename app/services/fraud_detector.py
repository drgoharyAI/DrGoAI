"""
Fraud Detector
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
from app.models.fhir_models import ParsedClinicalData

class FraudDetector:
    def __init__(self):
        self.provider_stats = {}
        self.patient_stats = {}
        logger.info("✓ Fraud Detector initialized")
    
    def detect_fraud(self, clinical_data: ParsedClinicalData) -> Dict[str, Any]:
        """Detect potential fraud patterns in the request"""
        result = {
            "fraud_flags": [],
            "fraud_risk": "LOW",
            "risk_score": 0.0,
            "requires_investigation": False
        }
        
        provider_id = clinical_data.provider_id
        patient_id = clinical_data.patient_id
        
        # Track provider patterns
        if provider_id not in self.provider_stats:
            self.provider_stats[provider_id] = {"requests": 0, "high_cost": 0, "dates": []}
        
        self.provider_stats[provider_id]["requests"] += 1
        self.provider_stats[provider_id]["dates"].append(datetime.utcnow())
        
        # Check for unusual patterns
        if clinical_data.total_cost and clinical_data.total_cost > 50000:
            self.provider_stats[provider_id]["high_cost"] += 1
            result["fraud_flags"].append("high_cost_claim")
            result["risk_score"] += 0.3
        
        # Check request frequency
        if self._check_frequency_anomaly(provider_id):
            result["fraud_flags"].append("high_frequency")
            result["risk_score"] += 0.2
        
        # Check for unusual service combinations
        if self._check_service_anomaly(clinical_data):
            result["fraud_flags"].append("unusual_service_combination")
            result["risk_score"] += 0.2
        
        # Determine fraud risk level
        if result["risk_score"] >= 0.7:
            result["fraud_risk"] = "HIGH"
            result["requires_investigation"] = True
        elif result["risk_score"] >= 0.5:
            result["fraud_risk"] = "MEDIUM"
            result["requires_investigation"] = True
        elif result["risk_score"] >= 0.3:
            result["fraud_risk"] = "LOW_MEDIUM"
        
        logger.info(f"Fraud analysis: Provider={provider_id}, Risk={result['fraud_risk']}, Score={result['risk_score']:.2f}")
        
        return result
    
    def _check_frequency_anomaly(self, provider_id: str) -> bool:
        stats = self.provider_stats[provider_id]
        if len(stats["dates"]) < 10:
            return False
        
        # Check if more than 20 requests in last 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        recent = sum(1 for d in stats["dates"] if d > cutoff)
        return recent > 20
    
    def _check_service_anomaly(self, clinical_data: ParsedClinicalData) -> bool:
        # Check for unusual number of services
        if len(clinical_data.services) > 10:
            return True
        return False

fraud_detector = FraudDetector()
