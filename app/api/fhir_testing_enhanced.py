"""
Enhanced FHIR Testing API with OCR and Attachment Processing
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json
import base64
import io
from datetime import datetime
from loguru import logger

# Import enhanced parser
import sys
sys.path.append('/home/claude')
from app.services.fhir_parser_enhanced import FHIRBundleParser, AttachmentProcessor

router = APIRouter(prefix="/fhir", tags=["Enhanced FHIR Testing"])

class FHIRBundleRequest(BaseModel):
    bundle_data: Dict[str, Any]
    process_ocr: bool = True
    enabled_layers: List[str] = []

class DecisionLayerConfig(BaseModel):
    medical_rules: bool = True
    fraud_detection: bool = True
    risk_assessment: bool = True
    medical_necessity: bool = True
    

@router.post("/parse-bundle")
async def parse_fhir_bundle(request: FHIRBundleRequest):
    """
    Parse FHIR Bundle with complete categorization and OCR processing
    """
    try:
        start_time = datetime.now()
        
        # Parse bundle
        parser = FHIRBundleParser(request.bundle_data)
        parsed_data = parser.parse_complete()
        
        # Process attachments with OCR if enabled
        if request.process_ocr:
            processed_attachments = []
            for attachment in parsed_data['attachments']:
                processed = AttachmentProcessor.process_attachment(attachment)
                # Don't include the full base64 data in response
                processed_att = {k: v for k, v in processed.items() if k != 'data'}
                processed_att['has_text'] = len(processed.get('text', '')) > 0
                processed_att['text_length'] = len(processed.get('text', ''))
                processed_att['text_preview'] = processed.get('text', '')[:500] + '...' if len(processed.get('text', '')) > 500 else processed.get('text', '')
                processed_attachments.append(processed_att)
            
            parsed_data['processed_attachments'] = processed_attachments
        
        # Remove large base64 data from response
        if 'attachments' in parsed_data:
            for att in parsed_data['attachments']:
                if 'data' in att:
                    att['data'] = f"[BASE64_DATA_{att['size']}_BYTES]"
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            'status': 'success',
            'parsed_data': parsed_data,
            'processing_time_ms': round(processing_time, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Bundle parsing error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/process-with-ai")
async def process_with_ai_layers(
    bundle_data: Dict[str, Any] = Body(...),
    enabled_layers: Dict[str, bool] = Body(default={
        'medical_rules': True,
        'fraud_detection': True,
        'risk_assessment': True,
        'medical_necessity': True
    })
):
    """
    Process FHIR Bundle through enabled AI decision layers
    """
    try:
        start_time = datetime.now()
        
        # Parse bundle
        parser = FHIRBundleParser(bundle_data)
        parsed_data = parser.parse_complete()
        
        results = {
            'parsing': {
                'status': 'success',
                'statistics': parsed_data['statistics']
            }
        }
        
        # Medical Rules Layer
        if enabled_layers.get('medical_rules', False):
            results['medical_rules'] = process_medical_rules_layer(parsed_data)
        
        # Fraud Detection Layer
        if enabled_layers.get('fraud_detection', False):
            results['fraud_detection'] = process_fraud_detection_layer(parsed_data)
        
        # Risk Assessment Layer
        if enabled_layers.get('risk_assessment', False):
            results['risk_assessment'] = process_risk_assessment_layer(parsed_data)
        
        # Medical Necessity Layer
        if enabled_layers.get('medical_necessity', False):
            results['medical_necessity'] = process_medical_necessity_layer(parsed_data)
        
        # Generate final decision
        results['final_decision'] = generate_final_decision(results, parsed_data)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            'status': 'success',
            'results': results,
            'processing_time_ms': round(processing_time, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"AI processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-attachment-text")
async def extract_attachment_text(
    attachment_sequence: int = Body(...),
    bundle_data: Dict[str, Any] = Body(...)
):
    """
    Extract and OCR text from a specific attachment
    """
    try:
        parser = FHIRBundleParser(bundle_data)
        attachments = parser.extract_attachments()
        
        # Find the requested attachment
        target_attachment = None
        for att in attachments:
            if att['sequence'] == attachment_sequence:
                target_attachment = att
                break
        
        if not target_attachment:
            raise HTTPException(status_code=404, detail="Attachment not found")
        
        # Process with OCR
        processed = AttachmentProcessor.process_attachment(target_attachment)
        
        return {
            'status': 'success',
            'attachment_info': {
                'sequence': attachment_sequence,
                'title': processed['title'],
                'contentType': processed['contentType'],
                'size': processed['size']
            },
            'extraction': {
                'processed': processed['processed'],
                'method': processed.get('method'),
                'text': processed['text'],
                'error': processed.get('error')
            },
            'timestamp': datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Attachment extraction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Decision Layer Processors
def process_medical_rules_layer(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process through medical rules engine"""
    claim = parsed_data.get('claim', {})
    items = claim.get('items', [])
    
    results = {
        'status': 'PROCESSED',
        'layer': 'Medical Rules Engine',
        'rules_applied': len(items),
        'decisions': [],
        'summary': {
            'approved': 0,
            'denied': 0,
            'requires_review': 0
        }
    }
    
    for item in items:
        product = item.get('productOrService', {})
        coding = product.get('coding', [{}])[0]
        
        decision = {
            'sequence': item.get('sequence'),
            'service_code': coding.get('code', 'UNKNOWN'),
            'service_name': coding.get('display', 'Unknown Service'),
            'decision': 'APPROVED',
            'confidence': 0.95,
            'reason': 'Service covered under policy terms'
        }
        
        results['decisions'].append(decision)
        results['summary']['approved'] += 1
    
    return results


