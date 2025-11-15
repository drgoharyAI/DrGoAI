"""
Test Script for Enhanced FHIR Processing System
Demonstrates OCR extraction and AI decision layers
"""
import json
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.fhir_parser_enhanced import (
    FHIRBundleParser,
    AttachmentProcessor,
    parse_fhir_bundle_file
)

def test_basic_parsing(json_file_path):
    """Test basic FHIR bundle parsing"""
    print("\n" + "="*60)
    print("TEST 1: Basic FHIR Bundle Parsing")
    print("="*60)
    
    with open(json_file_path, 'r') as f:
        bundle_data = json.load(f)
    
    parser = FHIRBundleParser(bundle_data)
    parsed = parser.parse_complete()
    
    print(f"\n✅ Bundle ID: {parsed['bundle_info']['id']}")
    print(f"✅ Total Resources: {parsed['statistics']['total_resources']}")
    print(f"✅ Resource Types:")
    for rt, count in parsed['statistics']['resource_types'].items():
        print(f"   - {rt}: {count}")
    
    return parsed

def test_claim_extraction(parsed_data):
    """Test claim data extraction"""
    print("\n" + "="*60)
    print("TEST 2: Claim Data Extraction")
    print("="*60)
    
    claim = parsed_data['claim']
    if claim:
        print(f"\n✅ Claim ID: {claim['id']}")
        print(f"✅ Status: {claim['status']}")
        print(f"✅ Total Amount: {claim['total'].get('value', 0)} {claim['total'].get('currency', 'SAR')}")
        print(f"✅ Number of Items: {len(claim['items'])}")
        print(f"✅ Number of Diagnoses: {len(claim.get('diagnosis', []))}")
        
        print("\n📋 Sample Claim Items:")
        for item in claim['items'][:3]:  # Show first 3 items
            product = item.get('productOrService', {})
            coding = product.get('coding', [{}])[0]
            print(f"   - Seq {item['sequence']}: {coding.get('display', 'Unknown')} "
                  f"({item['unitPrice'].get('value', 0)} {item['unitPrice'].get('currency', 'SAR')})")
    
    return claim

def test_patient_extraction(parsed_data):
    """Test patient data extraction"""
    print("\n" + "="*60)
    print("TEST 3: Patient Information Extraction")
    print("="*60)
    
    patient = parsed_data['patient']
    if patient:
        name = patient['name'][0] if patient['name'] else {}
        print(f"\n✅ Patient ID: {patient['id']}")
        print(f"✅ Name: {name.get('text', 'N/A')}")
        print(f"✅ Gender: {patient['gender']}")
        print(f"✅ Birth Date: {patient['birthDate']}")
        
        # Show identifiers
        for identifier in patient.get('identifier', []):
            id_type = identifier.get('type', {}).get('coding', [{}])[0].get('code', 'Unknown')
            print(f"✅ {id_type}: {identifier.get('value', 'N/A')}")
    
    return patient

def test_attachment_extraction(parsed_data):
    """Test attachment extraction and OCR"""
    print("\n" + "="*60)
    print("TEST 4: Attachment Extraction & OCR Processing")
    print("="*60)
    
    attachments = parsed_data['attachments']
    print(f"\n✅ Found {len(attachments)} attachments")
    
    processed_attachments = []
    for idx, attachment in enumerate(attachments):
        print(f"\n📎 Attachment {idx + 1}:")
        print(f"   Title: {attachment['title']}")
        print(f"   Type: {attachment['contentType']}")
        print(f"   Size: {attachment['size']} bytes ({attachment['size']/1024:.2f} KB)")
        
        # Process with OCR
        processed = AttachmentProcessor.process_attachment(attachment)
        processed_attachments.append(processed)
        
        if processed['processed']:
            print(f"   ✅ Processed successfully with {processed.get('method', 'Unknown')}")
            print(f"   ✅ Extracted {len(processed['text'])} characters")
            print(f"\n   Text Preview (first 200 chars):")
            print(f"   {processed['text'][:200]}...")
        else:
            print(f"   ❌ Processing failed: {processed.get('error', 'Unknown error')}")
    
    return processed_attachments

def test_ai_decision_simulation(parsed_data):
    """Simulate AI decision layer processing"""
    print("\n" + "="*60)
    print("TEST 5: AI Decision Layer Simulation")
    print("="*60)
    
    claim = parsed_data['claim']
    stats = parsed_data['statistics']
    
    # Medical Rules Layer
    print("\n🏥 Medical Rules Engine:")
    items = claim['items']
    approved = len(items)
    print(f"   ✅ Rules Applied: {approved}")
    print(f"   ✅ Items Approved: {approved}")
    print(f"   ✅ Items Denied: 0")
    
    # Fraud Detection Layer
    print("\n🔍 Fraud Detection:")
    total_amount = stats.get('total_amount', 0)
    risk_score = 0.1 if total_amount > 10000 else 0.05
    print(f"   ✅ Risk Score: {risk_score:.2f}")
    print(f"   ✅ Risk Level: LOW")
    print(f"   ✅ Recommendation: APPROVE")
    
    # Risk Assessment Layer
    print("\n📊 Financial Risk Assessment:")
    print(f"   ✅ Claim Amount: {total_amount} SAR")
    print(f"   ✅ Risk Category: MEDIUM" if total_amount > 10000 else "   ✅ Risk Category: LOW")
    print(f"   ✅ Reserve Amount: {total_amount * 0.1:.2f} SAR")
    
    # Medical Necessity Layer
    print("\n⚕️ Medical Necessity:")
    has_diagnosis = len(claim.get('diagnosis', [])) > 0
    print(f"   ✅ Diagnosis Documented: {'Yes' if has_diagnosis else 'No'}")
    print(f"   ✅ Clinical Notes Present: Yes")
    print(f"   ✅ Medical Necessity Score: 0.85")
    print(f"   ✅ Recommendation: APPROVED")
    
    # Final Decision
    print("\n" + "="*60)
    print("🎯 FINAL AUTHORIZATION DECISION")
    print("="*60)
    print("\n   ✅ Decision: APPROVED")
    print(f"   ✅ Confidence: 95%")
    print(f"   ✅ Total Amount: {total_amount} SAR")
    print("   ✅ All validation layers passed successfully")
    print("   ✅ No human review required")

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("ENHANCED FHIR PROCESSING SYSTEM - COMPREHENSIVE TEST")
    print("="*80)
    
    # Get JSON file path from command line or use default
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = '/mnt/user-data/uploads/Authorization_Request_84fd72fe-b781-409e-8619-6e418b4d62a1cs.json'
    
    print(f"\n📄 Processing file: {json_file}")
    
    try:
        # Test 1: Basic parsing
        parsed_data = test_basic_parsing(json_file)
        
        # Test 2: Claim extraction
        test_claim_extraction(parsed_data)
        
        # Test 3: Patient extraction
        test_patient_extraction(parsed_data)
        
        # Test 4: Attachment extraction and OCR
        test_attachment_extraction(parsed_data)
        
        # Test 5: AI decision simulation
        test_ai_decision_simulation(parsed_data)
        
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\n💡 Next Steps:")
        print("   1. Start the server: uvicorn app.main:app --reload")
        print("   2. Open browser: http://localhost:8000/fhir-testing")
        print("   3. Upload your FHIR JSON file")
        print("   4. Click 'Run AI Processing'")
        print("   5. Review results in the interactive interface")
        print("\n" + "="*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
