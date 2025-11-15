"""
NPHIES FHIR Parser Service
Extracts and validates clinical data from FHIR Bundle
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.models.fhir_models import Bundle, ParsedClinicalData, Claim
from app.config.settings import settings
import json
from loguru import logger

class FHIRParserService:
    """Parse NPHIES FHIR bundles into structured clinical data"""
    
    def __init__(self):
        self.required_resources = ["Claim", "Patient", "Coverage"]
    
    def parse_bundle(self, bundle_data: Dict[str, Any]) -> ParsedClinicalData:
        """
        Parse FHIR Bundle and extract clinical information
        
        Args:
            bundle_data: FHIR Bundle as dictionary
            
        Returns:
            ParsedClinicalData: Structured clinical data
        """
        try:
            # Validate bundle structure
            self._validate_bundle(bundle_data)
            
            # Extract resources from bundle
            resources = self._extract_resources(bundle_data)
            
            # Parse Claim
            claim = resources.get("Claim", [{}])[0]
            patient = resources.get("Patient", [{}])[0]
            coverage = resources.get("Coverage", [{}])[0]
            
            # Build parsed data
            parsed_data = ParsedClinicalData(
                request_id=self._get_claim_id(claim),
                patient_id=self._get_patient_id(patient),
                patient_age=self._calculate_age(patient.get("birthDate")),
                patient_gender=patient.get("gender"),
                coverage_id=self._get_coverage_id(coverage),
                insurer_id=self._get_insurer_id(claim),
                provider_id=self._get_provider_id(claim),
                
                diagnoses=self._parse_diagnoses(claim),
                procedures=self._parse_procedures(claim),
                services=self._parse_items(claim),
                
                service_date=claim.get("created"),
                total_cost=self._calculate_total_cost(claim),
                facility_type=self._get_facility_type(claim),
                
                clinical_notes=self._extract_clinical_notes(claim),
                attachments=self._extract_attachments(claim),
                
                created_date=claim.get("created", datetime.utcnow().isoformat()),
                priority=self._get_priority(claim)
            )
            
            logger.info(f"Successfully parsed FHIR bundle for request {parsed_data.request_id}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing FHIR bundle: {str(e)}")
            raise ValueError(f"FHIR parsing error: {str(e)}")
    
    def _validate_bundle(self, bundle_data: Dict[str, Any]):
        """Validate FHIR Bundle structure"""
        if bundle_data.get("resourceType") != "Bundle":
            raise ValueError("Invalid FHIR Bundle: resourceType must be 'Bundle'")
        
        if "entry" not in bundle_data or not bundle_data["entry"]:
            raise ValueError("Invalid FHIR Bundle: no entries found")
        
        # Check for required resources
        resource_types = [
            entry.get("resource", {}).get("resourceType") 
            for entry in bundle_data.get("entry", [])
        ]
        
        for required in self.required_resources:
            if required not in resource_types:
                raise ValueError(f"Missing required resource: {required}")
    
    def _extract_resources(self, bundle_data: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Extract and group resources by type"""
        resources = {}
        
        for entry in bundle_data.get("entry", []):
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType")
            
            if resource_type:
                if resource_type not in resources:
                    resources[resource_type] = []
                resources[resource_type].append(resource)
        
        return resources
    
    def _get_claim_id(self, claim: Dict[str, Any]) -> str:
        """Extract claim ID"""
        claim_id = claim.get("id")
        if not claim_id and claim.get("identifier"):
            claim_id = claim["identifier"][0].get("value")
        return claim_id or f"claim-{datetime.utcnow().timestamp()}"
    
    def _get_patient_id(self, patient: Dict[str, Any]) -> str:
        """Extract patient ID"""
        patient_id = patient.get("id")
        if not patient_id and patient.get("identifier"):
            patient_id = patient["identifier"][0].get("value")
        return patient_id or "unknown"
    
    def _get_coverage_id(self, coverage: Dict[str, Any]) -> str:
        """Extract coverage ID"""
        coverage_id = coverage.get("id")
        if not coverage_id and coverage.get("identifier"):
            coverage_id = coverage["identifier"][0].get("value")
        return coverage_id or "unknown"
    
    def _get_insurer_id(self, claim: Dict[str, Any]) -> Optional[str]:
        """Extract insurer ID"""
        insurer = claim.get("insurer")
        if insurer:
            return insurer.get("reference", "").split("/")[-1]
        return None
    
    def _get_provider_id(self, claim: Dict[str, Any]) -> str:
        """Extract provider ID"""
        provider = claim.get("provider", {})
        return provider.get("reference", "").split("/")[-1] or "unknown"
    
    def _calculate_age(self, birth_date: Optional[str]) -> Optional[int]:
        """Calculate age from birth date"""
        if not birth_date:
            return None
        
        try:
            birth = datetime.fromisoformat(birth_date.replace("Z", "+00:00"))
            today = datetime.utcnow()
            age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            return age
        except:
            return None
    
    def _parse_diagnoses(self, claim: Dict[str, Any]) -> List[Dict[str, str]]:
        """Parse diagnosis codes"""
        diagnoses = []
        
        for diag in claim.get("diagnosis", []):
            diagnosis_code = diag.get("diagnosisCodeableConcept", {})
            if diagnosis_code and diagnosis_code.get("coding"):
                coding = diagnosis_code["coding"][0]
                diagnoses.append({
                    "code": coding.get("code", ""),
                    "display": coding.get("display", ""),
                    "system": coding.get("system", ""),
                    "type": self._get_diagnosis_type(diag)
                })
        
        return diagnoses
    
    def _get_diagnosis_type(self, diag: Dict[str, Any]) -> str:
        """Get diagnosis type (primary, secondary, etc.)"""
        types = diag.get("type", [])
        if types and types[0].get("coding"):
            return types[0]["coding"][0].get("code", "unknown")
        return "unknown"
    
    def _parse_procedures(self, claim: Dict[str, Any]) -> List[Dict[str, str]]:
        """Parse procedure codes"""
        procedures = []
        
        for proc in claim.get("procedure", []):
            procedure_code = proc.get("procedureCodeableConcept", {})
            if procedure_code and procedure_code.get("coding"):
                coding = procedure_code["coding"][0]
                procedures.append({
                    "code": coding.get("code", ""),
                    "display": coding.get("display", ""),
                    "system": coding.get("system", ""),
                    "date": proc.get("date", "")
                })
        
        return procedures
    
    def _parse_items(self, claim: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse service items"""
        services = []
        
        for item in claim.get("item", []):
            product_or_service = item.get("productOrService", {})
            if product_or_service and product_or_service.get("coding"):
                coding = product_or_service["coding"][0]
                
                # Extract cost information
                unit_price = item.get("unitPrice", {})
                quantity = item.get("quantity", {})
                net = item.get("net", {})
                
                services.append({
                    "sequence": item.get("sequence"),
                    "code": coding.get("code", ""),
                    "description": coding.get("display", ""),
                    "system": coding.get("system", ""),
                    "quantity": quantity.get("value", 1),
                    "unit_price": unit_price.get("value"),
                    "currency": unit_price.get("currency", "SAR"),
                    "net_amount": net.get("value"),
                    "serviced_date": item.get("servicedDate"),
                    "body_site": self._get_body_site(item)
                })
        
        return services
    
    def _get_body_site(self, item: Dict[str, Any]) -> Optional[str]:
        """Extract body site if available"""
        body_site = item.get("bodySite", {})
        if body_site and body_site.get("coding"):
            return body_site["coding"][0].get("display")
        return None
    
    def _calculate_total_cost(self, claim: Dict[str, Any]) -> Optional[float]:
        """Calculate total cost from items"""
        total = claim.get("total", {})
        if total and "value" in total:
            return float(total["value"])
        
        # Calculate from items
        total_cost = 0.0
        for item in claim.get("item", []):
            net = item.get("net", {})
            if "value" in net:
                total_cost += float(net["value"])
        
        return total_cost if total_cost > 0 else None
    
    def _get_facility_type(self, claim: Dict[str, Any]) -> Optional[str]:
        """Extract facility type"""
        facility = claim.get("facility", {})
        if facility:
            return facility.get("type", "unknown")
        return None
    
    def _extract_clinical_notes(self, claim: Dict[str, Any]) -> List[str]:
        """Extract clinical notes from supporting info"""
        notes = []
        
        for info in claim.get("supportingInfo", []):
            if info.get("category", {}).get("coding", [{}])[0].get("code") == "clinical-notes":
                if "valueString" in info:
                    notes.append(info["valueString"])
        
        return notes
    
    def _extract_attachments(self, claim: Dict[str, Any]) -> List[str]:
        """Extract attachment references"""
        attachments = []
        
        for info in claim.get("supportingInfo", []):
            if "valueAttachment" in info:
                attachment = info["valueAttachment"]
                if "url" in attachment:
                    attachments.append(attachment["url"])
        
        return attachments
    
    def _get_priority(self, claim: Dict[str, Any]) -> Optional[str]:
        """Extract priority level"""
        priority = claim.get("priority", {})
        if priority and priority.get("coding"):
            return priority["coding"][0].get("code")
        return None

# Global instance
fhir_parser = FHIRParserService()
