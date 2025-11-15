"""
Test Endpoints for FHIR Validation & Processing
Used by FHIR Testing page
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
from loguru import logger
import json

from app.services.fhir_parser import fhir_parser
from app.services.decision_orchestrator import decision_orchestrator

router = APIRouter(prefix="/test", tags=["Testing"])

@router.get("/sample-fhir", summary="Get Sample FHIR Bundle")
async def get_sample_fhir():
    """Get a sample FHIR bundle for testing"""
    try:
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "patient-1",
                        "name": [{"given": ["John"], "family": "Doe"}],
                        "birthDate": "1980-01-01"
                    }
                },
                {
                    "resource": {
                        "resourceType": "Claim",
                        "id": "claim-1",
                        "status": "active",
                        "type": {"coding": [{"code": "institutional"}]},
                        "use": "claim",
                        "patient": {"reference": "Patient/patient-1"},
                        "billablePeriod": {
                            "start": "2024-01-01",
                            "end": "2024-12-31"
                        },
                        "item": [
                            {
                                "sequence": 1,
                                "productOrService": {"coding": [{"code": "123456"}]},
                                "quantity": {"value": 1},
                                "unitPrice": {"value": 1000, "currency": "SAR"}
                            }
                        ]
                    }
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error getting sample FHIR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-fhir", summary="Validate FHIR Bundle")
async def validate_fhir(bundle_data: Dict[str, Any]):
    """Validate FHIR bundle structure"""
    try:
        if not bundle_data:
            raise ValueError("Bundle data is empty")
        
        if not isinstance(bundle_data, dict):
            raise ValueError("Bundle must be a JSON object")
        
        if "resourceType" not in bundle_data:
            raise ValueError("Missing resourceType in bundle")
        
        # Parse the bundle to validate structure
        clinical_data = fhir_parser.parse_bundle(bundle_data)
        
        logger.info(f"✓ FHIR bundle validated for patient {clinical_data.patient_id}")
        
        return {
            "valid": True,
            "message": "FHIR bundle is valid",
            "patient_id": clinical_data.patient_id,
            "parsed_data": {
                "patient_id": clinical_data.patient_id,
                "diagnoses": [str(d) for d in clinical_data.diagnoses],
                "services": len(clinical_data.services) if hasattr(clinical_data, 'services') else 0,
                "total_amount": getattr(clinical_data, 'total_amount', 0)
            },
            "timestamp": datetime.utcnow()
        }
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error validating FHIR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-claim", summary="Process FHIR Claim")
async def process_claim(request: Dict[str, Any]):
    """Process a FHIR claim through adjudication layers"""
    try:
        bundle_data = request.get("bundle_data")
        policy_start_date = request.get("policy_start_date")
        
        if not bundle_data:
            raise ValueError("bundle_data is required")
        
        # Parse FHIR bundle
        logger.info("Step 1: Parsing FHIR bundle...")
        clinical_data = fhir_parser.parse_bundle(bundle_data)
        logger.info(f"✓ Parsed clinical data for patient {clinical_data.patient_id}")
        
        # Run adjudication
        logger.info("Step 2: Running adjudication layers...")
        orchestration_result = decision_orchestrator.adjudicate_request(
            clinical_data,
            policy_start_date=policy_start_date
        )
        
        service_decisions = orchestration_result["service_decisions"]
        
        # Build response
        return {
            "success": True,
            "claim_id": clinical_data.patient_id,
            "patient_id": clinical_data.patient_id,
            "status": "processed",
            "overall_decision": orchestration_result.get("overall_decision", "PENDING"),
            "deciding_layer": orchestration_result.get("deciding_layer", "Unknown"),
            "confidence": round(orchestration_result.get("final_confidence", 0.5), 2),
            "service_decisions": [
                {
                    "service_code": d.service_code,
                    "description": d.service_description,
                    "decision": d.decision.value if hasattr(d.decision, 'value') else str(d.decision),
                    "approved_amount": d.approved_amount or 0,
                    "requested_amount": d.requested_amount or 0
                }
                for d in service_decisions
            ],
            "decision_path": orchestration_result.get("decision_path", []),
            "processing_time_ms": orchestration_result.get("processing_time_ms", 0),
            "timestamp": datetime.utcnow()
        }
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/layer-info", summary="Get Adjudication Layer Information")
async def get_layer_info():
    """Get information about adjudication layers"""
    return {
        "layers": [
            {
                "name": "Health Declaration Pre-Screening",
                "layer": 0,
                "confidence_range": "95-99%",
                "description": "Validates health declaration requirements and status"
            },
            {
                "name": "Rules Engine",
                "layer": 1,
                "confidence_range": "90-99%",
                "description": "Auto-approve/deny based on hard rules"
            },
            {
                "name": "RAG Policy System",
                "layer": 2,
                "confidence_range": "75-90%",
                "description": "Retrieves and applies policy guidelines"
            },
            {
                "name": "Medical LLM",
                "layer": 3,
                "confidence_range": "50-75%",
                "description": "Clinical reasoning for complex cases"
            }
        ],
        "timestamp": datetime.utcnow()
    }

@router.post("/diagnose", summary="Get Diagnosis Information")
async def get_diagnosis_info(data: Dict[str, Any]):
    """Get diagnosis information from clinical data"""
    try:
        diagnosis_code = data.get("code")
        
        if not diagnosis_code:
            raise ValueError("Diagnosis code is required")
        
        return {
            "code": diagnosis_code,
            "description": f"Diagnosis: {diagnosis_code}",
            "hd_required": True,
            "risk_level": "medium",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error getting diagnosis info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
