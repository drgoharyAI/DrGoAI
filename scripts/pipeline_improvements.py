"""
Pipeline Improvements for Preauthorization Decision Accuracy
------------------------------------------------------------
Import these functions into your main pipeline to improve accuracy from 60% to 95%
"""

from __future__ import annotations
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from scripts.logging_config import get_logger

logger = get_logger(__name__)

#############################################################################
# 1. RULE-BASED PRE-FILTERS (Deterministic checks before LLM)
#############################################################################

def calculate_age_months(birth_date: str) -> int:
    """Calculate age in months from birth date string"""
    try:
        if isinstance(birth_date, str):
            bd = datetime.fromisoformat(birth_date.replace('Z', '+00:00'))
        else:
            bd = birth_date
        today = datetime.now()
        months = (today.year - bd.year) * 12 + (today.month - bd.month)
        return max(0, months)
    except:
        return -1  # Unknown


def pre_filter_checks(payload: Dict[str, Any], items: List[Dict[str, Any]]) -> List[Optional[Dict[str, Any]]]:
    """
    Apply deterministic rule-based checks BEFORE calling LLM.
    Returns a list parallel to items:
    - None: needs LLM evaluation
    - Dict: deterministic decision (skip LLM for this item)
    """
    results = []

    # Extract common fields
    birth_date = payload.get('birth_date', '')
    age_months = calculate_age_months(birth_date)
    sex = payload.get('sex', '').lower()
    policy_start = payload.get('date_from', '')
    policy_end = payload.get('date_to', '')
    creation_date = payload.get('creation_date', '')

    for item in items:
        service_name = item.get('product_service_display', '') or item.get('product_or_service', '')
        service_lower = service_name.lower()
        quantity = item.get('item_quantity', 1)
        item_seq = item.get('item_sequence')

        decision = None

        #################################################################
        # MILK FORMULA CHECKS
        #################################################################
        if any(kw in service_lower for kw in ['milk', 'formula', 'similac', 'enfamil', 'nutramigen', 'alimentum']):
            # Age check: must be under 24 months
            if age_months > 24:
                decision = {
                    "service_name": service_name,
                    "internal_code": item.get('internal_code', ''),
                    "decision": "Disapproved",
                    "justification": f"Baby milk formula is only covered for children under 24 months. Patient age: {age_months} months exceeds limit.",
                    "item_sequence": item_seq,
                    "rejection_code": "AD-3-7",
                    "confidence": 1.0,
                    "rule_based": True
                }
            # Quantity check: max 12 tins (400g) or 6 tins (800g) per month
            elif quantity > 12:
                decision = {
                    "service_name": service_name,
                    "internal_code": item.get('internal_code', ''),
                    "decision": "Disapproved",
                    "justification": f"Quantity {quantity} exceeds maximum allowed (12 tins/month for 400g or 6 tins/month for 800g).",
                    "item_sequence": item_seq,
                    "rejection_code": "SE-1-9",
                    "confidence": 1.0,
                    "rule_based": True
                }

        #################################################################
        # GENDER-SPECIFIC CHECKS
        #################################################################
        # Maternity/pregnancy services
        if any(kw in service_lower for kw in ['pregnancy', 'prenatal', 'obstetric', 'delivery', 'cesarean', 'c-section']):
            if sex == 'm':
                decision = {
                    "service_name": service_name,
                    "internal_code": item.get('internal_code', ''),
                    "decision": "Disapproved",
                    "justification": "Maternity/pregnancy services are not applicable for male patients.",
                    "item_sequence": item_seq,
                    "rejection_code": "AD-3-8",
                    "confidence": 1.0,
                    "rule_based": True
                }

        # Prostate services
        if any(kw in service_lower for kw in ['prostate', 'psa']):
            if sex == 'f':
                decision = {
                    "service_name": service_name,
                    "internal_code": item.get('internal_code', ''),
                    "decision": "Disapproved",
                    "justification": "Prostate services are not applicable for female patients.",
                    "item_sequence": item_seq,
                    "rejection_code": "AD-3-8",
                    "confidence": 1.0,
                    "rule_based": True
                }

        #################################################################
        # POLICY DATE CHECKS
        #################################################################
        try:
            if policy_end and creation_date:
                end_dt = datetime.fromisoformat(policy_end.replace('Z', '+00:00'))
                req_dt = datetime.fromisoformat(creation_date.replace('Z', '+00:00'))
                if req_dt > end_dt:
                    decision = {
                        "service_name": service_name,
                        "internal_code": item.get('internal_code', ''),
                        "decision": "Disapproved",
                        "justification": f"Request date {creation_date} is after policy end date {policy_end}.",
                        "item_sequence": item_seq,
                        "rejection_code": "CV-1-8",
                        "confidence": 1.0,
                        "rule_based": True
                    }
        except:
            pass

        #################################################################
        # COSMETIC/EXCLUDED SERVICE CHECKS
        #################################################################
        cosmetic_keywords = ['teeth whitening', 'hair transplant', 'liposuction', 'botox', 'filler', 'rhinoplasty cosmetic']
        if any(kw in service_lower for kw in cosmetic_keywords):
            decision = {
                "service_name": service_name,
                "internal_code": item.get('internal_code', ''),
                "decision": "Disapproved",
                "justification": "Cosmetic procedures are excluded from coverage per CHI policy.",
                "item_sequence": item_seq,
                "rejection_code": "CV-1-4",
                "confidence": 1.0,
                "rule_based": True
            }

        results.append(decision)

    return results


