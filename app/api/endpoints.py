"""
API Endpoints for Pre-Authorization Adjudication
With Health Declaration (HD) Layer Integration
"""
from fastapi import APIRouter, HTTPException, status, Body
from typing import Dict, Any, Optional
from datetime import datetime
import time
from loguru import logger

from app.models.fhir_models import Bundle
from app.models.response_models import (
    AdjudicationResult,
    DecisionType,
    ErrorResponse
)
from app.services.fhir_parser import fhir_parser
from app.services.decision_orchestrator import decision_orchestrator
from app.services.rag_system import rag_system
from app.services.rules_engine import rules_engine
from app.services.llm_service import llm_service
from app.services.health_declaration_validator import health_declaration_validator
from app.config.settings import settings

router = APIRouter()

@router.post(
    "/preauth/adjudicate",
    response_model=AdjudicationResult,
    summary="Adjudicate Pre-Authorization Request with HD Validation",
    description="Process NPHIES FHIR pre-authorization with Health Declaration validation: HD > Rules > RAG > LLM"
)
async def adjudicate_preauth(
    bundle_data: Dict[str, Any],
    policy_start_date: Optional[str] = Body(None, description="Member's policy start date (ISO format)")
):
    """
    Main adjudication endpoint with Health Declaration pre-screening
    
    Decision Layers (in priority order):
    0. **Health Declaration** (Pre-screening) - Validates declared conditions
    1. **Rules Engine** (95% confidence) - Auto-approve/deny based on hard rules
    2. **RAG Policy System** (75-90% confidence) - Your internal policy guidelines
    3. **Medical LLM** (50-75% confidence) - Clinical reasoning for complex cases
    
    Health Declaration Logic:
    - Checks if diagnosis requires health declaration
    - Validates member's HD records
    - Checks policy start date vs diagnosis date
    - Flags for HITL if not declared
    - Denies if pre-existing within waiting period
    
    Higher layers ALWAYS override lower layers.
    """
    
    start_time = time.time()
    request_id = f"req-{int(time.time() * 1000)}"
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing request: {request_id}")
    logger.info(f"Policy Start Date: {policy_start_date or 'Not provided'}")
    logger.info(f"{'='*60}")
    
    try:
        # Step 1: Parse FHIR Bundle
        logger.info("Step 1: Parsing FHIR bundle...")
        clinical_data = fhir_parser.parse_bundle(bundle_data)
        logger.info(f"  ✓ Parsed clinical data for patient {clinical_data.patient_id}")
        
        # Step 2: Use Decision Orchestrator (handles all layers including HD)
        logger.info("\nStep 2: Running Layered Adjudication with HD Pre-screening...")
        orchestration_result = decision_orchestrator.adjudicate_request(
            clinical_data,
            policy_start_date=policy_start_date
        )
        
        service_decisions = orchestration_result["service_decisions"]
        decision_path = orchestration_result["decision_path"]
        layer_results = orchestration_result["layer_results"]
        
        logger.info(f"\n✓ Adjudication complete!")
        logger.info(f"  Deciding layer: {orchestration_result['deciding_layer']}")
        logger.info(f"  Final confidence: {orchestration_result['final_confidence']:.2f}")
        
        # Check if HD blocked the request
        hd_blocked = orchestration_result.get("hd_blocked", False)
        if hd_blocked:
            logger.warning(f"  ⚠ Request blocked by Health Declaration validation")
        
        # Step 3: Compile Results
        logger.info("\nStep 3: Compiling final results...")
        
        # Calculate overall decision
        approved_count = sum(1 for d in service_decisions if d.decision == DecisionType.APPROVED)
        denied_count = sum(1 for d in service_decisions if d.decision == DecisionType.DENIED)
        pending_count = sum(1 for d in service_decisions if d.decision == DecisionType.PENDING)
        
        if approved_count == len(service_decisions):
            overall_decision = DecisionType.APPROVED
        elif denied_count == len(service_decisions):
            overall_decision = DecisionType.DENIED
        elif pending_count > 0:
            overall_decision = DecisionType.PENDING
        elif approved_count > 0:
            overall_decision = DecisionType.PARTIAL
        else:
            overall_decision = DecisionType.PENDING
        
        # Calculate financial summary
        total_requested = sum(d.requested_amount or 0 for d in service_decisions)
        total_approved = sum(d.approved_amount or 0 for d in service_decisions)
        total_denied = total_requested - total_approved
        
        # Build enhanced decision path for audit
        formatted_decision_path = [
            f"1. FHIR Bundle Parsed: Patient {clinical_data.patient_id}",
        ]
        
        # Add HD layer info if present
        hd_result = layer_results.get("health_declaration", {})
        if hd_result:
            formatted_decision_path.append(f"2. Health Declaration Pre-Screening:")
            if hd_result.get("hd_validation_required"):
                formatted_decision_path.append(
                    f"   ⚠ HD Required: {len(hd_result.get('hd_conditions_found', []))} condition(s)"
                )
                formatted_decision_path.append(
                    f"   Status: {hd_result.get('hd_status', 'unknown')}"
                )
                formatted_decision_path.append(
                    f"   Action: {hd_result.get('action', 'unknown')}"
                )
                if hd_result.get("reason"):
                    formatted_decision_path.append(f"   Reason: {hd_result['reason']}")
            else:
                formatted_decision_path.append("   ✓ No HD validation required")
        
        formatted_decision_path.append(f"3. Core Adjudication Layers:")
        
        for i, step in enumerate(decision_path):
            layer_name = step["layer"]
            decision = step["decision"]
            confidence = step["confidence"]
            is_final = step.get("final", False)
            
            status_icon = "✓ FINAL" if is_final else "→ PASS"
            formatted_decision_path.append(
                f"   {status_icon} {layer_name}: {decision} (confidence: {confidence:.2f})"
            )
            
            if "reason" in step:
                formatted_decision_path.append(f"      Reason: {step['reason']}")
        
        # Add validation results to path
        formatted_decision_path.append(f"4. Validation Layers:")
        
        # Medical necessity
        med_necessity = orchestration_result["validation_results"].get("medical_necessity", {})
        if med_necessity:
            formatted_decision_path.append(
                f"   ✓ Medical Necessity: {'VALID' if med_necessity.get('overall_valid') else 'CONCERNS'} "
                f"(score: {med_necessity.get('score', 1.0):.2f})"
            )
        
        # Patient history
        pat_history = orchestration_result["validation_results"].get("patient_history", {})
        if pat_history:
            formatted_decision_path.append(
                f"   ✓ Patient History: Risk {pat_history.get('risk_score', 0.0):.2f} "
                f"({len(pat_history.get('flags', []))} flags)"
            )
        
        # Financial risk
        fin_risk = orchestration_result["validation_results"].get("financial_risk", {})
        if fin_risk:
            formatted_decision_path.append(
                f"   ✓ Financial Risk: {fin_risk.get('risk_level', 'LOW')} "
                f"(score: {fin_risk.get('risk_score', 0.0):.2f})"
            )
        
        # Fraud detection
        fraud = orchestration_result["validation_results"].get("fraud_detection", {})
        if fraud:
            formatted_decision_path.append(
                f"   ✓ Fraud Detection: {fraud.get('fraud_risk', 'LOW')} "
                f"({'Investigation required' if fraud.get('requires_investigation') else 'Clear'})"
            )
        
        # HITL
        hitl_reviews_required = sum(1 for h in orchestration_result.get("hitl_results", []) 
                                    if h.get("requires_review"))
        formatted_decision_path.append(
            f"   ✓ HITL Review: {hitl_reviews_required}/{len(service_decisions)} services require review"
        )
        
        formatted_decision_path.append(
            f"5. Final Decision: {overall_decision.value} (decided by {orchestration_result['deciding_layer']})"
        )
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Get RAG stats
        rag_chunks = len(layer_results.get("rag_system", []))
        
        # Build response
        result = AdjudicationResult(
            request_id=request_id,
            timestamp=datetime.utcnow(),
            overall_decision=overall_decision,
            overall_confidence=orchestration_result["final_confidence"],
            service_decisions=service_decisions,
            total_requested=total_requested,
            total_approved=total_approved,
            total_denied=total_denied,
            patient_responsibility=0.0,
            processing_time_ms=processing_time_ms,
            llm_model_used=settings.Gemeni,
            rag_chunks_retrieved=rag_chunks,
            rules_evaluated=len(layer_results.get("rules_engine", {}).get("rules_triggered", [])),
            decision_path=formatted_decision_path,
            recommendations=_generate_recommendations(service_decisions, layer_results.get("rules_engine", {}), hd_result),
            requires_additional_documentation=any(
                d.requires_human_review for d in service_decisions
            ),
            missing_information=_identify_missing_info(clinical_data, layer_results.get("rules_engine", {})),
            appeal_rights="Member has the right to appeal any denied services within 30 days",
            appeal_deadline_days=30
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Request {request_id} completed in {processing_time_ms}ms")
        logger.info(f"Overall: {overall_decision.value}, Confidence: {orchestration_result['final_confidence']:.2f}")
        if hd_blocked:
            logger.warning(f"HD Status: Request blocked by Health Declaration layer")
        logger.info(f"{'='*60}\n")
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Adjudication error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error during adjudication: {str(e)}"
        )

