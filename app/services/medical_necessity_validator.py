"""
Medical Necessity Validator
"""
from typing import Dict, Any, List
from loguru import logger
from app.models.fhir_models import ParsedClinicalData
from app.models.response_models import ServiceDecision

class MedicalNecessityValidator:
    def __init__(self):
        self.icd_cpt_mappings = {
            "M17": ["27447"], "M16": ["27130"], "I25": ["33510", "92928"],
            "E11": ["99213"], "I50": ["33510"]
        }
        self.guidelines = {
            "27447": {"min_age": 45, "max_age": 85, "conservative_months": 6},
            "27130": {"min_age": 45, "max_age": 85, "conservative_months": 6},
            "33510": {"min_age": 30, "max_age": 85}
        }
        logger.info("✓ Medical Necessity Validator initialized")
    
    def validate(self, clinical_data: ParsedClinicalData, service_decisions: List[ServiceDecision]) -> Dict[str, Any]:
        """Validate medical necessity for all services"""
        validations = []
        all_valid = True
        
        for service_decision in service_decisions:
            result = self._validate_single(clinical_data, service_decision)
            validations.append(result)
            if not result["valid"]:
                all_valid = False
        
        return {
            "overall_valid": all_valid,
            "validations": validations,
            "flags": [v["flags"] for v in validations if v["flags"]],
            "score": sum(v["score"] for v in validations) / len(validations) if validations else 1.0
        }
    
    def _validate_single(self, clinical_data: ParsedClinicalData, service_decision: ServiceDecision) -> Dict[str, Any]:
        """Validate single service"""
        result = {"valid": True, "score": 1.0, "flags": []}
        
        service_code = service_decision.service_code
        
        # Check diagnosis-procedure match
        if not self._check_diagnosis_match(clinical_data, service_code):
            result["flags"].append("diagnosis_mismatch")
            result["score"] -= 0.2
        
        # Check age
        if not self._check_age(clinical_data, service_code):
            result["flags"].append("age_inappropriate")
            result["score"] -= 0.15
        
        if len(result["flags"]) >= 2:
            result["valid"] = False
        
        result["score"] = max(0.5, result["score"])
        return result
    
    def _check_diagnosis_match(self, clinical_data: ParsedClinicalData, service_code: str) -> bool:
        if not clinical_data.diagnoses:
            return True
        for diag in clinical_data.diagnoses:
            icd_prefix = diag.get("code", "")[:3]
            if icd_prefix in self.icd_cpt_mappings:
                if service_code in self.icd_cpt_mappings[icd_prefix]:
                    return True
        return False
    
    def _check_age(self, clinical_data: ParsedClinicalData, service_code: str) -> bool:
        if service_code not in self.guidelines or not clinical_data.patient_age:
            return True
        gl = self.guidelines[service_code]
        return gl.get("min_age", 0) <= clinical_data.patient_age <= gl.get("max_age", 120)

medical_necessity_validator = MedicalNecessityValidator()