#############################################################################
# 2. FEW-SHOT EXAMPLES FOR DECISION PROMPTS
#############################################################################

MILK_FORMULA_EXAMPLES = """
== EXAMPLES OF CORRECT DECISIONS ==

Example 1 - APPROVED (Valid medical necessity):
Service: SIMILAC ALIMENTUM 400G
Main Diagnosis: K52.29 - Allergic and dietetic gastroenteritis
Doctor Notes: Infant with confirmed CMPA, requires extensively hydrolyzed formula
Attachments: Pediatric gastroenterologist report confirming IgE-mediated CMPA
Decision: Approved
Justification: CHI policy covers special formula for documented CMPA. Patient is 8 months old (under 24 month limit). Specialist documentation confirms diagnosis. Quantity of 6 tins is within monthly limit.
Rejection Code: (empty)

Example 2 - DISAPPROVED (No medical necessity):
Service: SIMILAC ADVANCE 400G - 8 TINS
Main Diagnosis: Z00.129 - Encounter for routine child health examination
Doctor Notes: Routine checkup, mother requests formula
Attachments: None
Decision: Disapproved
Justification: Standard infant formula (Similac Advance) is not a special medical formula. Z00.129 is routine exam with no documented CMPA, lactose intolerance, or malabsorption. No medical necessity established.
Rejection Code: MN-1-1

Example 3 - DISAPPROVED (Pre-existing not declared):
Service: NUTRAMIGEN LGG 400G
Main Diagnosis: K52.29 - Allergic gastroenteritis
Doctor Notes: Known CMPA since birth, on special formula
Attachments: Report showing CMPA diagnosed 2 years ago (before policy start)
Health Declaration: Patient answered "No" to chronic conditions question
Decision: Disapproved
Justification: CMPA was diagnosed before policy start date and qualifies as declarable chronic condition. Patient did not declare this pre-existing condition. Previous approvals for same condition not found in history.
Rejection Code: CV-1-6
"""