# === HEALTH DECLARATION ENDPOINTS ===

@router.post(
    "/hd/add",
    summary="Add Health Declaration Record",
    description="Add a health declaration record for a member"
)
async def add_health_declaration(
    member_id: str = Body(..., description="Member/Patient ID"),
    icd10_code: str = Body(..., description="ICD10 code of condition"),
    condition_name: str = Body(..., description="Name of condition"),
    diagnosis_date: str = Body(..., description="Date of diagnosis (ISO format)"),
    declaration_date: str = Body(..., description="Date of declaration (ISO format)"),
    declared_by: str = Body("member", description="Who declared (member/physician/system)")
):
    """
    Add a health declaration record to the database
    
    Example:
    ```json
    {
        "member_id": "PAT001",
        "icd10_code": "E11",
        "condition_name": "Type 2 Diabetes Mellitus",
        "diagnosis_date": "2023-01-15",
        "declaration_date": "2023-06-01",
        "declared_by": "member"
    }
    ```
    """
    try:
        success = health_declaration_validator.add_member_hd_record(
            member_id=member_id,
            icd10_code=icd10_code,
            condition_name=condition_name,
            diagnosis_date=diagnosis_date,
            declaration_date=declaration_date,
            declared_by=declared_by
        )
        
        return {
            "success": success,
            "message": f"Health declaration added for member {member_id}",
            "condition": condition_name,
            "icd10": icd10_code,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error adding HD record: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding health declaration: {str(e)}"
        )

