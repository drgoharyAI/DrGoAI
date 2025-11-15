"""
FHIR Data Models for NPHIES Pre-Authorization Requests
Based on FHIR R4 and NPHIES specifications
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ResourceType(str, Enum):
    BUNDLE = "Bundle"
    CLAIM = "Claim"
    PATIENT = "Patient"
    COVERAGE = "Coverage"
    PRACTITIONER = "Practitioner"
    ORGANIZATION = "Organization"
    CONDITION = "Condition"
    PROCEDURE = "Procedure"

class BundleType(str, Enum):
    COLLECTION = "collection"
    DOCUMENT = "document"
    MESSAGE = "message"
    TRANSACTION = "transaction"

class ClaimType(str, Enum):
    INSTITUTIONAL = "institutional"
    ORAL = "oral"
    PHARMACY = "pharmacy"
    PROFESSIONAL = "professional"
    VISION = "vision"

class ClaimUse(str, Enum):
    CLAIM = "claim"
    PREAUTHORIZATION = "preauthorization"
    PREDETERMINATION = "predetermination"

# FHIR Coding
class Coding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None

class CodeableConcept(BaseModel):
    coding: List[Coding] = []
    text: Optional[str] = None

# Patient Information
class PatientName(BaseModel):
    use: Optional[str] = None
    family: Optional[str] = None
    given: List[str] = []

class Patient(BaseModel):
    resourceType: str = "Patient"
    id: Optional[str] = None
    identifier: List[Dict[str, Any]] = []
    name: List[PatientName] = []
    gender: Optional[str] = None
    birthDate: Optional[str] = None
    address: List[Dict[str, Any]] = []

# Coverage Information
class Coverage(BaseModel):
    resourceType: str = "Coverage"
    id: Optional[str] = None
    identifier: List[Dict[str, Any]] = []
    status: str
    type: Optional[CodeableConcept] = None
    subscriber: Optional[Dict[str, str]] = None
    beneficiary: Dict[str, str]
    period: Optional[Dict[str, str]] = None
    payor: List[Dict[str, str]] = []

# Diagnosis
class Diagnosis(BaseModel):
    sequence: int
    diagnosisCodeableConcept: Optional[CodeableConcept] = None
    diagnosisReference: Optional[Dict[str, str]] = None
    type: List[CodeableConcept] = []
    onAdmission: Optional[CodeableConcept] = None

# Procedure Information
class ProcedureModel(BaseModel):
    sequence: int
    type: List[CodeableConcept] = []
    date: Optional[str] = None
    procedureCodeableConcept: Optional[CodeableConcept] = None
    procedureReference: Optional[Dict[str, str]] = None

# Item (Service/Product)
class ItemDetail(BaseModel):
    sequence: int
    productOrService: CodeableConcept
    quantity: Optional[Dict[str, Any]] = None
    unitPrice: Optional[Dict[str, Any]] = None
    net: Optional[Dict[str, Any]] = None

class Item(BaseModel):
    sequence: int
    careTeamSequence: List[int] = []
    diagnosisSequence: List[int] = []
    procedureSequence: List[int] = []
    informationSequence: List[int] = []
    productOrService: CodeableConcept
    modifier: List[CodeableConcept] = []
    servicedDate: Optional[str] = None
    servicedPeriod: Optional[Dict[str, str]] = None
    locationCodeableConcept: Optional[CodeableConcept] = None
    quantity: Optional[Dict[str, Any]] = None
    unitPrice: Optional[Dict[str, Any]] = None
    net: Optional[Dict[str, Any]] = None
    bodySite: Optional[CodeableConcept] = None
    detail: List[ItemDetail] = []

# Care Team
class CareTeam(BaseModel):
    sequence: int
    provider: Dict[str, str]
    role: Optional[CodeableConcept] = None
    qualification: Optional[CodeableConcept] = None

# Insurance
class Insurance(BaseModel):
    sequence: int
    focal: bool
    identifier: Optional[Dict[str, Any]] = None
    coverage: Dict[str, str]

# Supporting Info
class SupportingInfo(BaseModel):
    sequence: int
    category: CodeableConcept
    code: Optional[CodeableConcept] = None
    timingDate: Optional[str] = None
    timingPeriod: Optional[Dict[str, str]] = None
    valueBoolean: Optional[bool] = None
    valueString: Optional[str] = None
    valueQuantity: Optional[Dict[str, Any]] = None
    valueAttachment: Optional[Dict[str, Any]] = None
    valueReference: Optional[Dict[str, str]] = None

# Main Claim Resource
class Claim(BaseModel):
    resourceType: str = "Claim"
    id: Optional[str] = None
    identifier: List[Dict[str, Any]] = []
    status: str
    type: CodeableConcept
    subType: Optional[CodeableConcept] = None
    use: ClaimUse
    patient: Dict[str, str]
    billablePeriod: Optional[Dict[str, str]] = None
    created: str
    insurer: Optional[Dict[str, str]] = None
    provider: Dict[str, str]
    priority: CodeableConcept
    prescription: Optional[Dict[str, str]] = None
    originalPrescription: Optional[Dict[str, str]] = None
    payee: Optional[Dict[str, Any]] = None
    referral: Optional[Dict[str, str]] = None
    facility: Optional[Dict[str, str]] = None
    careTeam: List[CareTeam] = []
    supportingInfo: List[SupportingInfo] = []
    diagnosis: List[Diagnosis] = []
    procedure: List[ProcedureModel] = []
    insurance: List[Insurance] = []
    accident: Optional[Dict[str, Any]] = None
    item: List[Item] = []
    total: Optional[Dict[str, Any]] = None

# Bundle Entry
class BundleEntry(BaseModel):
    fullUrl: Optional[str] = None
    resource: Dict[str, Any]  # Can be Claim, Patient, Coverage, etc.

# Main Bundle (NPHIES Request)
class Bundle(BaseModel):
    resourceType: str = "Bundle"
    id: Optional[str] = None
    type: BundleType
    timestamp: Optional[str] = None
    entry: List[BundleEntry] = []

# Parsed Clinical Data (Internal Use)
class ParsedClinicalData(BaseModel):
    """Structured clinical data extracted from FHIR"""
    request_id: str
    patient_id: str
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    coverage_id: str
    insurer_id: Optional[str] = None
    provider_id: str
    
    # Clinical Information
    diagnoses: List[Dict[str, str]] = []  # [{code, display, type}]
    procedures: List[Dict[str, str]] = []  # [{code, display, date}]
    services: List[Dict[str, Any]] = []  # [{code, description, cost, quantity}]
    
    # Administrative
    service_date: Optional[str] = None
    total_cost: Optional[float] = None
    facility_type: Optional[str] = None
    
    # Supporting Documentation
    clinical_notes: List[str] = []
    attachments: List[str] = []
    
    # Metadata
    created_date: str
    priority: Optional[str] = None
    
    # Validators to handle int/str conversion
    @field_validator('coverage_id', 'created_date', mode='before')
    @classmethod
    def convert_to_string(cls, v):
        """Convert int to string if needed"""
        if isinstance(v, int):
            return str(v)
        return v
    
    @field_validator('service_date', mode='before')
    @classmethod
    def convert_service_date(cls, v):
        """Convert int to string for service_date"""
        if v is not None and isinstance(v, int):
            return str(v)
        return v
