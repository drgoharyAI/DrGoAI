"""
API Response Models for Adjudication Results
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DecisionType(str, Enum):
    """Adjudication decision types"""
    APPROVED = "A"  # Approved
    DENIED = "D"  # Denied
    PARTIAL = "P"  # Partially Approved
    PENDING = "PENDING"  # Requires Human Review
    ERROR = "ERROR"  # Processing Error

class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ServiceDecision(BaseModel):
    """Decision for individual service/item"""
    service_sequence: int
    service_code: str
    service_description: str
    requested_amount: Optional[float] = None
    
    decision: DecisionType
    approved_amount: Optional[float] = None
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    confidence_level: ConfidenceLevel
    
    # Explanation
    explanation: str
    clinical_rationale: Optional[str] = None
    policy_reference: List[str] = []  # Policy sections used
    rules_applied: List[str] = []  # Rule IDs that influenced decision
    
    # Flags
    requires_human_review: bool = False
    review_reason: Optional[str] = None
    medical_necessity_met: Optional[bool] = None

class AdjudicationResult(BaseModel):
    """Main adjudication response"""
    request_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Overall Decision
    overall_decision: DecisionType
    overall_confidence: float = Field(ge=0.0, le=1.0)
    
    # Service-Level Decisions
    service_decisions: List[ServiceDecision]
    
    # Financial Summary
    total_requested: Optional[float] = None
    total_approved: Optional[float] = None
    total_denied: Optional[float] = None
    patient_responsibility: Optional[float] = None
    
    # Processing Details
    processing_time_ms: int
    llm_model_used: str
    rag_chunks_retrieved: int
    rules_evaluated: int
    
    # Audit Trail
    decision_path: List[str] = []  # Step-by-step decision process
    
    # Additional Information
    recommendations: List[str] = []
    requires_additional_documentation: bool = False
    missing_information: List[str] = []
    
    # Appeals Information
    appeal_rights: Optional[str] = None
    appeal_deadline_days: Optional[int] = 30

class HealthCheckResponse(BaseModel):
    """Health check endpoint response"""
    status: str
    timestamp: datetime
    version: str
    models_loaded: Dict[str, bool]

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

class ValidationError(BaseModel):
    """Validation error details"""
    field: str
    message: str
    value: Optional[Any] = None

class ValidationErrorResponse(BaseModel):
    """Response for validation errors"""
    error: str = "Validation Error"
    details: List[ValidationError]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Audit Log Model
class AuditLog(BaseModel):
    """Audit log entry for compliance"""
    request_id: str
    timestamp: datetime
    patient_id: str
    provider_id: str
    insurer_id: Optional[str]
    
    decision: DecisionType
    confidence: float
    
    # Decision Components
    rules_triggered: List[str]
    policy_sections: List[str]
    llm_reasoning: str
    
    # Metadata
    processing_time_ms: int
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    
    # Compliance
    reviewed_by: Optional[str] = None
    review_date: Optional[datetime] = None
    appeal_status: Optional[str] = None
