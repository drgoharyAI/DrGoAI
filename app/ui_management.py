"""
UI Management Router - Complete Database-Backed Implementation
All management endpoints for DrGoAi dashboard with persistent storage
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
from pydantic import BaseModel, Field

from app.db.database import get_db, init_db
from app.db import crud
from app.config.settings import settings
from app.core.phi_redactor import phi_redactor

router = APIRouter()

# ============================================================================
# PYDANTIC MODELS FOR REQUEST/RESPONSE
# ============================================================================

class MedicalRuleCreate(BaseModel):
    rule_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    enabled: bool = True
    action: str = Field(..., pattern="^(APPROVE|DENY|CONDITIONAL_APPROVAL|PARTIAL_APPROVAL|REVIEW)$")
    priority: int = Field(1, ge=1, le=10)
    conditions: List[str] = []

class MedicalRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    action: Optional[str] = None
    priority: Optional[int] = None
    conditions: Optional[List[str]] = None

class HDConditionCreate(BaseModel):
    condition_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    icd_code: Optional[str] = None
    waiting_period_months: int = Field(0, ge=0)
    coverage_percentage: int = Field(100, ge=0, le=100)
    severity: Optional[str] = None

class HDConditionUpdate(BaseModel):
    name: Optional[str] = None
    icd_code: Optional[str] = None
    waiting_period_months: Optional[int] = None
    coverage_percentage: Optional[int] = None
    severity: Optional[str] = None

class FraudRuleCreate(BaseModel):
    rule_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    enabled: bool = True
    threshold: float = Field(0.85, ge=0.0, le=1.0)
    pattern_type: Optional[str] = None

class FraudRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    threshold: Optional[float] = None
    pattern_type: Optional[str] = None

class RiskParameterCreate(BaseModel):
    param_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    weight: float = Field(0.1, ge=0.0, le=1.0)
    description: Optional[str] = None
    enabled: bool = True

class RiskParameterUpdate(BaseModel):
    name: Optional[str] = None
    weight: Optional[float] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None

# ============================================================================
# SYSTEM STATUS & HEALTH
# ============================================================================

@router.get("/system-status")
async def get_system_status(db: Session = Depends(get_db)):
    """Get comprehensive system status"""
    try:
        stats = crud.get_system_stats(db)
        
        # Check RAG system
        rag_status = "operational"
        try:
            from app.services.rag_system import rag_system
            if not rag_system.initialized:
                rag_status = "not_initialized"
        except:
            rag_status = "error"
        
        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "database": stats,
            "rag_system": rag_status,
            "version": settings.VERSION
        }
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# ============================================================================
# MEDICAL RULES ENDPOINTS
# ============================================================================

@router.get("/medical-rules")
async def list_medical_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all medical rules"""
    try:
        rules = crud.get_medical_rules(db, skip=skip, limit=limit)
        return [
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "enabled": rule.enabled,
                "action": rule.action,
                "priority": rule.priority,
                "conditions": rule.conditions,
                "created_at": rule.created_at.isoformat() if rule.created_at else None
            }
            for rule in rules
        ]
    except Exception as e:
        logger.error(f"Error listing medical rules: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/medical-rules/{rule_id}")