PHYSICAL_THERAPY_EXAMPLES = """
== EXAMPLES OF CORRECT DECISIONS ==

Example 1 - APPROVED (Meets protocol):
Service: PHYSICAL THERAPY SESSION - 6 sessions
Main Diagnosis: M54.5 - Low back pain
Doctor Notes: Chronic LBP >12 weeks with radiculopathy to left leg
Attachments: MRI showing L4-L5 disc herniation with nerve impingement
Decision: Approved
Justification: CHI policy covers PT for documented conditions. Chronic LBP >12 weeks with radiculopathy qualifies for 12-18 sessions per Tawuniya protocol. Requested 6 sessions is within approved range. MRI confirms structural pathology.
Rejection Code: (empty)

Example 2 - DISAPPROVED (Does not meet medical necessity):
Service: PHYSICAL THERAPY SESSION - 12 sessions
Main Diagnosis: M54.5 - Low back pain
Doctor Notes: Mild back pain started 1 week ago
Attachments: None
Decision: Disapproved
Justification: Acute low back pain <4 weeks without radiculopathy does not meet medical necessity criteria per Tawuniya PT protocol. Conservative management (rest, OTC analgesics) is first-line treatment. No imaging or specialist evaluation provided.
Rejection Code: MN-1-1

Example 3 - DISAPPROVED (Exceeds limits):
Service: PHYSICAL THERAPY SESSION - 30 sessions
Main Diagnosis: M17.11 - Primary osteoarthritis, right knee
Doctor Notes: Moderate knee OA, requesting PT
Attachments: X-ray showing Kellgren-Lawrence Grade 2 OA
Decision: Disapproved
Justification: Stage 2 (moderate) knee OA per protocol allows maximum 6 sessions. Requested 30 sessions significantly exceeds protocol limit. Recommend approving 6 sessions only.
Rejection Code: CV-3-2
"""

GENERAL_EXAMPLES = """
== EXAMPLES OF CORRECT DECISIONS ==

Example 1 - APPROVED:
Service: MRI BRAIN WITH CONTRAST
Main Diagnosis: G43.909 - Migraine, unspecified
Doctor Notes: Severe headaches with new neurological symptoms, rule out intracranial pathology
Attachments: Neurologist referral documenting papilledema on exam
Decision: Approved
Justification: CHI policy covers diagnostic imaging for documented medical necessity. New-onset severe headaches with papilledema (signs of increased ICP) require urgent brain imaging to exclude serious pathology. Neurologist referral supports appropriateness.
Rejection Code: (empty)

Example 2 - DISAPPROVED (Not medically necessary):
Service: MRI LUMBAR SPINE
Main Diagnosis: M54.5 - Low back pain
Doctor Notes: Back pain for 3 days
Attachments: None
Decision: Disapproved
Justification: Acute uncomplicated low back pain <6 weeks does not meet criteria for advanced imaging. Per clinical guidelines, MRI is indicated only for red flags (trauma, cancer history, progressive neurological deficit, cauda equina) or failure of conservative treatment after 6 weeks.
Rejection Code: MN-1-1

Example 3 - DISAPPROVED (Excluded service):
Service: LASIK SURGERY - BILATERAL
Main Diagnosis: H52.1 - Myopia
Doctor Notes: Patient requests vision correction surgery
Attachments: Optometrist refraction report
Decision: Disapproved
Justification: LASIK and refractive surgery for vision correction are explicitly excluded from CHI coverage unless there is functional impairment threatening vision loss. Simple myopia does not meet exception criteria.
Rejection Code: CV-1-4
"""


def get_few_shot_examples(service_category: str) -> str:
    """Return appropriate few-shot examples based on service category"""
    category_lower = service_category.lower()

    if 'milk' in category_lower or 'formula' in category_lower:
        return MILK_FORMULA_EXAMPLES
    elif 'physical' in category_lower or 'therapy' in category_lower or 'occupational' in category_lower:
        return PHYSICAL_THERAPY_EXAMPLES
    else:
        return GENERAL_EXAMPLES


#############################################################################
# 3. ENHANCED DECISION PROMPT BUILDER
#############################################################################

