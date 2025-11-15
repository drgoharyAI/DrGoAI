"""
Health Declaration (HD) Validator
Validates if medical conditions require health declaration and checks member's HD records
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from loguru import logger
from app.models.fhir_models import ParsedClinicalData

class HealthDeclarationStatus:
    """HD validation status"""
    NOT_REQUIRED = "not_required"
    DECLARED = "declared"
    NOT_DECLARED = "not_declared"
    PRE_EXISTING = "pre_existing"
    NEWLY_DISCOVERED = "newly_discovered"

class HealthDeclarationValidator:
    """
    Validates Health Declaration requirements for insurance claims
    
    Process:
    1. Check if ICD10 codes require health declaration
    2. Query member's HD records from database
    3. Validate if condition was declared
    4. Check policy start date vs condition discovery date
    5. Determine if normal adjudication or HITL is required
    """
    
    def __init__(self):
        # Conditions requiring health declaration (ICD10 codes)
        self.hd_required_conditions = self._load_hd_required_conditions()
        
        # Mock database - In production, replace with actual DB connection
        self.member_hd_database = {}
        
        # Configuration
        self.pre_existing_waiting_period_days = 180  # 6 months waiting period for pre-existing
        
        logger.info("✓ Health Declaration Validator initialized")
        logger.info(f"  Monitoring {len(self.hd_required_conditions)} HD-required conditions")
    
    def _load_hd_required_conditions(self) -> Dict[str, Dict[str, Any]]:
        """
        Load conditions that require health declaration
        
        Returns:
            Dict with ICD10 code as key and condition details as value
        """
        return {
            # Chronic Diseases
            "E11": {
                "name": "Type 2 Diabetes Mellitus",
                "category": "chronic_metabolic",
                "severity": "high",
                "waiting_period_days": 180
            },
            "E10": {
                "name": "Type 1 Diabetes Mellitus", 
                "category": "chronic_metabolic",
                "severity": "high",
                "waiting_period_days": 180
            },
            "I25": {
                "name": "Chronic Ischemic Heart Disease",
                "category": "cardiovascular",
                "severity": "critical",
                "waiting_period_days": 365
            },
            "I10": {
                "name": "Essential Hypertension",
                "category": "cardiovascular",
                "severity": "medium",
                "waiting_period_days": 90
            },
            "I50": {
                "name": "Heart Failure",
                "category": "cardiovascular",
                "severity": "critical",
                "waiting_period_days": 365
            },
            "J45": {
                "name": "Asthma",
                "category": "respiratory",
                "severity": "medium",
                "waiting_period_days": 180
            },
            "J44": {
                "name": "Chronic Obstructive Pulmonary Disease",
                "category": "respiratory",
                "severity": "high",
                "waiting_period_days": 365
            },
            "N18": {
                "name": "Chronic Kidney Disease",
                "category": "renal",
                "severity": "critical",
                "waiting_period_days": 365
            },
            "K70": {
                "name": "Alcoholic Liver Disease",
                "category": "hepatic",
                "severity": "high",
                "waiting_period_days": 365
            },
            "C": {  # Any cancer code starting with C
                "name": "Cancer/Malignant Neoplasms",
                "category": "oncology",
                "severity": "critical",
                "waiting_period_days": 730  # 2 years
            },
            "M05": {
                "name": "Rheumatoid Arthritis",
                "category": "autoimmune",
                "severity": "medium",
                "waiting_period_days": 180
            },
            "G40": {
                "name": "Epilepsy",
                "category": "neurological",
                "severity": "high",
                "waiting_period_days": 180
            },
            "F20": {
                "name": "Schizophrenia",
                "category": "psychiatric",
                "severity": "high",
                "waiting_period_days": 365
            },
            "F31": {
                "name": "Bipolar Disorder",
                "category": "psychiatric",
                "severity": "high",
                "waiting_period_days": 180
            },
        }
    
    def validate_health_declaration(
        self, 
        clinical_data: ParsedClinicalData,
        member_id: str,
        policy_start_date: str
    ) -> Dict[str, Any]:
        """
        Main validation method for health declaration requirements
        
        Args:
            clinical_data: Parsed clinical data with diagnoses
            member_id: Member/patient ID for HD lookup
            policy_start_date: Policy start date (ISO format)
            
        Returns:
            Dict with HD validation results and action required
        """
        
        logger.info(f"=== HD Validation for Member {member_id} ===")
        
        result = {
            "hd_validation_required": False,
            "hd_conditions_found": [],
            "hd_status": HealthDeclarationStatus.NOT_REQUIRED,
            "requires_hitl": False,
            "can_proceed_to_adjudication": True,
            "hd_details": {},
            "action": "normal_adjudication",
            "reason": "",
            "flagged_conditions": []
        }
        
        # Step 1: Check if any diagnosis requires HD
        hd_conditions = self._check_hd_required_diagnoses(clinical_data.diagnoses)
        
        if not hd_conditions:
            logger.info("  ✓ No HD-required conditions found")
            return result
        
        # Found HD-required conditions
        result["hd_validation_required"] = True
        result["hd_conditions_found"] = hd_conditions
        
        logger.info(f"  ⚠ Found {len(hd_conditions)} HD-required condition(s)")
        for condition in hd_conditions:
            logger.info(f"    - {condition['icd10']}: {condition['name']}")
        
        # Step 2: Get member's HD records
        member_hd_records = self._get_member_hd_records(member_id)
        
        # Step 3: Parse policy start date
        policy_date = self._parse_date(policy_start_date)
        current_date = datetime.utcnow().date()
        
        # Step 4: Validate each HD-required condition
        validation_details = []
        overall_can_proceed = True
        overall_requires_hitl = False
        
        for condition in hd_conditions:
            validation = self._validate_single_condition(
                condition=condition,
                member_hd_records=member_hd_records,
                policy_date=policy_date,
                current_date=current_date
            )
            
            validation_details.append(validation)
            
            # Determine overall action
            if validation["requires_hitl"]:
                overall_requires_hitl = True
                overall_can_proceed = False
            elif not validation["can_proceed"]:
                overall_can_proceed = False
        
        result["hd_details"] = validation_details
        result["requires_hitl"] = overall_requires_hitl
        result["can_proceed_to_adjudication"] = overall_can_proceed
        
        # Determine final action
        if overall_requires_hitl:
            result["action"] = "hitl_review_required"
            result["hd_status"] = HealthDeclarationStatus.NOT_DECLARED
            result["reason"] = "Health declaration required but not found in member records"
            result["flagged_conditions"] = [v["condition_name"] for v in validation_details if v["requires_hitl"]]
            
            logger.error(f"  🚨 HITL REQUIRED: {result['reason']}")
            logger.error(f"     Flagged: {', '.join(result['flagged_conditions'])}")
            
        elif not overall_can_proceed:
            result["action"] = "deny_pre_existing"
            result["hd_status"] = HealthDeclarationStatus.PRE_EXISTING
            result["reason"] = "Pre-existing condition within waiting period"
            result["flagged_conditions"] = [v["condition_name"] for v in validation_details if not v["can_proceed"]]
            
            logger.warning(f"  ⚠ DENIAL: {result['reason']}")
            
        else:
            result["action"] = "proceed_to_adjudication"
            result["hd_status"] = HealthDeclarationStatus.DECLARED
            result["reason"] = "All HD conditions properly declared"
            
            logger.info(f"  ✓ HD Validated: Can proceed to adjudication")
        
        return result
    
    def _check_hd_required_diagnoses(self, diagnoses: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Check if any diagnosis requires health declaration"""
        hd_conditions = []
        
        for diagnosis in diagnoses:
            icd10_code = diagnosis.get("code", "")
            
            # Check exact match
            if icd10_code in self.hd_required_conditions:
                condition_info = self.hd_required_conditions[icd10_code].copy()
                condition_info["icd10"] = icd10_code
                condition_info["diagnosis_display"] = diagnosis.get("display", "")
                hd_conditions.append(condition_info)
                continue
            
            # Check prefix match (e.g., all C codes for cancer)
            icd10_prefix = icd10_code[:3] if len(icd10_code) >= 3 else icd10_code
            if icd10_prefix in self.hd_required_conditions:
                condition_info = self.hd_required_conditions[icd10_prefix].copy()
                condition_info["icd10"] = icd10_code
                condition_info["diagnosis_display"] = diagnosis.get("display", "")
                hd_conditions.append(condition_info)
                continue
            
            # Check single character prefix for categories like "C" (cancer)
            if len(icd10_code) > 0 and icd10_code[0] in self.hd_required_conditions:
                condition_info = self.hd_required_conditions[icd10_code[0]].copy()
                condition_info["icd10"] = icd10_code
                condition_info["diagnosis_display"] = diagnosis.get("display", "")
                hd_conditions.append(condition_info)
        
        return hd_conditions
    
    def _get_member_hd_records(self, member_id: str) -> List[Dict[str, Any]]:
        """
        Get member's health declaration records from database
        
        In production, this should query actual database
        """
        return self.member_hd_database.get(member_id, [])
    
    def _validate_single_condition(
        self,
        condition: Dict[str, Any],
        member_hd_records: List[Dict[str, Any]],
        policy_date: date,
        current_date: date
    ) -> Dict[str, Any]:
        """Validate a single HD-required condition"""
        
        icd10_code = condition["icd10"]
        condition_name = condition["name"]
        waiting_period_days = condition.get("waiting_period_days", 180)
        
        validation = {
            "condition_name": condition_name,
            "icd10_code": icd10_code,
            "declared": False,
            "declaration_date": None,
            "diagnosis_date": None,
            "is_pre_existing": False,
            "within_waiting_period": False,
            "can_proceed": False,
            "requires_hitl": False,
            "reason": ""
        }
        
        # Search for this condition in member's HD records
        declared_condition = None
        for record in member_hd_records:
            if record["icd10_code"] == icd10_code or icd10_code.startswith(record["icd10_code"]):
                declared_condition = record
                break
        
        # Case 1: Condition NOT declared in HD
        if not declared_condition:
            validation["requires_hitl"] = True
            validation["can_proceed"] = False
            validation["reason"] = f"{condition_name} requires health declaration but was not declared by member"
            return validation
        
        # Case 2: Condition WAS declared
        validation["declared"] = True
        validation["declaration_date"] = declared_condition.get("declaration_date")
        validation["diagnosis_date"] = declared_condition.get("diagnosis_date")
        
        diagnosis_date = self._parse_date(declared_condition.get("diagnosis_date"))
        
        if diagnosis_date:
            # Check if pre-existing (diagnosed before policy start)
            if diagnosis_date < policy_date:
                validation["is_pre_existing"] = True
                
                # Check waiting period
                days_since_policy = (current_date - policy_date).days
                
                if days_since_policy < waiting_period_days:
                    validation["within_waiting_period"] = True
                    validation["can_proceed"] = False
                    validation["reason"] = f"Pre-existing condition within {waiting_period_days}-day waiting period"
                else:
                    validation["can_proceed"] = True
                    validation["reason"] = f"Pre-existing condition declared, waiting period satisfied"
            else:
                # Newly discovered after policy start
                validation["can_proceed"] = True
                validation["reason"] = f"Condition declared and discovered after policy start"
        else:
            # No diagnosis date, assume declared and allow
            validation["can_proceed"] = True
            validation["reason"] = f"Condition declared in health declaration"
        
        return validation
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str:
            return None
        
        try:
            # Try ISO format first
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            else:
                return datetime.fromisoformat(date_str).date()
        except:
            try:
                # Try YYYY-MM-DD format
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except:
                return None
    
    def add_member_hd_record(
        self,
        member_id: str,
        icd10_code: str,
        condition_name: str,
        diagnosis_date: str,
        declaration_date: str,
        declared_by: str = "member"
    ) -> bool:
        """
        Add a health declaration record for a member
        
        This is a mock implementation. In production, this should insert into database.
        """
        if member_id not in self.member_hd_database:
            self.member_hd_database[member_id] = []
        
        record = {
            "icd10_code": icd10_code,
            "condition_name": condition_name,
            "diagnosis_date": diagnosis_date,
            "declaration_date": declaration_date,
            "declared_by": declared_by,
            "added_at": datetime.utcnow().isoformat()
        }
        
        self.member_hd_database[member_id].append(record)
        
        logger.info(f"✓ Added HD record for member {member_id}: {condition_name} ({icd10_code})")
        return True
    
    def get_member_hd_summary(self, member_id: str) -> Dict[str, Any]:
        """Get summary of member's health declarations"""
        records = self._get_member_hd_records(member_id)
        
        return {
            "member_id": member_id,
            "total_declared_conditions": len(records),
            "declared_conditions": [
                {
                    "condition": r["condition_name"],
                    "icd10": r["icd10_code"],
                    "diagnosis_date": r["diagnosis_date"]
                }
                for r in records
            ]
        }
    
    def is_condition_hd_required(self, icd10_code: str) -> bool:
        """Check if a specific ICD10 code requires health declaration"""
        # Check exact match
        if icd10_code in self.hd_required_conditions:
            return True
        
        # Check prefix
        prefix = icd10_code[:3] if len(icd10_code) >= 3 else icd10_code
        if prefix in self.hd_required_conditions:
            return True
        
        # Check category
        if len(icd10_code) > 0 and icd10_code[0] in self.hd_required_conditions:
            return True
        
        return False


# Global instance
health_declaration_validator = HealthDeclarationValidator()


# Demo/Test data setup
def setup_demo_data():
    """Setup demo health declaration records for testing"""
    
    # Member 1: Has diabetes declared before policy
    health_declaration_validator.add_member_hd_record(
        member_id="PAT001",
        icd10_code="E11",
        condition_name="Type 2 Diabetes Mellitus",
        diagnosis_date="2023-01-15",
        declaration_date="2023-06-01"
    )
    
    # Member 2: Has heart disease declared  
    health_declaration_validator.add_member_hd_record(
        member_id="PAT002",
        icd10_code="I25",
        condition_name="Chronic Ischemic Heart Disease",
        diagnosis_date="2022-05-10",
        declaration_date="2023-01-01"
    )
    
    # Member 3: Has hypertension
    health_declaration_validator.add_member_hd_record(
        member_id="PAT002",
        icd10_code="I10",
        condition_name="Essential Hypertension",
        diagnosis_date="2023-03-20",
        declaration_date="2023-06-01"
    )
    
    logger.info("✓ Demo HD data loaded for 2 members")


# Initialize demo data
setup_demo_data()