@router.get(
    "/hd/member/{member_id}",
    summary="Get Member's Health Declarations",
    description="Retrieve all health declarations for a specific member"
)
async def get_member_health_declarations(member_id: str):
    """Get all health declaration records for a member"""
    try:
        summary = health_declaration_validator.get_member_hd_summary(member_id)
        
        return {
            **summary,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error retrieving HD records: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving health declarations: {str(e)}"
        )

@router.get(
    "/hd/conditions",
    summary="Get HD-Required Conditions",
    description="Get list of all conditions that require health declaration"
)
async def get_hd_required_conditions():
    """Get all conditions that require health declaration"""
    conditions = health_declaration_validator.hd_required_conditions
    
    return {
        "total_conditions": len(conditions),
        "conditions": [
            {
                "icd10_code": code,
                "name": info["name"],
                "category": info["category"],
                "severity": info["severity"],
                "waiting_period_days": info["waiting_period_days"]
            }
            for code, info in conditions.items()
        ],
        "timestamp": datetime.utcnow()
    }

@router.get(
    "/hd/check/{icd10_code}",
    summary="Check if Condition Requires HD",
    description="Check if a specific ICD10 code requires health declaration"
)
async def check_hd_requirement(icd10_code: str):
    """Check if a specific ICD10 code requires health declaration"""
    required = health_declaration_validator.is_condition_hd_required(icd10_code)
    
    condition_info = None
    if required:
        # Find matching condition
        for code, info in health_declaration_validator.hd_required_conditions.items():
            if icd10_code == code or icd10_code.startswith(code):
                condition_info = info
                break
    
    return {
        "icd10_code": icd10_code,
        "hd_required": required,
        "condition_info": condition_info,
        "timestamp": datetime.utcnow()
    }

