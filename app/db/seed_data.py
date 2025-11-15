"""
Database Seeding
Populate database with initial data
"""
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db import crud
from loguru import logger

def seed_initial_data():
    """Seed database with initial data if empty"""
    db = SessionLocal()
    try:
        # Check if data already exists
        existing_rules = crud.get_medical_rules(db, limit=1)
        if existing_rules:
            logger.info("Database already seeded, skipping...")
            return
        
        # Seed Medical Rules
        medical_rules = [
            {
                "rule_id": "KSA_EMERGENCY_001",
                "name": "Emergency Admission Auto-Approval",
                "description": "Automatic approval for emergency admissions in hospitals",
                "enabled": True,
                "action": "APPROVE",
                "priority": 1,
                "conditions": ["admission_type=emergency"]
            },
            {
                "rule_id": "KSA_CHRONIC_001",
                "name": "Chronic Disease Management",
                "description": "Coverage for chronic disease management programs",
                "enabled": True,
                "action": "APPROVE",
                "priority": 2,
                "conditions": ["diagnosis_code=E11.9", "diagnosis_code=I10"]
            },
            {
                "rule_id": "KSA_PREVENTIVE_001",
                "name": "Preventive Care Services",
                "description": "Coverage for preventive health services",
                "enabled": True,
                "action": "APPROVE",
                "priority": 3,
                "conditions": ["procedure_code=preventive_*"]
            },
            {
                "rule_id": "KSA_SURGERY_001",
                "name": "Planned Surgery Coverage",
                "description": "Approval process for planned surgical procedures",
                "enabled": True,
                "action": "CONDITIONAL_APPROVAL",
                "priority": 2,
                "conditions": ["procedure_type=surgical"]
            },
            {
                "rule_id": "KSA_DENTAL_001",
                "name": "Dental Services",
                "description": "Coverage limits for dental procedures",
                "enabled": True,
                "action": "PARTIAL_APPROVAL",
                "priority": 4,
                "conditions": ["service_category=dental"]
            }
        ]
        
        for rule in medical_rules:
            crud.create_medical_rule(db, rule)
        logger.info(f"✓ Seeded {len(medical_rules)} medical rules")
        
        # Seed HD Conditions
        hd_conditions = [
            {
                "condition_id": "HD_DIABETES_001",
                "name": "Type 2 Diabetes",
                "icd_code": "E11.9",
                "waiting_period_months": 0,
                "coverage_percentage": 100,
                "severity": "MEDIUM"
            },
            {
                "condition_id": "HD_HYPERTENSION_001",
                "name": "Hypertension",
                "icd_code": "I10",
                "waiting_period_months": 0,
                "coverage_percentage": 100,
                "severity": "MEDIUM"
            },
            {
                "condition_id": "HD_ASTHMA_001",
                "name": "Asthma",
                "icd_code": "J45.9",
                "waiting_period_months": 3,
                "coverage_percentage": 80,
                "severity": "MEDIUM"
            },
            {
                "condition_id": "HD_CARDIAC_001",
                "name": "Cardiac Conditions",
                "icd_code": "I50",
                "waiting_period_months": 6,
                "coverage_percentage": 90,
                "severity": "HIGH"
            }
        ]
        
        for condition in hd_conditions:
            crud.create_hd_condition(db, condition)
        logger.info(f"✓ Seeded {len(hd_conditions)} HD conditions")
        
        # Seed Fraud Rules
        fraud_rules = [
            {
                "rule_id": "FRAUD_DUPLICATE_001",
                "name": "Duplicate Claims Detection",
                "description": "Detects duplicate claims within 24 hours",
                "enabled": True,
                "threshold": 0.95,
                "pattern_type": "duplicate_detection"
            },
            {
                "rule_id": "FRAUD_AMOUNT_001",
                "name": "Unusual Amount Detection",
                "description": "Flags claims significantly above average",
                "enabled": True,
                "threshold": 3.0,
                "pattern_type": "amount_anomaly"
            },
            {
                "rule_id": "FRAUD_PATTERN_001",
                "name": "Pattern Analysis",
                "description": "Detects suspicious provider patterns",
                "enabled": True,
                "threshold": 0.85,
                "pattern_type": "behavioral_pattern"
            }
        ]
        
        for rule in fraud_rules:
            crud.create_fraud_rule(db, rule)
        logger.info(f"✓ Seeded {len(fraud_rules)} fraud rules")
        
        # Seed Risk Parameters
        risk_parameters = [
            {
                "param_id": "RISK_AGE",
                "name": "Age Factor",
                "weight": 0.15,
                "description": "Patient age risk assessment",
                "enabled": True
            },
            {
                "param_id": "RISK_AMOUNT",
                "name": "Claim Amount",
                "weight": 0.25,
                "description": "Financial amount risk",
                "enabled": True
            },
            {
                "param_id": "RISK_DIAGNOSIS",
                "name": "Diagnosis Severity",
                "weight": 0.20,
                "description": "Medical diagnosis complexity",
                "enabled": True
            },
            {
                "param_id": "RISK_PROVIDER",
                "name": "Provider History",
                "weight": 0.20,
                "description": "Provider track record",
                "enabled": True
            },
            {
                "param_id": "RISK_FREQUENCY",
                "name": "Claim Frequency",
                "weight": 0.15,
                "description": "Frequency of claims",
                "enabled": True
            },
            {
                "param_id": "RISK_PATTERN",
                "name": "Pattern Anomaly",
                "weight": 0.05,
                "description": "Unusual patterns detection",
                "enabled": True
            }
        ]
        
        for param in risk_parameters:
            crud.create_risk_parameter(db, param)
        logger.info(f"✓ Seeded {len(risk_parameters)} risk parameters")
        
        logger.info("✓ Database seeding completed successfully")
        
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        db.rollback()
    finally:
        db.close()