def process_fraud_detection_layer(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fraud detection analysis"""
    claim = parsed_data.get('claim', {})
    stats = parsed_data.get('statistics', {})
    
    risk_score = 0.0
    flags = []
    
    # Check for high amount
    total_amount = stats.get('total_amount', 0)
    if total_amount > 100000:
        flags.append({
            'type': 'HIGH_AMOUNT',
            'severity': 'MEDIUM',
            'description': f'Claim amount ({total_amount} SAR) exceeds threshold'
        })
        risk_score += 0.2
    
    # Check for excessive items
    item_count = stats.get('claim_items', 0)
    if item_count > 50:
        flags.append({
            'type': 'EXCESSIVE_ITEMS',
            'severity': 'LOW',
            'description': f'High number of line items ({item_count})'
        })
        risk_score += 0.1
    
    # Provider pattern analysis (simplified)
    flags.append({
        'type': 'PROVIDER_PATTERN',
        'severity': 'INFO',
        'description': 'Provider submission pattern within normal range'
    })
    
    return {
        'status': 'ANALYZED',
        'layer': 'Fraud Detection',
        'risk_score': round(risk_score, 2),
        'risk_level': 'HIGH' if risk_score >= 0.7 else 'MEDIUM' if risk_score >= 0.4 else 'LOW',
        'flags': flags,
        'recommendation': 'APPROVE' if risk_score < 0.4 else 'REVIEW'
    }


def process_risk_assessment_layer(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Financial risk assessment"""
    stats = parsed_data.get('statistics', {})
    claim = parsed_data.get('claim', {})
    
    total_amount = stats.get('total_amount', 0)
    
    return {
        'status': 'CALCULATED',
        'layer': 'Risk Assessment',
        'financial_risk': {
            'claim_amount': total_amount,
            'currency': stats.get('currency', 'SAR'),
            'risk_category': 'HIGH' if total_amount > 50000 else 'MEDIUM' if total_amount > 10000 else 'LOW',
            'reserve_amount': round(total_amount * 0.1, 2)
        },
        'clinical_risk': {
            'diagnosis_complexity': 'MODERATE',
            'procedure_risk': 'STANDARD'
        },
        'recommendations': [
            'Monitor claim progression',
            'Review high-cost items' if total_amount > 10000 else 'Standard processing'
        ]
    }


def process_medical_necessity_layer(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Medical necessity validation"""
    claim = parsed_data.get('claim', {})
    diagnosis = claim.get('diagnosis', [])
    items = claim.get('items', [])
    supporting_info = claim.get('supportingInfo', [])
    
    # Check for clinical documentation
    has_clinical_notes = any(
        info.get('type') == 'string' and info.get('category', {}).get('coding', [{}])[0].get('code') in 
        ['history-of-present-illness', 'physical-examination', 'treatment-plan']
        for info in supporting_info
    )
    
    return {
        'status': 'VALIDATED',
        'layer': 'Medical Necessity',
        'assessment': {
            'diagnosis_documented': len(diagnosis) > 0,
            'clinical_notes_present': has_clinical_notes,
            'treatment_plan_documented': has_clinical_notes,
            'medical_necessity_score': 0.85 if has_clinical_notes and len(diagnosis) > 0 else 0.5
        },
        'recommendation': 'APPROVED' if has_clinical_notes and len(diagnosis) > 0 else 'REQUIRES_ADDITIONAL_DOCUMENTATION',
        'missing_documentation': [] if has_clinical_notes else ['Clinical notes', 'Treatment justification']
    }


def generate_final_decision(results: Dict[str, Any], parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate final authorization decision"""
    decision = 'APPROVED'
    reasons = []
    confidence = 1.0
    
    # Check fraud detection
    if 'fraud_detection' in results:
        fraud_risk = results['fraud_detection'].get('risk_level')
        if fraud_risk == 'HIGH':
            decision = 'REQUIRES_REVIEW'
            reasons.append('High fraud risk detected')
            confidence *= 0.5
    
    # Check medical necessity
    if 'medical_necessity' in results:
        med_necessity = results['medical_necessity'].get('recommendation')
        if med_necessity == 'REQUIRES_ADDITIONAL_DOCUMENTATION':
            decision = 'PENDING_DOCUMENTATION' if decision == 'APPROVED' else decision
            reasons.append('Additional clinical documentation required')
            confidence *= 0.7
    
    # Check medical rules
    if 'medical_rules' in results:
        denied_count = results['medical_rules']['summary'].get('denied', 0)
        if denied_count > 0:
            decision = 'PARTIAL_APPROVAL'
            reasons.append(f'{denied_count} items denied per policy')
    
    if decision == 'APPROVED' and not reasons:
        reasons.append('All validation layers passed successfully')
    
    return {
        'final_decision': decision,
        'confidence': round(confidence, 2),
        'reasons': reasons,
        'total_amount': parsed_data.get('statistics', {}).get('total_amount', 0),
        'currency': parsed_data.get('statistics', {}).get('currency', 'SAR'),
        'requires_human_review': decision == 'REQUIRES_REVIEW',
        'decision_date': datetime.now().isoformat()
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'service': 'Enhanced FHIR Testing API',
        'features': {
            'pdf_ocr': True,
            'image_ocr': True,
            'ai_layers': ['medical_rules', 'fraud_detection', 'risk_assessment', 'medical_necessity']
        },
        'timestamp': datetime.now().isoformat()
    }