# === EXISTING ENDPOINTS (keeping all previous endpoints) ===

@router.get(
    "/health",
    summary="Health Check",
    description="Check if the adjudication service is healthy and all components are loaded"
)
async def health_check():
    """Health check endpoint with HD validator status"""
    
    models_loaded = {
        "rules_engine": bool(rules_engine.rules),
        "rag_system": rag_system.initialized,
        "llm_service": (llm_service.use_gemini or llm_service.pipeline is not None),
        "health_declaration": True,
        "decision_orchestrator": True
    }
    
    all_loaded = all(models_loaded.values())
    
    # Get RAG system details
    rag_details = rag_system.get_database_stats() if rag_system.initialized else {}
    
    # Get HD stats
    hd_stats = {
        "hd_required_conditions": len(health_declaration_validator.hd_required_conditions),
        "members_with_hd": len(health_declaration_validator.member_hd_database)
    }
    
    return {
        "status": "healthy" if all_loaded else "degraded",
        "timestamp": datetime.utcnow(),
        "version": settings.VERSION,
        "models_loaded": models_loaded,
        "rag_system": rag_details,
        "health_declaration": hd_stats,
        "decision_hierarchy": "Health Declaration > Rules Engine > RAG ChromaDB > Medical LLM"
    }

@router.get(
    "/policies/stats",
    summary="Get Policy Database Statistics",
    description="Get information about policies stored in ChromaDB"
)
async def get_policy_stats():
    """Get statistics about the policy database"""
    stats = rag_system.get_database_stats()
    
    return {
        "timestamp": datetime.utcnow(),
        **stats,
        "message": "Add policies via /policies/add endpoint or by placing files in data/policies/"
    }

@router.post(
    "/policies/search",
    summary="Search Policy Database",
    description="Search for specific policy information in ChromaDB"
)
async def search_policies(query: str, top_k: int = 5):
    """Search the policy database directly"""
    if not rag_system.initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG system not initialized"
        )
    
    results = rag_system.search_policies(query, top_k)
    
    return {
        "query": query,
        "results_found": len(results),
        "results": results,
        "timestamp": datetime.utcnow()
    }

@router.post(
    "/policies/add",
    summary="Add Policy to ChromaDB",
    description="Add a policy document to the ChromaDB vector store"
)
async def add_policy(
    content: str,
    source: str,
    policy_type: str = "general",
    version: str = "1.0"
):
    """Add a policy document to ChromaDB"""
    if not rag_system.initialized:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG system not initialized"
        )
    
    try:
        metadata = {
            "source": source,
            "type": policy_type,
            "version": version,
            "added_at": datetime.utcnow().isoformat(),
            "added_via": "api"
        }
        
        chunks_added = rag_system.add_policy_document(content, metadata)
        
        logger.info(f"✓ Added policy '{source}' to ChromaDB ({chunks_added} chunks)")
        
        return {
            "success": True,
            "source": source,
            "chunks_added": chunks_added,
            "policy_type": policy_type,
            "version": version,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error adding policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding policy: {str(e)}"
        )

