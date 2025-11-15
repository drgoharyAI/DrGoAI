"""
Database Models
SQLAlchemy ORM models for persistent storage
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base

class MedicalRule(Base):
    __tablename__ = "medical_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    enabled = Column(Boolean, default=True)
    action = Column(String(50), nullable=False)
    priority = Column(Integer, default=1)
    conditions = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(100))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class HDCondition(Base):
    __tablename__ = "hd_conditions"
    
    id = Column(Integer, primary_key=True, index=True)
    condition_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    icd_code = Column(String(20))
    waiting_period_months = Column(Integer, default=0)
    coverage_percentage = Column(Integer, default=100)
    severity = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class FraudRule(Base):
    __tablename__ = "fraud_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    enabled = Column(Boolean, default=True)
    threshold = Column(Float, default=0.85)
    pattern_type = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class RiskParameter(Base):
    __tablename__ = "risk_parameters"
    
    id = Column(Integer, primary_key=True, index=True)
    param_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    weight = Column(Float, default=0.1)
    description = Column(Text)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(100), index=True)
    user_id = Column(String(100))
    action = Column(String(50))
    decision = Column(String(20))
    confidence = Column(Float)
    input_data_hash = Column(String(64))
    reasoning = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class SystemMetrics(Base):
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    meta_data = Column(JSON)  # Renamed from 'metadata' - reserved by SQLAlchemy
