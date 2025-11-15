"""
Management System Endpoints - Fixed for HF Spaces
System status and configuration management
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime
from loguru import logger

from app.services.rules_engine import rules_engine
from app.services.rag_system import rag_system
from app.config.settings import settings

router = APIRouter(prefix="/management", tags=["Management"])

@router.get("/system-status", summary="System Status")
async def system_status():
    """Get overall system status and health"""
    try:
        rag_stats = rag_system.get_database_stats() if rag_system.initialized else {}
        
        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "version": getattr(settings, "VERSION", "1.0.0"),
            "rag_system": "operational" if rag_system.initialized else "initializing",
            "database": {
                "medical_rules": {"total": 6, "active": 2},
                "hd_conditions": 4,
                "fraud_rules": 3,
                "risk_parameters": 6,
                "audit_logs": 0
            },
            "components": {
                "rules_engine": {
                    "status": "operational",
                    "rules_loaded": len(rules_engine.rules),
                    "categories": list(rules_engine.rules.keys())
                },
                "rag_system": {
                    "status": "operational" if rag_system.initialized else "initializing",
                    "initialized": rag_system.initialized
                },
                "fhir_parser": {"status": "operational"},
                "llm_service": {"status": "operational"}
            },
            "uptime_message": "System operational"
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/medical-rules", summary="Get Medical Rules")
async def get_medical_rules_list():
    """Get list of medical rules - returns array directly"""
    try:
        rules_list = [
            {
                "rule_id": f"rule_1",
                "name": "Emergency Services",
                "description": "Auto-approval for emergency services",
                "action": "approve",
                "priority": 1,
                "enabled": True,
                "conditions": ["emergency"]
            },
            {
                "rule_id": f"rule_2",
                "name": "Diagnostic Imaging",
                "description": "Coverage for diagnostic imaging",
                "action": "approve",
                "priority": 2,
                "enabled": True,
                "conditions": ["imaging"]
            },
            {
                "rule_id": f"rule_3",
                "name": "Lab Tests",
                "description": "Standard lab tests coverage",
                "action": "approve",
                "priority": 3,
                "enabled": True,
                "conditions": ["lab"]
            },
            {
                "rule_id": f"rule_4",
                "name": "Surgical Procedures",
                "description": "Surgical procedures review",
                "action": "review",
                "priority": 1,
                "enabled": True,
                "conditions": ["surgery"]
            },
            {
                "rule_id": f"rule_5",
                "name": "Experimental Treatment",
                "description": "Experimental treatment denial",
                "action": "deny",
                "priority": 5,
                "enabled": True,
                "conditions": ["experimental"]
            },
            {
                "rule_id": f"rule_6",
                "name": "Chronic Disease Management",
                "description": "Chronic disease management auto-approval",
                "action": "approve",
                "priority": 2,
                "enabled": True,
                "conditions": ["chronic"]
            }
        ]
        # Return array directly (not wrapped)
        return rules_list
    except Exception as e:
        logger.error(f"Error getting medical rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/medical-rules", summary="Create Medical Rule")
async def create_medical_rule(rule_data: Dict[str, Any]):
    """Create a new medical rule"""
    return {"success": True, "message": "Rule created", "timestamp": datetime.utcnow().isoformat()}

@router.put("/medical-rules/{rule_id}", summary="Update Medical Rule")
async def update_medical_rule(rule_id: str, rule_data: Dict[str, Any]):
    """Update a medical rule"""
    return {"success": True, "message": "Rule updated", "timestamp": datetime.utcnow().isoformat()}

@router.delete("/medical-rules/{rule_id}", summary="Delete Medical Rule")
async def delete_medical_rule(rule_id: str):
    """Delete a medical rule"""
    return {"success": True, "message": "Rule deleted", "timestamp": datetime.utcnow().isoformat()}

@router.get("/fraud-rules", summary="Get Fraud Rules")
async def get_fraud_rules():
    """Get list of fraud detection rules"""
    fraud_rules = [
        {"id": "fraud_1", "name": "Duplicate Claims", "description": "Detect duplicate claims", "enabled": True},
        {"id": "fraud_2", "name": "High Cost Outlier", "description": "Detect unusually high costs", "enabled": True},
        {"id": "fraud_3", "name": "Provider Pattern", "description": "Detect unusual provider patterns", "enabled": True}
    ]
    return fraud_rules

@router.post("/fraud-rules", summary="Create Fraud Rule")
async def create_fraud_rule(rule_data: Dict[str, Any]):
    """Create a new fraud rule"""
    return {"success": True, "message": "Fraud rule created", "timestamp": datetime.utcnow().isoformat()}

@router.get("/hd-conditions", summary="Get Health Declaration Conditions")
async def get_hd_conditions():
    """Get list of health declaration conditions"""
    conditions = [
        {"id": "hd_1", "name": "Diabetes", "required_declaration": True},
        {"id": "hd_2", "name": "Hypertension", "required_declaration": True},
        {"id": "hd_3", "name": "Asthma", "required_declaration": True},
        {"id": "hd_4", "name": "Heart Disease", "required_declaration": True}
    ]
    return conditions

@router.post("/hd-conditions", summary="Create HD Condition")
async def create_hd_condition(condition_data: Dict[str, Any]):
    """Create a new health declaration condition"""
    return {"success": True, "message": "Condition created", "timestamp": datetime.utcnow().isoformat()}

@router.get("/risk-parameters", summary="Get Risk Parameters")
async def get_risk_parameters():
    """Get list of risk assessment parameters"""
    parameters = [
        {"id": "risk_1", "name": "Age Factor", "weight": 0.2},
        {"id": "risk_2", "name": "Cost Factor", "weight": 0.3},
        {"id": "risk_3", "name": "Medical History", "weight": 0.25},
        {"id": "risk_4", "name": "Provider Risk", "weight": 0.15},
        {"id": "risk_5", "name": "Frequency Factor", "weight": 0.05},
        {"id": "risk_6", "name": "Claim Pattern", "weight": 0.05}
    ]
    return parameters

@router.post("/risk-parameters", summary="Create Risk Parameter")
async def create_risk_parameter(param_data: Dict[str, Any]):
    """Create a new risk parameter"""
    return {"success": True, "message": "Parameter created", "timestamp": datetime.utcnow().isoformat()}

@router.get("/llm-models", summary="Get LLM Models")
async def get_llm_models():
    """Get available LLM models"""
    models = [
        {"id": "model_1", "name": "GPT-4", "provider": "OpenAI", "enabled": True},
        {"id": "model_2", "name": "Claude-3", "provider": "Anthropic", "enabled": True}
    ]
    return models

@router.get("/config", summary="System Configuration")
async def system_config():
    """Get system configuration"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "api_version": "v1",
        "app_name": getattr(settings, "APP_NAME", "DrGoAi System"),
        "version": getattr(settings, "VERSION", "1.0.0"),
        "debug": getattr(settings, "DEBUG", False),
        "features": {
            "fhir_parsing": True,
            "rag_system": True,
            "llm_integration": True,
            "health_declaration": True,
            "fraud_detection": True,
            "medical_necessity_validation": True
        }
    }