@router.get(
    "/decision/layers",
    summary="Get Decision Layer Information",
    description="Get information about the layered decision-making system with HD"
)
async def get_decision_layers():
    """Get information about decision layers and their hierarchy"""
    return {
        **decision_orchestrator.get_layer_statistics(),
        "description": """
        The system uses a 4-layer decision hierarchy with HD pre-screening:
        
        Layer 0 - Health Declaration (PRE-SCREENING):
        - Confidence: 95-99%
        - Validates if conditions require health declaration
        - Checks member's HD records and policy dates
        - Blocks request for HITL if not declared
        - Denies if pre-existing within waiting period
        
        Layer 1 - Rules Engine (HIGHEST):
        - Confidence: 90-99%
        - Auto-approve or auto-deny based on hard rules
        - Overrides all lower layers
        
        Layer 2 - RAG Policy System (HIGH):
        - Confidence: 75-90%
        - Retrieves exact policy matches from ChromaDB
        - Your internal guidelines have authority here
        - Overrides LLM but not Rules Engine
        
        Layer 3 - Medical LLM (MEDIUM):
        - Confidence: 50-75%
        - Clinical reasoning for complex cases
        - Used when rules and policies don't provide clear answer
        - Can be overridden by Rules, RAG, or HD
        """,
        "timestamp": datetime.utcnow()
    }

@router.get(
    "/rules",
    summary="Get Active Rules",
    description="Retrieve currently active adjudication rules"
)
async def get_rules():
    """Get active rules configuration"""
    return {
        "rules_version": "1.0",
        "last_updated": datetime.utcnow(),
        "rules_summary": {
            "total_rules": len(rules_engine.rules),
            "categories": list(rules_engine.rules.keys()),
            "auto_approve_rules": len(
                rules_engine.rules.get("coverage_rules", {}).get("auto_approve", [])
            ),
            "auto_deny_rules": len(
                rules_engine.rules.get("coverage_rules", {}).get("auto_deny", [])
            ),
            "excluded_services": len(
                rules_engine.rules.get("excluded_services", [])
            )
        }
    }

def _generate_recommendations(
    service_decisions: list,
    rules_results: Dict[str, Any],
    hd_result: Dict[str, Any] = None
) -> list:
    """Generate recommendations for the provider"""
    recommendations = []
    
    # HD-related recommendations
    if hd_result and hd_result.get("requires_hitl"):
        recommendations.append(
            f"Member must provide health declaration for: {', '.join(hd_result.get('flagged_conditions', []))}"
        )
    
    if hd_result and hd_result.get("action") == "deny_pre_existing":
        recommendations.append(
            "Services denied due to pre-existing condition within waiting period. "
            "Member may resubmit after waiting period expires."
        )
    
    # Check for denied services
    denied_services = [d for d in service_decisions if d.decision == DecisionType.DENIED]
    if denied_services:
        recommendations.append(
            "Review denied services and consider alternative treatments covered under the policy"
        )
    
    # Check for services requiring review
    review_services = [d for d in service_decisions if d.requires_human_review]
    if review_services:
        recommendations.append(
            "Additional clinical documentation may improve approval chances for pending services"
        )
    
    # Check risk flags
    risk_flags = rules_results.get("risk_flags", [])
    if "high_cost_service" in risk_flags:
        recommendations.append(
            "Consider discussing alternative lower-cost options with the patient"
        )
    
    return recommendations

def _identify_missing_info(
    clinical_data,
    rules_results: Dict[str, Any]
) -> list:
    """Identify missing information that could improve adjudication"""
    missing = []
    
    if not clinical_data.clinical_notes:
        missing.append("Clinical notes and justification")
    
    if not clinical_data.diagnoses:
        missing.append("Primary and secondary diagnoses")
    
    if rules_results.get("rule_results", {}).get("medical_necessity", {}).get("triggers"):
        triggers = rules_results["rule_results"]["medical_necessity"]["triggers"]
        if "missing_clinical_notes" in triggers:
            missing.append("Detailed clinical rationale for medical necessity")
    
    return missing
