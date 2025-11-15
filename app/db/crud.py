"""
CRUD Operations
Database operations for all entities
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.db.models import MedicalRule, HDCondition, FraudRule, RiskParameter, AuditLog, SystemMetrics

# ============================================================================
# MEDICAL RULES CRUD
# ============================================================================

def create_medical_rule(db: Session, rule_data: Dict[str, Any]) -> MedicalRule:
    rule = MedicalRule(**rule_data)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

def get_medical_rules(db: Session, skip: int = 0, limit: int = 100) -> List[MedicalRule]:
    return db.query(MedicalRule).offset(skip).limit(limit).all()

def get_medical_rule(db: Session, rule_id: str) -> Optional[MedicalRule]:
    return db.query(MedicalRule).filter(MedicalRule.rule_id == rule_id).first()

def update_medical_rule(db: Session, rule_id: str, rule_data: Dict[str, Any]) -> Optional[MedicalRule]:
    rule = get_medical_rule(db, rule_id)
    if rule:
        for key, value in rule_data.items():
            setattr(rule, key, value)
        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)
    return rule

def delete_medical_rule(db: Session, rule_id: str) -> bool:
    rule = get_medical_rule(db, rule_id)
    if rule:
        db.delete(rule)
        db.commit()
        return True
    return False

def toggle_medical_rule(db: Session, rule_id: str) -> Optional[MedicalRule]:
    rule = get_medical_rule(db, rule_id)
    if rule:
        rule.enabled = not rule.enabled
        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)
    return rule

# ============================================================================
# HD CONDITIONS CRUD
# ============================================================================

def create_hd_condition(db: Session, condition_data: Dict[str, Any]) -> HDCondition:
    condition = HDCondition(**condition_data)
    db.add(condition)
    db.commit()
    db.refresh(condition)
    return condition

def get_hd_conditions(db: Session, skip: int = 0, limit: int = 100) -> List[HDCondition]:
    return db.query(HDCondition).offset(skip).limit(limit).all()

def get_hd_condition(db: Session, condition_id: str) -> Optional[HDCondition]:
    return db.query(HDCondition).filter(HDCondition.condition_id == condition_id).first()

def update_hd_condition(db: Session, condition_id: str, condition_data: Dict[str, Any]) -> Optional[HDCondition]:
    condition = get_hd_condition(db, condition_id)
    if condition:
        for key, value in condition_data.items():
            setattr(condition, key, value)
        condition.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(condition)
    return condition

def delete_hd_condition(db: Session, condition_id: str) -> bool:
    condition = get_hd_condition(db, condition_id)
    if condition:
        db.delete(condition)
        db.commit()
        return True
    return False

# ============================================================================
# FRAUD RULES CRUD
# ============================================================================

def create_fraud_rule(db: Session, rule_data: Dict[str, Any]) -> FraudRule:
    rule = FraudRule(**rule_data)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule

def get_fraud_rules(db: Session, skip: int = 0, limit: int = 100) -> List[FraudRule]:
    return db.query(FraudRule).offset(skip).limit(limit).all()

def get_fraud_rule(db: Session, rule_id: str) -> Optional[FraudRule]:
    return db.query(FraudRule).filter(FraudRule.rule_id == rule_id).first()

def update_fraud_rule(db: Session, rule_id: str, rule_data: Dict[str, Any]) -> Optional[FraudRule]:
    rule = get_fraud_rule(db, rule_id)
    if rule:
        for key, value in rule_data.items():
            setattr(rule, key, value)
        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)
    return rule

def delete_fraud_rule(db: Session, rule_id: str) -> bool:
    rule = get_fraud_rule(db, rule_id)
    if rule:
        db.delete(rule)
        db.commit()
        return True
    return False

def toggle_fraud_rule(db: Session, rule_id: str) -> Optional[FraudRule]:
    rule = get_fraud_rule(db, rule_id)
    if rule:
        rule.enabled = not rule.enabled
        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)
    return rule

# ============================================================================
# RISK PARAMETERS CRUD
# ============================================================================

def create_risk_parameter(db: Session, param_data: Dict[str, Any]) -> RiskParameter:
    param = RiskParameter(**param_data)
    db.add(param)
    db.commit()
    db.refresh(param)
    return param

def get_risk_parameters(db: Session, skip: int = 0, limit: int = 100) -> List[RiskParameter]:
    return db.query(RiskParameter).offset(skip).limit(limit).all()

def get_risk_parameter(db: Session, param_id: str) -> Optional[RiskParameter]:
    return db.query(RiskParameter).filter(RiskParameter.param_id == param_id).first()

def update_risk_parameter(db: Session, param_id: str, param_data: Dict[str, Any]) -> Optional[RiskParameter]:
    param = get_risk_parameter(db, param_id)
    if param:
        for key, value in param_data.items():
            setattr(param, key, value)
        param.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(param)
    return param

def delete_risk_parameter(db: Session, param_id: str) -> bool:
    param = get_risk_parameter(db, param_id)
    if param:
        db.delete(param)
        db.commit()
        return True
    return False

# ============================================================================
# AUDIT LOGS
# ============================================================================

def create_audit_log(db: Session, log_data: Dict[str, Any]) -> AuditLog:
    log = AuditLog(**log_data)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def get_audit_logs(db: Session, skip: int = 0, limit: int = 100) -> List[AuditLog]:
    return db.query(AuditLog).order_by(desc(AuditLog.timestamp)).offset(skip).limit(limit).all()

# ============================================================================
# SYSTEM METRICS
# ============================================================================

def record_metric(db: Session, metric_name: str, metric_value: float, meta_data: Optional[Dict] = None):
    metric = SystemMetrics(
        metric_name=metric_name,
        metric_value=metric_value,
        meta_data=meta_data
    )
    db.add(metric)
    db.commit()

def get_system_stats(db: Session) -> Dict[str, Any]:
    """Get aggregated system statistics"""
    total_rules = db.query(func.count(MedicalRule.id)).scalar()
    active_rules = db.query(func.count(MedicalRule.id)).filter(MedicalRule.enabled == True).scalar()
    total_hd_conditions = db.query(func.count(HDCondition.id)).scalar()
    total_fraud_rules = db.query(func.count(FraudRule.id)).scalar()
    total_risk_params = db.query(func.count(RiskParameter.id)).scalar()
    total_audits = db.query(func.count(AuditLog.id)).scalar()
    
    return {
        "medical_rules": {
            "total": total_rules,
            "active": active_rules,
            "inactive": total_rules - active_rules
        },
        "hd_conditions": total_hd_conditions,
        "fraud_rules": total_fraud_rules,
        "risk_parameters": total_risk_params,
        "audit_logs": total_audits
    }
