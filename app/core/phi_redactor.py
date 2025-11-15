"""
PHI Redaction System
Protects Protected Health Information in logs and error messages
"""
import re
from typing import Any, Dict, List
import hashlib

class PHIRedactor:
    """Redact Protected Health Information from logs and error messages"""
    
    @staticmethod
    def redact_patient_id(text: str) -> str:
        """Redact patient identifiers"""
        text = re.sub(r'(patient|mrn|member)[-_]?\d+', '[PATIENT_ID]', text, flags=re.IGNORECASE)
        text = re.sub(r'\b\d{10,}\b', '[ID_NUMBER]', text)
        return text
    
    @staticmethod
    def redact_diagnosis_codes(text: str) -> str:
        """Redact ICD-10 codes"""
        return re.sub(r'\b[A-Z]\d{2}\.?\d{0,2}\b', '[DIAGNOSIS_CODE]', text)
    
    @staticmethod
    def redact_phone_numbers(text: str) -> str:
        """Redact phone numbers"""
        return re.sub(
            r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            '[PHONE]',
            text
        )
    
    @staticmethod
    def redact_email(text: str) -> str:
        """Redact email addresses"""
        return re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    @staticmethod
    def redact_arabic_names(text: str) -> str:
        """Redact Arabic names (basic pattern)"""
        return re.sub(r'[\u0600-\u06FF]{2,}', '[NAME]', text)
    
    @staticmethod
    def redact_structured_data(data: Any) -> Any:
        """Recursively redact PHI from structured data"""
        if isinstance(data, dict):
            redacted = {}
            phi_fields = {
                'patient', 'name', 'given', 'family', 'telecom', 'phone', 'email',
                'address', 'birthDate', 'identifier', 'mrn', 'member_id'
            }
            
            for key, value in data.items():
                key_lower = key.lower()
                if any(phi_field in key_lower for phi_field in phi_fields):
                    if isinstance(value, str):
                        redacted[key] = '[REDACTED]'
                    elif isinstance(value, (list, dict)):
                        redacted[key] = '[REDACTED_OBJECT]'
                    else:
                        redacted[key] = '[REDACTED]'
                else:
                    redacted[key] = PHIRedactor.redact_structured_data(value)
            return redacted
        
        elif isinstance(data, list):
            return [PHIRedactor.redact_structured_data(item) for item in data]
        
        elif isinstance(data, str):
            text = data
            text = PHIRedactor.redact_patient_id(text)
            text = PHIRedactor.redact_diagnosis_codes(text)
            text = PHIRedactor.redact_phone_numbers(text)
            text = PHIRedactor.redact_email(text)
            text = PHIRedactor.redact_arabic_names(text)
            return text
        
        else:
            return data
    
    @staticmethod
    def hash_identifier(identifier: str) -> str:
        """Create a consistent hash of an identifier for tracking without exposing PHI"""
        return hashlib.sha256(identifier.encode()).hexdigest()[:12]
    
    @staticmethod
    def redact_log_message(message: str, redact_enabled: bool = True) -> str:
        """Main method to redact a log message"""
        if not redact_enabled:
            return message
        
        message = PHIRedactor.redact_patient_id(message)
        message = PHIRedactor.redact_diagnosis_codes(message)
        message = PHIRedactor.redact_phone_numbers(message)
        message = PHIRedactor.redact_email(message)
        message = PHIRedactor.redact_arabic_names(message)
        
        return message

# Global instance
phi_redactor = PHIRedactor()
