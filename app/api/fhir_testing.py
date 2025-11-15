"""
FHIR Testing & Processing Endpoints
Comprehensive claim validation and AI processing through all system layers
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from loguru import logger

router = APIRouter(prefix="/test", tags=["FHIR Testing"])

# Models
class FHIRValidationRequest(BaseModel):
    fhir_data: Dict[str, Any]

class AIProcessingRequest(BaseModel):
    fhir_data: Dict[str, Any]
    process_fraud_detection: bool = True
    process_medical_rules: bool = True
    process_risk_assessment: bool = True

class ProcessingResult(BaseModel):
    status: str
    validation: Dict[str, Any]
    medical_rules_result: Optional[Dict[str, Any]] = None
    fraud_detection_result: Optional[Dict[str, Any]] = None
    risk_assessment_result: Optional[Dict[str, Any]] = None
    final_decision: Dict[str, Any]
    processing_time_ms: float
    timestamp: str

# FHIR Validators
class FHIRValidator:
    @staticmethod
    def validate_claim(fhir_data: Dict) -> Dict[str, Any]:
        """Validate FHIR Claim resource"""
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ['resourceType', 'id', 'status', 'type', 'patient', 'created', 'provider']
        
        for field in required_fields:
            if field not in fhir_data:
                errors.append(f"Missing required field: {field}")
        
        if fhir_data.get('resourceType') != 'Claim':
            errors.append("Invalid resource type. Expected 'Claim'")
        
        # Validate nested structures
        if 'item' in fhir_data and isinstance(fhir_data['item'], list):
            for idx, item in enumerate(fhir_data['item']):
                if 'productOrService' not in item:
                    warnings.append(f"Item {idx} missing productOrService")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'resource_type': fhir_data.get('resourceType'),
            'resource_id': fhir_data.get('id'),
            'total_items': len(fhir_data.get('item', []))
        }
    
    @staticmethod
    def extract_claim_summary(fhir_data: Dict) -> Dict[str, Any]:
        """Extract key information from FHIR Claim"""
        try:
            patient_ref = fhir_data.get('patient', {})
            provider_ref = fhir_data.get('provider', {})
            enterer_ref = fhir_data.get('enterer', {})
            
            items = fhir_data.get('item', [])
            total_amount = 0
            for item in items:
                if 'unitPrice' in item:
                    price = item['unitPrice']
                    if isinstance(price, dict):
                        total_amount += float(price.get('value', 0))
            
            return {
                'claim_id': fhir_data.get('id'),
                'status': fhir_data.get('status'),
                'type': fhir_data.get('type', {}).get('coding', [{}])[0].get('code', 'UNKNOWN'),
                'patient': patient_ref.get('reference', 'N/A'),
                'provider': provider_ref.get('reference', 'N/A'),
                'created': fhir_data.get('created'),
                'total_amount': total_amount,
                'currency': fhir_data.get('item', [{}])[0].get('unitPrice', {}).get('currency', 'SAR') if fhir_data.get('item') else 'SAR',
                'item_count': len(items),
                'diagnosis_count': len(fhir_data.get('diagnosis', [])),
                'procedure_count': len(fhir_data.get('procedure', []))
            }
        except Exception as e:
            logger.error(f"Error extracting claim summary: {e}")
            return {}

# AI Processing Engine
class ClaimsProcessor:
    @staticmethod
    def process_medical_rules(fhir_data: Dict, validation: Dict) -> Dict[str, Any]:
        """Process claim through medical rules engine"""
        if not validation['valid']:
            return {
                'status': 'FAILED',
                'reason': 'Invalid FHIR data',
                'rules_applied': 0
            }
        
        results = {
            'status': 'PROCESSED',
            'rules_applied': 0,
            'decisions': [],
            'coverage_analysis': {
                'total_items': validation['total_items'],
                'covered': 0,
                'denied': 0,
                'requires_review': 0
            }
        }
        
        # Simulate rule processing
        items = fhir_data.get('item', [])
        for idx, item in enumerate(items):
            decision = {
                'item_index': idx,
                'product_code': item.get('productOrService', {}).get('coding', [{}])[0].get('code', 'UNKNOWN'),
                'decision': 'APPROVED',  # Simplified logic
                'reason': 'Coverage approved per medical policy'
            }
            results['decisions'].append(decision)
            results['coverage_analysis']['covered'] += 1
            results['rules_applied'] += 1
        
        return results
    
    @staticmethod
    def process_fraud_detection(fhir_data: Dict, validation: Dict) -> Dict[str, Any]:
        """Fraud detection analysis"""
        results = {
            'status': 'ANALYZED',
            'fraud_risk_score': 0.0,
            'risk_level': 'LOW',
            'red_flags': [],
            'provider_analysis': {
                'provider_id': fhir_data.get('provider', {}).get('reference', 'UNKNOWN'),
                'submission_pattern': 'NORMAL',
                'frequency_score': 0.0
            }
        }
        
        # Analyze for fraud indicators
        items = fhir_data.get('item', [])
        total_amount = sum([float(item.get('unitPrice', {}).get('value', 0)) for item in items])
        
        # Check for anomalies
        if total_amount > 100000:
            results['red_flags'].append('Unusually high claim amount')
            results['fraud_risk_score'] += 0.2
        
        if len(items) > 50:
            results['red_flags'].append('Excessive number of items')
            results['fraud_risk_score'] += 0.15
        
        # Determine risk level
        if results['fraud_risk_score'] >= 0.7:
            results['risk_level'] = 'HIGH'
        elif results['fraud_risk_score'] >= 0.4:
            results['risk_level'] = 'MEDIUM'
        
        return results
    
    @staticmethod
    def process_risk_assessment(fhir_data: Dict, validation: Dict) -> Dict[str, Any]:
        """Financial risk assessment"""
        results = {
            'status': 'CALCULATED',
            'overall_risk_score': 0.0,
            'financial_risk': {
                'amount_at_risk': 0.0,
                'coverage_probability': 100.0
            },
            'member_risk': {
                'diagnosis_severity': 'MODERATE',
                'healthcare_cost_prediction': 0.0
            },
            'recommendations': []
        }
        
        items = fhir_data.get('item', [])
        total_amount = sum([float(item.get('unitPrice', {}).get('value', 0)) for item in items])
        
        results['financial_risk']['amount_at_risk'] = total_amount * 0.1  # 10% risk buffer
        results['overall_risk_score'] = min(0.3, total_amount / 1000000)  # Normalize to 0-1
        
        if results['overall_risk_score'] > 0.2:
            results['recommendations'].append('Consider pre-authorization for high-risk items')
        
        return results

# API Endpoints
@router.post("/validate-fhir")
async def validate_fhir(request: FHIRValidationRequest):
    """Validate FHIR Claim resource"""
    try:
        validator = FHIRValidator()
        validation = validator.validate_claim(request.fhir_data)
        summary = validator.extract_claim_summary(request.fhir_data)
        
        return {
            'status': 'success',
            'validation': validation,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"FHIR validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/process-claim")
async def process_claim(request: AIProcessingRequest):
    """Process FHIR Claim through all system layers"""
    import time
    start_time = time.time()
    
    try:
        validator = FHIRValidator()
        processor = ClaimsProcessor()
        
        # Step 1: Validate
        validation = validator.validate_claim(request.fhir_data)
        
        # Step 2: Process through layers
        medical_rules_result = None
        fraud_detection_result = None
        risk_assessment_result = None
        
        if request.process_medical_rules:
            medical_rules_result = processor.process_medical_rules(request.fhir_data, validation)
        
        if request.process_fraud_detection:
            fraud_detection_result = processor.process_fraud_detection(request.fhir_data, validation)
        
        if request.process_risk_assessment:
            risk_assessment_result = processor.process_risk_assessment(request.fhir_data, validation)
        
        # Step 3: Generate final decision
        final_decision = {
            'recommendation': 'APPROVED',
            'reasoning': []
        }
        
        if not validation['valid']:
            final_decision['recommendation'] = 'REJECTED'
            final_decision['reasoning'].append('Validation failed: ' + ', '.join(validation['errors']))
        elif fraud_detection_result and fraud_detection_result['risk_level'] == 'HIGH':
            final_decision['recommendation'] = 'REQUIRES_REVIEW'
            final_decision['reasoning'].append('High fraud risk detected')
        elif medical_rules_result and medical_rules_result['status'] == 'PROCESSED':
            final_decision['reasoning'].append('All items covered per medical policy')
        
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return {
            'status': 'success',
            'validation': validation,
            'medical_rules_result': medical_rules_result,
            'fraud_detection_result': fraud_detection_result,
            'risk_assessment_result': risk_assessment_result,
            'final_decision': final_decision,
            'processing_time_ms': round(processing_time, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Claim processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sample-fhir")
async def get_sample_fhir():
    """Get sample FHIR Claim for testing"""
    return {
        "resourceType": "Claim",
        "id": "CLAIM-2025-001",
        "status": "active",
        "type": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/claim-type",
                    "code": "institutional",
                    "display": "Institutional"
                }
            ]
        },
        "patient": {
            "reference": "Patient/12345"
        },
        "billablePeriod": {
            "start": "2025-01-01",
            "end": "2025-01-31"
        },
        "created": "2025-01-15T10:00:00Z",
        "enterer": {
            "reference": "Practitioner/98765"
        },
        "insurer": {
            "reference": "Organization/insurance-co"
        },
        "provider": {
            "reference": "Organization/hospital-123"
        },
        "priority": {
            "coding": [
                {
                    "code": "normal"
                }
            ]
        },
        "diagnosis": [
            {
                "sequence": 1,
                "diagnosisCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10-cm",
                            "code": "E11.9",
                            "display": "Type 2 diabetes mellitus without complications"
                        }
                    ]
                }
            }
        ],
        "procedure": [
            {
                "sequence": 1,
                "procedureCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://www.ama-assn.org/go/cpt",
                            "code": "99213",
                            "display": "Office visit"
                        }
                    ]
                }
            }
        ],
        "item": [
            {
                "sequence": 1,
                "careTeamSequence": [1],
                "diagnosisSequence": [1],
                "procedureSequence": [1],
                "productOrService": {
                    "coding": [
                        {
                            "system": "http://www.ama-assn.org/go/cpt",
                            "code": "99213",
                            "display": "Office visit"
                        }
                    ]
                },
                "servicedDate": "2025-01-10",
                "quantity": {
                    "value": 1
                },
                "unitPrice": {
                    "value": 500.00,
                    "currency": "SAR"
                },
                "net": {
                    "value": 500.00,
                    "currency": "SAR"
                }
            },
            {
                "sequence": 2,
                "careTeamSequence": [1],
                "diagnosisSequence": [1],
                "productOrService": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "2345-7",
                            "display": "Glucose [Mass/volume] in Serum or Plasma"
                        }
                    ]
                },
                "servicedDate": "2025-01-10",
                "quantity": {
                    "value": 1
                },
                "unitPrice": {
                    "value": 150.00,
                    "currency": "SAR"
                },
                "net": {
                    "value": 150.00,
                    "currency": "SAR"
                }
            }
        ],
        "total": {
            "value": 650.00,
            "currency": "SAR"
        }
    }