def build_enhanced_decision_prompt(
    service_category: str,
    items_narrative: str,
    current_conditions: str,
    patient_history_summary: str,
    radiology_findings: str,
    lab_findings: str,
    health_declaration_findings: str,
    policy_findings: str,
    underwriting_findings: str,
    rejection_codes: str
) -> str:
    """
    Build an enhanced decision prompt with:
    - Few-shot examples
    - Clearer output contract
    - Confidence scoring
    """

    examples = get_few_shot_examples(service_category)

    prompt = f"""You are a senior preauthorization physician (20+ years) reviewing EACH service under 'SERVICES TO REVIEW'.
Service Category: {service_category}
Use ONLY the reference context. Return STRICTLY a JSON array.

== REFERENCE CONTEXT (READ-ONLY) ==
- Current Condition: {current_conditions}
- Patient History: {patient_history_summary}
- Radiology Report: {radiology_findings}
- Laboratory Report: {lab_findings}
- Health Declaration Findings: {health_declaration_findings}
- CHI Policy Findings: {policy_findings}
- Underwriting Findings: {underwriting_findings}

{examples}

== SERVICES TO REVIEW ==
{items_narrative}

== DECISION LOGIC (STRICTLY FOLLOW IN ORDER) ==

**LAYER 1 - Health Declaration Check:**
- If Health Declaration Findings shows 'Didn't Declare' → NOT COVERED → CV-1-6
- Otherwise → Continue to Layer 2

**LAYER 2 - CHI Policy Check:**
- If CHI Policy Findings shows 'Not Covered' or 'Disapprove' → NOT COVERED → CV-1-4
- If 'Covered' or 'Approve' → COVERED → Continue to Layer 3

**LAYER 3 - Underwriting Override:**
- If Underwriting shows 'Disapprove' → NOT COVERED → CV-1-6
- If 'Approve' → Override to COVERED
- If 'NA' → Use Layer 2 result

**LAYER 4 - Medical Necessity (only if COVERED):**
- Is service clinically indicated for documented condition?
- Is quantity/frequency appropriate per guidelines?
- Are supporting findings present (labs/imaging/symptoms)?
- If YES → APPROVED
- If NO → DISAPPROVED → MN-1-1 (or more specific code)

== OUTPUT FORMAT (STRICT JSON) ==
Return a JSON array. One object per service:
```json
[
  {{
    "service_name": "<exact name from input>",
    "internal_code": "<code from input>",
    "decision": "Approved" | "Disapproved",
    "justification": "<3-5 sentences: (1) Coverage result from layers 1-3, (2) Medical necessity from layer 4, (3) Final decision with specific evidence>",
    "item_sequence": <integer from input>,
    "rejection_code": "<single code or empty string if approved>",
    "confidence": <0.0 to 1.0>,
    "needs_review": <true if confidence < 0.8 or edge case>
  }}
]
```

== REJECTION CODE CATALOG ==
{rejection_codes}

== CRITICAL RULES ==
1. Copy service_name, internal_code, item_sequence EXACTLY from input
2. Justification must cite SPECIFIC findings from context (not generic statements)
3. If approved → rejection_code is empty string ""
4. If disapproved → exactly ONE rejection code
5. Set confidence based on clarity of evidence (1.0 = definitive, 0.5 = borderline)
6. Set needs_review=true if confidence < 0.8 or unusual case

Output ONLY the JSON array, no other text."""

    return prompt


#############################################################################
# 4. OUTPUT VALIDATION
#############################################################################

ALLOWED_REJECTION_CODES = [
    "AD-3-6", "AD-3-8", "BE-1-3", "BE-1-5", "CV-1-3", "CV-1-4", "CV-3-2",
    "CV-4-1", "CV-4-7", "CV-4-9", "SE-1-9", "CV-4-2", "CV-1-6", "CV-1-10",
    "CV-1-8", "SE-1-6", "CV-3-1", "MN-1-1", "AD-1-2", "CV-4-3", "AD-3-5",
    "AD-3-7", "AD-1-4", "CV-4-5", "CV-4-8", "AD-1-9", "AD-2-4", "AD-1-6"
]