async def get_medical_rule(rule_id: str, db: Session = Depends(get_db)):
    """Get a specific medical rule"""
    try:
        rule = crud.get_medical_rule(db, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        return {
            "rule_id": rule.rule_id,
            "name": rule.name,
            "description": rule.description,
            "enabled": rule.enabled,
            "action": rule.action,
            "priority": rule.priority,
            "conditions": rule.conditions,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting medical rule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/medical-rules")
async def create_medical_rule(rule: MedicalRuleCreate, db: Session = Depends(get_db)):
    """Create a new medical rule"""
    try:
        # Check if rule_id already exists
        existing = crud.get_medical_rule(db, rule.rule_id)
        if existing:
            raise HTTPException(status_code=400, detail="Rule ID already exists")
        
        rule_data = rule.dict()
        new_rule = crud.create_medical_rule(db, rule_data)
        
        logger.info(f"Created medical rule: {new_rule.rule_id}")
        return {
            "message": "Rule created successfully",
            "rule_id": new_rule.rule_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating medical rule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/medical-rules/{rule_id}")
async def update_medical_rule(
    rule_id: str,
    rule: MedicalRuleUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing medical rule"""
    try:
        rule_data = rule.dict(exclude_unset=True)
        updated_rule = crud.update_medical_rule(db, rule_id, rule_data)
        
        if not updated_rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        logger.info(f"Updated medical rule: {rule_id}")
        return {"message": "Rule updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating medical rule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/medical-rules/{rule_id}")
async def delete_medical_rule(rule_id: str, db: Session = Depends(get_db)):
    """Delete a medical rule"""
    try:
        success = crud.delete_medical_rule(db, rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        logger.info(f"Deleted medical rule: {rule_id}")
        return {"message": "Rule deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting medical rule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/medical-rules/{rule_id}/toggle")
async def toggle_medical_rule(rule_id: str, db: Session = Depends(get_db)):
    """Toggle a medical rule's enabled status"""
    try:
        rule = crud.toggle_medical_rule(db, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        logger.info(f"Toggled medical rule: {rule_id} -> {rule.enabled}")
        return {
            "message": "Rule toggled successfully",
            "enabled": rule.enabled
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling medical rule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# HEALTH DECLARATION CONDITIONS ENDPOINTS
# ============================================================================

@router.get("/hd-conditions")
async def list_hd_conditions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all HD conditions"""
    try:
        conditions = crud.get_hd_conditions(db, skip=skip, limit=limit)
        return [
            {
                "condition_id": c.condition_id,
                "name": c.name,
                "icd_code": c.icd_code,
                "waiting_period_months": c.waiting_period_months,
                "coverage_percentage": c.coverage_percentage,
                "severity": c.severity
            }
            for c in conditions
        ]
    except Exception as e:
        logger.error(f"Error listing HD conditions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/hd-conditions")
async def create_hd_condition(condition: HDConditionCreate, db: Session = Depends(get_db)):
    """Create a new HD condition"""
    try:
        existing = crud.get_hd_condition(db, condition.condition_id)
        if existing:
            raise HTTPException(status_code=400, detail="Condition ID already exists")
        
        new_condition = crud.create_hd_condition(db, condition.dict())
        logger.info(f"Created HD condition: {new_condition.condition_id}")
        return {"message": "Condition created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating HD condition: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/hd-conditions/{condition_id}")
async def update_hd_condition(
    condition_id: str,
    condition: HDConditionUpdate,
    db: Session = Depends(get_db)
):
    """Update an HD condition"""
    try:
        updated = crud.update_hd_condition(db, condition_id, condition.dict(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Condition not found")
        
        logger.info(f"Updated HD condition: {condition_id}")
        return {"message": "Condition updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating HD condition: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/hd-conditions/{condition_id}")
async def delete_hd_condition(condition_id: str, db: Session = Depends(get_db)):
    """Delete an HD condition"""
    try:
        success = crud.delete_hd_condition(db, condition_id)
        if not success:
            raise HTTPException(status_code=404, detail="Condition not found")
        
        logger.info(f"Deleted HD condition: {condition_id}")
        return {"message": "Condition deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting HD condition: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# FRAUD RULES ENDPOINTS
# ============================================================================

@router.get("/fraud-rules")
async def list_fraud_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all fraud detection rules"""
    try:
        rules = crud.get_fraud_rules(db, skip=skip, limit=limit)
        return [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "description": r.description,
                "enabled": r.enabled,
                "threshold": r.threshold,
                "pattern_type": r.pattern_type
            }
            for r in rules
        ]
    except Exception as e:
        logger.error(f"Error listing fraud rules: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fraud-rules")
async def create_fraud_rule(rule: FraudRuleCreate, db: Session = Depends(get_db)):
    """Create a new fraud rule"""
    try:
        existing = crud.get_fraud_rule(db, rule.rule_id)
        if existing:
            raise HTTPException(status_code=400, detail="Fraud rule ID already exists")
        
        new_rule = crud.create_fraud_rule(db, rule.dict())
        logger.info(f"Created fraud rule: {new_rule.rule_id}")
        return {"message": "Fraud rule created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating fraud rule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/fraud-rules/{rule_id}")
async def update_fraud_rule(
    rule_id: str,
    rule: FraudRuleUpdate,
    db: Session = Depends(get_db)
):
    """Update a fraud rule"""
    try:
        updated = crud.update_fraud_rule(db, rule_id, rule.dict(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Fraud rule not found")
        
        logger.info(f"Updated fraud rule: {rule_id}")
        return {"message": "Fraud rule updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating fraud rule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/fraud-rules/{rule_id}")
async def delete_fraud_rule(rule_id: str, db: Session = Depends(get_db)):
    """Delete a fraud rule"""
    try:
        success = crud.delete_fraud_rule(db, rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Fraud rule not found")
        
        logger.info(f"Deleted fraud rule: {rule_id}")
        return {"message": "Fraud rule deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting fraud rule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fraud-rules/{rule_id}/toggle")
async def toggle_fraud_rule(rule_id: str, db: Session = Depends(get_db)):
    """Toggle a fraud rule's enabled status"""
    try:
        rule = crud.toggle_fraud_rule(db, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Fraud rule not found")
        
        logger.info(f"Toggled fraud rule: {rule_id} -> {rule.enabled}")
        return {"message": "Fraud rule toggled successfully", "enabled": rule.enabled}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling fraud rule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RISK PARAMETERS ENDPOINTS
# ============================================================================

@router.get("/risk-parameters")
async def list_risk_parameters(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all risk assessment parameters"""
    try:
        params = crud.get_risk_parameters(db, skip=skip, limit=limit)
        return [
            {
                "param_id": p.param_id,
                "name": p.name,
                "weight": p.weight,
                "description": p.description,
                "enabled": p.enabled
            }
            for p in params
        ]
    except Exception as e:
        logger.error(f"Error listing risk parameters: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/risk-parameters")
async def create_risk_parameter(param: RiskParameterCreate, db: Session = Depends(get_db)):
    """Create a new risk parameter"""
    try:
        existing = crud.get_risk_parameter(db, param.param_id)
        if existing:
            raise HTTPException(status_code=400, detail="Parameter ID already exists")
        
        new_param = crud.create_risk_parameter(db, param.dict())
        logger.info(f"Created risk parameter: {new_param.param_id}")
        return {"message": "Risk parameter created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating risk parameter: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/risk-parameters/{param_id}")
async def update_risk_parameter(
    param_id: str,
    param: RiskParameterUpdate,
    db: Session = Depends(get_db)
):
    """Update a risk parameter"""
    try:
        updated = crud.update_risk_parameter(db, param_id, param.dict(exclude_unset=True))
        if not updated:
            raise HTTPException(status_code=404, detail="Parameter not found")
        
        logger.info(f"Updated risk parameter: {param_id}")
        return {"message": "Parameter updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating risk parameter: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/risk-parameters/{param_id}")
async def delete_risk_parameter(param_id: str, db: Session = Depends(get_db)):
    """Delete a risk parameter"""
    try:
        success = crud.delete_risk_parameter(db, param_id)
        if not success:
            raise HTTPException(status_code=404, detail="Parameter not found")
        
        logger.info(f"Deleted risk parameter: {param_id}")
        return {"message": "Parameter deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting risk parameter: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# LLM MODELS ENDPOINTS
# ============================================================================

@router.get("/llm-models")
async def list_llm_models():
    """List available LLM models"""
    try:
        return [{
            "model_id": "gemini-2.0-flash-exp",
            "name": "Google Gemini 2.0 Flash",
            "provider": "Google",
            "enabled": True,
            "configuration": {
                "max_tokens": settings.GEMINI_MAX_TOKENS,
                "temperature": settings.GEMINI_TEMPERATURE
            }
        }]
    except Exception as e:
        logger.error(f"Error listing LLM models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RAG DATABASE ENDPOINTS
# ============================================================================

@router.get("/rag-databases")
async def list_rag_databases():
    """List RAG databases"""
    try:
        from app.services.rag_system import rag_system
        if rag_system.initialized:
            stats = rag_system.get_database_stats()
            return [{
                "db_id": "NPHIES_RAG_001",
                "name": "NPHIES Medical Standards (KSA)",
                "records": stats.get('total_chunks', 0),
                "documents": stats.get('unique_documents', 0),
                "last_updated": datetime.utcnow().isoformat(),
                "enabled": True
            }]
        else:
            return [{
                "db_id": "NPHIES_RAG_001",
                "name": "NPHIES Medical Standards (KSA)",
                "records": 0,
                "enabled": False,
                "error": rag_system.initialization_error
            }]
    except Exception as e:
        logger.error(f"Error listing RAG databases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# AUDIT LOGS ENDPOINTS
# ============================================================================

@router.get("/audit-logs")
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List audit logs"""
    try:
        logs = crud.get_audit_logs(db, skip=skip, limit=limit)
        return [
            {
                "request_id": log.request_id,
                "action": log.action,
                "decision": log.decision,
                "confidence": log.confidence,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None
            }
            for log in logs
        ]
    except Exception as e:
        logger.error(f"Error listing audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# FHIR TESTING ENDPOINTS
# ============================================================================

@router.post("/test/process-claim")
@router.post("/fhir/process")
async def process_fhir_bundle(data: Dict[str, Any]):
    """Process FHIR bundle through mock adjudication (for testing)"""
    try:
        bundle = data.get("bundle", {})
        
        # Extract patient info
        patient_name = "Unknown Patient"
        diagnoses = []
        procedures = []
        
        if "entry" in bundle:
            for entry in bundle.get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Patient":
                    names = resource.get("name", [])
                    if names:
                        given = " ".join(names[0].get("given", []))
                        family = names[0].get("family", "")
                        patient_name = f"{given} {family}".strip() or "Unknown Patient"
                elif resource.get("resourceType") == "Condition":
                    code = resource.get("code", {}).get("coding", [{}])[0]
                    diagnoses.append(code.get("display", "Unknown Condition"))
                elif resource.get("resourceType") == "Procedure":
                    code = resource.get("code", {}).get("coding", [{}])[0]
                    procedures.append(code.get("display", "Unknown Procedure"))
        
        # Generate mock results
        import hashlib
        bundle_hash = hashlib.md5(str(bundle).encode()).hexdigest()[:8].upper()
        
        results = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "completed",
            "patient_name": patient_name,
            "medical_rules": {
                "applied": "Emergency Admission Auto-Approval" if diagnoses else "Standard Processing",
                "coverage": "covered",
                "medical_necessity": "verified",
                "rules_matched": 1,
                "diagnoses_covered": diagnoses
            },
            "fraud_detection": {
                "risk_score": 2.3,
                "risk_level": "low",
                "anomalies_detected": False,
                "provider_verified": True,
                "patterns": []
            },
            "llm_analysis": {
                "clinical_summary": f"Patient {patient_name} with conditions: {', '.join(diagnoses or ['No diagnoses'])}. Procedures: {', '.join(procedures or ['None'])}.",
                "insights": [
                    "Diagnosis aligns with ICD-10 coding standards",
                    "Procedure complexity: Standard level",
                    "Expected recovery timeline: 3-5 days",
                    "No contraindications detected"
                ],
                "confidence": 87.5
            },
            "decision": {
                "status": "approved",
                "amount_approved": 45000,
                "currency": "SAR",
                "patient_responsibility": 5000,
                "copay_percentage": 10,
                "authorization_number": f"AUTH-2025-{bundle_hash}",
                "validity_days": 30
            }
        }
        
        logger.info(f"Processed FHIR bundle for patient: {patient_name}")
        return results
    except Exception as e:
        logger.error(f"Error processing FHIR bundle: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test/sample-fhir")
async def get_sample_fhir():
    """Get sample FHIR bundle for testing"""
    return {
        "resourceType": "Bundle",
        "id": "sample-bundle-001",
        "type": "transaction",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": "patient-001",
                    "identifier": [{"system": "http://example.com/mrn", "value": "1234567890"}],
                    "name": [{"use": "official", "given": ["Ahmed"], "family": "Al-Mutairi"}],
                    "gender": "male",
                    "birthDate": "1980-05-15",
                    "address": [{"city": "Riyadh", "country": "SA"}]
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-001",
                    "code": {
                        "coding": [{
                            "system": "http://hl7.org/fhir/sid/icd-10",
                            "code": "E11.9",
                            "display": "Type 2 Diabetes Mellitus"
                        }]
                    },
                    "subject": {"reference": "Patient/patient-001"}
                }
            },
            {
                "resource": {
                    "resourceType": "Procedure",
                    "id": "procedure-001",
                    "code": {
                        "coding": [{
                            "system": "http://www.ama-assn.org/go/cpt",
                            "code": "99213",
                            "display": "Office Visit"
                        }]
                    },
                    "subject": {"reference": "Patient/patient-001"}
                }
            }
        ]
    }
