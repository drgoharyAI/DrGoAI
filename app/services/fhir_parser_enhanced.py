"""
Enhanced FHIR Parser with OCR Support
Extracts and processes embedded attachments from FHIR Bundles
"""
import base64
import io
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class FHIRBundleParser:
    """Parse and categorize FHIR Bundle resources"""
    
    def __init__(self, bundle_data: Dict[str, Any]):
        self.bundle = bundle_data
        self.entries = bundle_data.get('entry', [])
        
    def parse_complete(self) -> Dict[str, Any]:
        """Complete parsing with categorization"""
        return {
            'bundle_info': self.get_bundle_info(),
            'message_header': self.extract_message_header(),
            'claim': self.extract_claim(),
            'patient': self.extract_patient(),
            'coverage': self.extract_coverage(),
            'organizations': self.extract_organizations(),
            'encounter': self.extract_encounter(),
            'practitioners': self.extract_practitioners(),
            'attachments': self.extract_attachments(),
            'statistics': self.get_statistics()
        }
    
    def get_bundle_info(self) -> Dict[str, Any]:
        """Extract bundle metadata"""
        return {
            'id': self.bundle.get('id'),
            'type': self.bundle.get('type'),
            'timestamp': self.bundle.get('timestamp'),
            'total_entries': len(self.entries)
        }
    
    def extract_message_header(self) -> Optional[Dict[str, Any]]:
        """Extract MessageHeader resource"""
        for entry in self.entries:
            resource = entry.get('resource', {})
            if resource.get('resourceType') == 'MessageHeader':
                return {
                    'id': resource.get('id'),
                    'event': resource.get('eventCoding', {}),
                    'destination': resource.get('destination', []),
                    'sender': resource.get('sender', {}),
                    'focus': resource.get('focus', [])
                }
        return None
    
    def extract_claim(self) -> Optional[Dict[str, Any]]:
        """Extract and parse Claim resource"""
        for entry in self.entries:
            resource = entry.get('resource', {})
            if resource.get('resourceType') == 'Claim':
                return {
                    'id': resource.get('id'),
                    'status': resource.get('status'),
                    'type': resource.get('type', {}),
                    'subType': resource.get('subType', {}),
                    'use': resource.get('use'),
                    'patient': resource.get('patient', {}),
                    'created': resource.get('created'),
                    'insurer': resource.get('insurer', {}),
                    'provider': resource.get('provider', {}),
                    'priority': resource.get('priority', {}),
                    'careTeam': resource.get('careTeam', []),
                    'supportingInfo': self.parse_supporting_info(resource.get('supportingInfo', [])),
                    'diagnosis': resource.get('diagnosis', []),
                    'items': self.parse_claim_items(resource.get('item', [])),
                    'total': resource.get('total', {}),
                    'related': resource.get('related', [])
                }
        return None
    
    def parse_supporting_info(self, supporting_info: List[Dict]) -> List[Dict[str, Any]]:
        """Parse supporting information with attachment detection"""
        parsed_info = []
        for info in supporting_info:
            parsed = {
                'sequence': info.get('sequence'),
                'category': info.get('category', {}),
                'has_attachment': 'valueAttachment' in info
            }
            
            # Add value based on type
            if 'valueString' in info:
                parsed['type'] = 'string'
                parsed['value'] = info['valueString']
            elif 'valueQuantity' in info:
                parsed['type'] = 'quantity'
                parsed['value'] = info['valueQuantity']
            elif 'valueAttachment' in info:
                parsed['type'] = 'attachment'
                attachment = info['valueAttachment']
                parsed['attachment_info'] = {
                    'contentType': attachment.get('contentType'),
                    'title': attachment.get('title'),
                    'size': len(attachment.get('data', '')),
                    'creation': attachment.get('creation')
                }
            elif 'code' in info:
                parsed['type'] = 'code'
                parsed['code'] = info['code']
            
            parsed_info.append(parsed)
        
        return parsed_info
    
    def parse_claim_items(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """Parse claim items with pricing"""
        parsed_items = []
        for item in items:
            parsed = {
                'sequence': item.get('sequence'),
                'productOrService': item.get('productOrService', {}),
                'servicedDate': item.get('servicedDate'),
                'quantity': item.get('quantity', {}),
                'unitPrice': item.get('unitPrice', {}),
                'net': item.get('net', {}),
                'careTeamSequence': item.get('careTeamSequence', []),
                'diagnosisSequence': item.get('diagnosisSequence', [])
            }
            parsed_items.append(parsed)
        return parsed_items
    
    def extract_patient(self) -> Optional[Dict[str, Any]]:
        """Extract Patient resource"""
        for entry in self.entries:
            resource = entry.get('resource', {})
            if resource.get('resourceType') == 'Patient':
                return {
                    'id': resource.get('id'),
                    'identifier': resource.get('identifier', []),
                    'name': resource.get('name', []),
                    'telecom': resource.get('telecom', []),
                    'gender': resource.get('gender'),
                    'birthDate': resource.get('birthDate'),
                    'maritalStatus': resource.get('maritalStatus', {})
                }
        return None
    
    def extract_coverage(self) -> Optional[Dict[str, Any]]:
        """Extract Coverage resource"""
        for entry in self.entries:
            resource = entry.get('resource', {})
            if resource.get('resourceType') == 'Coverage':
                return {
                    'id': resource.get('id'),
                    'identifier': resource.get('identifier', []),
                    'status': resource.get('status'),
                    'type': resource.get('type', {}),
                    'beneficiary': resource.get('beneficiary', {}),
                    'payor': resource.get('payor', []),
                    'class': resource.get('class', [])
                }
        return None
    
    def extract_organizations(self) -> List[Dict[str, Any]]:
        """Extract all Organization resources"""
        organizations = []
        for entry in self.entries:
            resource = entry.get('resource', {})
            if resource.get('resourceType') == 'Organization':
                organizations.append({
                    'id': resource.get('id'),
                    'identifier': resource.get('identifier', []),
                    'name': resource.get('name'),
                    'type': resource.get('type', []),
                    'active': resource.get('active')
                })
        return organizations
    
    def extract_encounter(self) -> Optional[Dict[str, Any]]:
        """Extract Encounter resource"""
        for entry in self.entries:
            resource = entry.get('resource', {})
            if resource.get('resourceType') == 'Encounter':
                return {
                    'id': resource.get('id'),
                    'identifier': resource.get('identifier', []),
                    'status': resource.get('status'),
                    'class': resource.get('class', {}),
                    'subject': resource.get('subject', {}),
                    'period': resource.get('period', {}),
                    'serviceProvider': resource.get('serviceProvider', {})
                }
        return None
    
    def extract_practitioners(self) -> List[Dict[str, Any]]:
        """Extract all Practitioner resources"""
        practitioners = []
        for entry in self.entries:
            resource = entry.get('resource', {})
            if resource.get('resourceType') == 'Practitioner':
                practitioners.append({
                    'id': resource.get('id'),
                    'identifier': resource.get('identifier', []),
                    'name': resource.get('name', []),
                    'gender': resource.get('gender'),
                    'active': resource.get('active')
                })
        return practitioners
    
    def extract_attachments(self) -> List[Dict[str, Any]]:
        """Extract all embedded attachments"""
        attachments = []
        for entry in self.entries:
            resource = entry.get('resource', {})
            if resource.get('resourceType') == 'Claim':
                for info in resource.get('supportingInfo', []):
                    if 'valueAttachment' in info:
                        attachment = info['valueAttachment']
                        attachments.append({
                            'sequence': info.get('sequence'),
                            'category': info.get('category', {}),
                            'contentType': attachment.get('contentType'),
                            'title': attachment.get('title', 'Untitled'),
                            'size': len(attachment.get('data', '')),
                            'data': attachment.get('data', ''),
                            'creation': attachment.get('creation')
                        })
        return attachments
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate bundle statistics"""
        claim = self.extract_claim()
        attachments = self.extract_attachments()
        
        stats = {
            'total_resources': len(self.entries),
            'resource_types': {},
            'total_attachments': len(attachments),
            'attachment_size_mb': sum(att['size'] for att in attachments) / 1024 / 1024
        }
        
        for entry in self.entries:
            rt = entry.get('resource', {}).get('resourceType', 'Unknown')
            stats['resource_types'][rt] = stats['resource_types'].get(rt, 0) + 1
        
        if claim:
            stats['claim_items'] = len(claim.get('items', []))
            total_amount = claim.get('total', {}).get('value', 0)
            stats['total_amount'] = total_amount
            stats['currency'] = claim.get('total', {}).get('currency', 'SAR')
        
        return stats


class AttachmentProcessor:
    """Process and OCR attachments"""
    
    @staticmethod
    def extract_pdf_text(base64_data: str) -> Dict[str, Any]:
        """Extract text from PDF"""
        if not PDF_AVAILABLE:
            return {
                'success': False,
                'error': 'PyPDF2 not available',
                'text': ''
            }
        
        try:
            # Decode base64
            pdf_data = base64.b64decode(base64_data)
            pdf_file = io.BytesIO(pdf_data)
            
            # Extract text
            reader = PyPDF2.PdfReader(pdf_file)
            text = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
            
            return {
                'success': True,
                'pages': len(reader.pages),
                'text': '\n\n'.join(text),
                'method': 'PDF text extraction'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }
    
    @staticmethod
    def extract_image_text(base64_data: str) -> Dict[str, Any]:
        """Extract text from image using OCR"""
        if not TESSERACT_AVAILABLE:
            return {
                'success': False,
                'error': 'Tesseract OCR not available',
                'text': ''
            }
        
        try:
            # Decode base64
            image_data = base64.b64decode(base64_data)
            image = Image.open(io.BytesIO(image_data))
            
            # Perform OCR
            text = pytesseract.image_to_string(image)
            
            return {
                'success': True,
                'size': image.size,
                'format': image.format,
                'text': text,
                'method': 'Tesseract OCR'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }
    
    @staticmethod
    def process_attachment(attachment: Dict[str, Any]) -> Dict[str, Any]:
        """Process attachment based on content type"""
        content_type = attachment.get('contentType', '')
        data = attachment.get('data', '')
        
        result = {
            'title': attachment.get('title'),
            'contentType': content_type,
            'size': attachment.get('size'),
            'processed': False,
            'text': '',
            'error': None
        }
        
        if 'pdf' in content_type.lower():
            extraction = AttachmentProcessor.extract_pdf_text(data)
            result['processed'] = extraction['success']
            result['text'] = extraction.get('text', '')
            result['error'] = extraction.get('error')
            result['method'] = extraction.get('method')
            if extraction['success']:
                result['pages'] = extraction.get('pages')
        
        elif any(img_type in content_type.lower() for img_type in ['image', 'png', 'jpg', 'jpeg']):
            extraction = AttachmentProcessor.extract_image_text(data)
            result['processed'] = extraction['success']
            result['text'] = extraction.get('text', '')
            result['error'] = extraction.get('error')
            result['method'] = extraction.get('method')
            if extraction['success']:
                result['image_size'] = extraction.get('size')
        
        return result


def parse_fhir_bundle_file(file_path: str) -> Dict[str, Any]:
    """Parse FHIR bundle from file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        bundle_data = json.load(f)
    
    parser = FHIRBundleParser(bundle_data)
    parsed_data = parser.parse_complete()
    
    # Process attachments
    processed_attachments = []
    for attachment in parsed_data['attachments']:
        processed = AttachmentProcessor.process_attachment(attachment)
        processed_attachments.append(processed)
    
    parsed_data['processed_attachments'] = processed_attachments
    
    return parsed_data


if __name__ == '__main__':
    # Example usage
    result = parse_fhir_bundle_file('/mnt/user-data/uploads/Authorization_Request_84fd72fe-b781-409e-8619-6e418b4d62a1cs.json')
    print(json.dumps({
        'bundle_id': result['bundle_info']['id'],
        'total_resources': result['statistics']['total_resources'],
        'attachments': result['statistics']['total_attachments'],
        'total_amount': result['statistics'].get('total_amount', 0)
    }, indent=2))