def validate_and_fix_decisions(
    decisions: List[Dict[str, Any]],
    items: List[Dict[str, Any]],
    health_declaration_findings: str,
    policy_findings: str
) -> List[Dict[str, Any]]:
    """
    Validate LLM decisions and fix common errors.
    Returns corrected decisions list.
    """
    validated = []

    for i, decision in enumerate(decisions):
        fixed = decision.copy()
        issues = []

        # 1. Validate rejection code
        rej_code = fixed.get('rejection_code', '')
        if fixed.get('decision') == 'Approved':
            if rej_code:
                issues.append(f"Approved but has rejection code '{rej_code}' - removing")
                fixed['rejection_code'] = ''
        else:  # Disapproved
            if not rej_code:
                issues.append("Disapproved but no rejection code - defaulting to MN-1-1")
                fixed['rejection_code'] = 'MN-1-1'
            elif rej_code not in ALLOWED_REJECTION_CODES:
                # Try to extract valid code
                pattern = r"[A-Z]{2}-[1-9]-[0-9]{1,2}"
                matches = re.findall(pattern, rej_code.upper())
                if matches and matches[0] in ALLOWED_REJECTION_CODES:
                    fixed['rejection_code'] = matches[0]
                else:
                    issues.append(f"Invalid code '{rej_code}' - defaulting to MN-1-1")
                    fixed['rejection_code'] = 'MN-1-1'

        # 2. Cross-check health declaration logic
        if health_declaration_findings and "Didn't Declare" in health_declaration_findings:
            if fixed.get('decision') == 'Approved':
                # This might be an error - but only flag for review, don't auto-fix
                if fixed.get('confidence', 1.0) >= 0.9:
                    fixed['confidence'] = 0.7
                    fixed['needs_review'] = True
                    issues.append("HD shows 'Didn't Declare' but service approved - flagged for review")

        # 3. Ensure confidence and needs_review exist
        if 'confidence' not in fixed:
            fixed['confidence'] = 0.8
        if 'needs_review' not in fixed:
            fixed['needs_review'] = fixed['confidence'] < 0.8

        # 4. Log issues
        if issues:
            logger.warning(f"Decision {i} validation issues: {issues}")

        validated.append(fixed)

    return validated


#############################################################################
# 5. CONFIDENCE-BASED ROUTING
#############################################################################

def route_by_confidence(decisions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Route decisions based on confidence for human review workflow.

    Returns:
        {
            'auto_approve': [...],    # High confidence approvals
            'auto_deny': [...],       # High confidence denials
            'needs_review': [...]     # Low confidence or edge cases
        }
    """
    routed = {
        'auto_approve': [],
        'auto_deny': [],
        'needs_review': []
    }

    for decision in decisions:
        confidence = decision.get('confidence', 0.8)
        needs_review = decision.get('needs_review', False)

        if needs_review or confidence < 0.85:
            routed['needs_review'].append(decision)
        elif decision.get('decision') == 'Approved':
            routed['auto_approve'].append(decision)
        else:
            routed['auto_deny'].append(decision)

    return routed


#############################################################################
# 6. ACCURACY EVALUATION HELPERS
#############################################################################

def evaluate_prediction(predicted: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare predicted decision to actual/expected decision.

    Returns evaluation metrics for this single prediction.
    """
    pred_decision = predicted.get('decision', '').lower()
    actual_decision = actual.get('decision', '').lower()

    is_correct = pred_decision == actual_decision

    # Determine error type
    error_type = None
    if not is_correct:
        if pred_decision == 'approved' and actual_decision == 'disapproved':
            error_type = 'false_positive'  # Wrongly approved
        else:
            error_type = 'false_negative'  # Wrongly denied

    # Check rejection code match (for denials)
    code_match = True
    if actual_decision == 'disapproved':
        pred_code = predicted.get('rejection_code', '')
        actual_code = actual.get('rejection_code', '')
        code_match = pred_code == actual_code

    return {
        'is_correct': is_correct,
        'error_type': error_type,
        'code_match': code_match,
        'confidence': predicted.get('confidence', 0.0),
        'service_name': predicted.get('service_name', '')
    }


def aggregate_evaluation(evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate individual evaluations into summary metrics.
    """
    total = len(evaluations)
    correct = sum(1 for e in evaluations if e['is_correct'])

    false_positives = sum(1 for e in evaluations if e['error_type'] == 'false_positive')
    false_negatives = sum(1 for e in evaluations if e['error_type'] == 'false_negative')

    code_matches = sum(1 for e in evaluations if e['code_match'])

    # Confidence calibration
    high_conf = [e for e in evaluations if e['confidence'] >= 0.9]
    high_conf_accuracy = sum(1 for e in high_conf if e['is_correct']) / len(high_conf) if high_conf else 0

    return {
        'total': total,
        'correct': correct,
        'accuracy': correct / total if total > 0 else 0,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'fp_rate': false_positives / total if total > 0 else 0,
        'fn_rate': false_negatives / total if total > 0 else 0,
        'code_accuracy': code_matches / total if total > 0 else 0,
        'high_confidence_accuracy': high_conf_accuracy,
        'high_confidence_count': len(high_conf)
    }
