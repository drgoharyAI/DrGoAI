"""
Rules Engine Service
Applies insurance policy rules and business logic
"""
from typing import Dict, Any, List, Tuple, Optional
import yaml
from pathlib import Path
from loguru import logger
from app.models.fhir_models import ParsedClinicalData
from app.models.response_models import DecisionType
from app.config.settings import settings

class RulesEngineService:
    """Apply insurance policy rules to adjudication requests"""
    
    def __init__(self):
        self.rules = self._load_rules()
        logger.info("Rules engine initialized")
    
    def _load_rules(self) -> Dict[str, Any]:
        """Load rules from YAML configuration"""
        rules_path = Path(settings.RULES_CONFIG_PATH)
        
        if not rules_path.exists():
            logger.warning(f"Rules file not found: {rules_path}")
            return {}
        
        with open(rules_path, 'r') as f:
            rules = yaml.safe_load(f)
        
        logger.info(f"Loaded {len(rules)} rule categories")
        return rules
    
    def evaluate_request(self, clinical_data: ParsedClinicalData) -> Dict[str, Any]:
        """
        Evaluate request against all rules
        
        Returns:
            Dict with:
            - auto_decision: Optional[DecisionType] if rules make automatic decision
            - rules_triggered: List of rule IDs that matched
            - rule_results: Detailed results for each rule check
            - risk_flags: Any risk indicators
        """
        results = {
            "auto_decision": None,
            "rules_triggered": [],
            "rule_results": {},
            "risk_flags": [],
            "confidence": 1.0
        }
        
        # 1. Check auto-deny rules (highest priority)
        auto_deny = self._check_auto_deny_rules(clinical_data)
        if auto_deny["triggered"]:
            results["auto_decision"] = DecisionType.DENIED
            results["rules_triggered"].extend(auto_deny["rules"])
            results["rule_results"]["auto_deny"] = auto_deny
            return results
        
        # 2. Check coverage and eligibility
        coverage_check = self._check_coverage_rules(clinical_data)
        results["rule_results"]["coverage"] = coverage_check
        if not coverage_check["passed"]:
            results["auto_decision"] = DecisionType.DENIED
            results["rules_triggered"].extend(coverage_check["rules"])
            return results
        
        # 3. Check service-specific rules
        service_checks = self._check_service_rules(clinical_data)
        results["rule_results"]["service_rules"] = service_checks
        results["rules_triggered"].extend(service_checks["rules_triggered"])
        
        # 4. Check age restrictions
        age_check = self._check_age_restrictions(clinical_data)
        results["rule_results"]["age_restrictions"] = age_check
        if not age_check["passed"]:
            results["auto_decision"] = DecisionType.DENIED
            results["rules_triggered"].extend(age_check["rules"])
            return results
        
        # 5. Check frequency limits
        frequency_check = self._check_frequency_limits(clinical_data)
        results["rule_results"]["frequency"] = frequency_check
        if not frequency_check["passed"]:
            results["auto_decision"] = DecisionType.DENIED
            results["rules_triggered"].append("frequency_limit_exceeded")
            return results
        
        # 6. Check cost thresholds
        cost_check = self._check_cost_thresholds(clinical_data)
        results["rule_results"]["cost_thresholds"] = cost_check
        if cost_check["requires_review"]:
            results["risk_flags"].append("high_cost_service")
        
        # 7. Check medical necessity triggers
        necessity_check = self._check_medical_necessity_triggers(clinical_data)
        results["rule_results"]["medical_necessity"] = necessity_check
        if necessity_check["requires_review"]:
            results["risk_flags"].extend(necessity_check["triggers"])
        
        # 8. Check auto-approve conditions (lowest priority)
        auto_approve = self._check_auto_approve_rules(clinical_data)
        if auto_approve["triggered"] and not results["risk_flags"]:
            results["auto_decision"] = DecisionType.APPROVED
            results["rules_triggered"].extend(auto_approve["rules"])
            results["confidence"] = 0.9  # High confidence for auto-approve
        
        return results
    
    def _check_auto_deny_rules(self, data: ParsedClinicalData) -> Dict[str, Any]:
        """Check automatic denial conditions"""
        result = {"triggered": False, "rules": [], "reasons": []}
        
        auto_deny_rules = self.rules.get("coverage_rules", {}).get("auto_deny", [])
        
        # Check excluded services
        excluded = self.rules.get("excluded_services", [])
        for service in data.services:
            service_type = self._classify_service_type(service)
            if service_type in excluded:
                result["triggered"] = True
                result["rules"].append(f"excluded_service_{service_type}")
                result["reasons"].append(f"Service {service_type} is not covered")
        
        # Check diagnoses for excluded conditions
        for diagnosis in data.diagnoses:
            if self._is_excluded_diagnosis(diagnosis):
                result["triggered"] = True
                result["rules"].append("excluded_diagnosis")
                result["reasons"].append(f"Diagnosis {diagnosis['code']} not covered")
        
        return result
    
    def _check_coverage_rules(self, data: ParsedClinicalData) -> Dict[str, Any]:
        """Verify coverage and eligibility"""
        result = {"passed": True, "rules": [], "details": {}}
        
        # Basic coverage validation
        if not data.coverage_id or data.coverage_id == "unknown":
            result["passed"] = False
            result["rules"].append("no_valid_coverage")
            result["details"]["coverage"] = "No valid coverage found"
        
        # Check if provider is in network (simplified - would need provider database)
        # This is a placeholder for actual network verification
        result["details"]["network_status"] = "in_network"  # Default assumption
        
        return result
    
    def _check_service_rules(self, data: ParsedClinicalData) -> Dict[str, Any]:
        """Check service-specific requirements"""
        result = {"rules_triggered": [], "service_checks": []}
        
        service_rules = self.rules.get("service_rules", {})
        
        for service in data.services:
            service_check = {
                "service_code": service["code"],
                "requires_preauth": False,
                "requires_referral": False,
                "limits_applied": []
            }
            
            # Classify service type
            service_type = self._classify_service_type(service)
            
            # Check if service requires pre-authorization
            prior_auth_services = self.rules.get("prior_auth_required", {}).get("procedures", [])
            if service_type in prior_auth_services:
                service_check["requires_preauth"] = True
                result["rules_triggered"].append(f"preauth_required_{service_type}")
            
            # Check cost limits for service type
            if service_type in service_rules:
                type_rules = service_rules[service_type]
                if "maximum_cost" in type_rules and service.get("net_amount"):
                    if service["net_amount"] > type_rules["maximum_cost"]:
                        result["rules_triggered"].append(f"cost_limit_exceeded_{service_type}")
                        service_check["limits_applied"].append("maximum_cost_exceeded")
            
            result["service_checks"].append(service_check)
        
        return result
    
    def _check_age_restrictions(self, data: ParsedClinicalData) -> Dict[str, Any]:
        """Check age-based restrictions"""
        result = {"passed": True, "rules": [], "details": {}}
        
        if not data.patient_age:
            # If age unknown, flag for review but don't auto-deny
            result["details"]["age"] = "Age unknown - requires verification"
            return result
        
        age_restrictions = self.rules.get("age_restrictions", {})
        
        # Determine age category
        if data.patient_age <= 14:
            age_category = "pediatric"
        elif data.patient_age <= 59:
            age_category = "adult"
        else:
            age_category = "elderly"
        
        result["details"]["age_category"] = age_category
        result["details"]["patient_age"] = data.patient_age
        
        # Check service-specific age restrictions (would need more complex logic)
        # This is simplified
        
        return result
    
    def _check_frequency_limits(self, data: ParsedClinicalData) -> Dict[str, Any]:
        """Check frequency and utilization limits"""
        result = {"passed": True, "limits_checked": []}
        
        # This would require historical claims data
        # Simplified implementation for demonstration
        frequency_limits = self.rules.get("frequency_limits", {})
        
        for service in data.services:
            service_type = self._classify_service_type(service)
            if service_type in frequency_limits:
                limit_info = frequency_limits[service_type]
                result["limits_checked"].append({
                    "service": service_type,
                    "max_per_year": limit_info.get("max_per_year", "unlimited"),
                    "current_usage": "unknown"  # Would need claims history
                })
        
        return result
    
    def _check_cost_thresholds(self, data: ParsedClinicalData) -> Dict[str, Any]:
        """Check cost-based decision thresholds"""
        result = {"requires_review": False, "threshold_level": None}
        
        if not data.total_cost:
            return result
        
        thresholds = self.rules.get("cost_thresholds", {})
        
        if data.total_cost <= thresholds.get("auto_approve_max", 5000):
            result["threshold_level"] = "auto_approve_eligible"
        elif data.total_cost <= thresholds.get("require_medical_review_min", 50000):
            result["threshold_level"] = "medical_review"
            result["requires_review"] = True
        else:
            result["threshold_level"] = "senior_review"
            result["requires_review"] = True
        
        result["total_cost"] = data.total_cost
        
        return result
    
    def _check_medical_necessity_triggers(self, data: ParsedClinicalData) -> Dict[str, Any]:
        """Check for medical necessity review triggers"""
        result = {"requires_review": False, "triggers": []}
        
        review_triggers = self.rules.get("medical_necessity", {}).get("review_triggers", [])
        
        # Check for experimental procedures
        for service in data.services:
            if "experimental" in service.get("description", "").lower():
                result["requires_review"] = True
                result["triggers"].append("experimental_procedure")
        
        # Check for high-cost services
        if data.total_cost and data.total_cost > 50000:
            result["requires_review"] = True
            result["triggers"].append("high_cost_service")
        
        # Check for missing documentation
        required_docs = self.rules.get("medical_necessity", {}).get("required_documentation", [])
        if not data.clinical_notes and "clinical_notes" in required_docs:
            result["triggers"].append("missing_clinical_notes")
        
        return result
    
    def _check_auto_approve_rules(self, data: ParsedClinicalData) -> Dict[str, Any]:
        """Check automatic approval conditions"""
        result = {"triggered": False, "rules": [], "reasons": []}
        
        # Simplified auto-approve logic
        if data.total_cost and data.total_cost <= 500:
            # Low-cost services
            for service in data.services:
                service_type = self._classify_service_type(service)
                if service_type == "consultation":
                    result["triggered"] = True
                    result["rules"].append("low_cost_consultation")
                    result["reasons"].append("Low-cost consultation under auto-approve threshold")
        
        return result
    
    def _classify_service_type(self, service: Dict[str, Any]) -> str:
        """Classify service into categories"""
        description = service.get("description", "").lower()
        code = service.get("code", "")
        
        # Simple classification based on keywords
        if any(kw in description for kw in ["consult", "visit", "exam"]):
            return "consultation"
        elif any(kw in description for kw in ["surgery", "operation"]):
            return "surgery"
        elif any(kw in description for kw in ["mri", "ct", "scan", "xray", "x-ray"]):
            return "diagnostics"
        elif any(kw in description for kw in ["therapy", "rehabilitation"]):
            return "therapy"
        elif any(kw in description for kw in ["medication", "drug", "prescription"]):
            return "pharmacy"
        else:
            return "other"
    
    def _is_excluded_diagnosis(self, diagnosis: Dict[str, str]) -> bool:
        """Check if diagnosis is in excluded list"""
        # Simplified check - would need comprehensive diagnosis mapping
        excluded_keywords = ["cosmetic", "fertility", "experimental"]
        display = diagnosis.get("display", "").lower()
        return any(kw in display for kw in excluded_keywords)
    
    def get_rule_explanation(self, rule_id: str) -> str:
        """Get human-readable explanation for a rule"""
        explanations = {
            "excluded_service_cosmetic_surgery": "Cosmetic surgery is not covered under the policy",
            "excluded_service_fertility_treatment": "Fertility treatments require special coverage",
            "no_valid_coverage": "No active insurance coverage found",
            "frequency_limit_exceeded": "Service frequency limit has been exceeded",
            "cost_limit_exceeded": "Service cost exceeds policy maximum",
            "preauth_required": "This service requires prior authorization"
        }
        
        return explanations.get(rule_id, f"Rule {rule_id} was triggered")

# Global instance
rules_engine = RulesEngineService()
