"""
Patient History Analyzer
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
from app.models.fhir_models import ParsedClinicalData

class PatientHistoryAnalyzer:
    def __init__(self):
        # In-memory storage (production would use database)
        self.patient_history = {}
        logger.info("✓ Patient History Analyzer initialized")
    
    def analyze_history(self, clinical_data: ParsedClinicalData) -> Dict[str, Any]:
        """Analyze patient's historical claims patterns"""
        patient_id = clinical_data.patient_id
        
        result = {
            "flags": [],
            "prior_requests": 0,
            "ytd_cost": 0,
            "frequency_violation": False,
            "risk_score": 0.0
        }
        
        if patient_id not in self.patient_history:
            self.patient_history[patient_id] = []
            return result
        
        history = self.patient_history[patient_id]
        result["prior_requests"] = len(history)
        
        # Check for duplicates (same service within 30 days)
        for service in clinical_data.services:
            if self._is_duplicate(history, service):
                result["flags"].append("duplicate_request")
                result["risk_score"] += 0.2
                break
        
        # Calculate YTD cost
        ytd_cost = sum(h.get("cost", 0) for h in history 
                      if self._is_current_year(h.get("date")))
        result["ytd_cost"] = ytd_cost
        
        # Check frequency
        if self._check_frequency_violation(history, clinical_data):
            result["flags"].append("frequency_violation")
            result["frequency_violation"] = True
            result["risk_score"] += 0.3
        
        # Store current request
        self.patient_history[patient_id].append({
            "date": datetime.utcnow().isoformat(),
            "services": clinical_data.services,
            "cost": clinical_data.total_cost or 0
        })
        
        return result
    
    def _is_duplicate(self, history: List[Dict], service: Dict) -> bool:
        cutoff = datetime.utcnow() - timedelta(days=30)
        for entry in history:
            entry_date = datetime.fromisoformat(entry.get("date", "2000-01-01"))
            if entry_date > cutoff:
                for s in entry.get("services", []):
                    if s.get("code") == service.get("code"):
                        return True
        return False
    
    def _is_current_year(self, date_str: str) -> bool:
        if not date_str:
            return False
        try:
            date = datetime.fromisoformat(date_str)
            return date.year == datetime.utcnow().year
        except:
            return False
    
    def _check_frequency_violation(self, history: List[Dict], clinical_data: ParsedClinicalData) -> bool:
        # Simplified: check if more than 10 requests this year
        current_year_requests = sum(1 for h in history if self._is_current_year(h.get("date")))
        return current_year_requests > 10

patient_history_analyzer = PatientHistoryAnalyzer()
