"""
Human-in-the-Loop (HITL) Review System
Determines when human review is required for safety and accuracy
"""
from typing import Dict, Any, List, Tuple
from enum import Enum
from loguru import logger

from app.models.fhir_models import ParsedClinicalData
from app.models.response_models import ServiceDecision, DecisionType


class ReviewPriority(str, Enum):
    """Priority levels for human review"""
    URGENT = "URGENT"          # Review within 4 hours
    HIGH = "HIGH"              # Review within 24 hours
    MEDIUM = "MEDIUM"          # Review within 3 days
    LOW = "LOW"                # Review within 7 days
    AUTO = "AUTO"              # No review needed


class ReviewReason(str, Enum):
    """Reasons for requiring human review"""
    LOW_CONFIDENCE = "Low confidence score"
    HIGH_COST = "High cost procedure"
    EXPERIMENTAL = "Experimental or investigational"
    COMPLEX_CASE = "Complex medical case"
    POLICY_CONFLICT = "Conflicting policy guidance"
    UNUSUAL_REQUEST = "Unusual or rare request"
    PATIENT_HISTORY = "Patient history concerns"
    FRAUD_INDICATOR = "Potential fraud indicator"
    APPEAL = "Previous denial appealed"
    REGULATORY = "Regulatory requirement"


class HITLReviewer:
    """
    Human-in-the-Loop Review Decision System
    
    Implements safe guardrails for AI decisions:
    - Auto-approve only high-confidence, low-risk cases
    - Flag medium-confidence or high-risk cases for review
    - Escalate complex cases to appropriate reviewers
    """
    
    def __init__(self):
        # Configurable thresholds
        self.AUTO_APPROVE_CONFIDENCE = 0.90
        self.AUTO_APPROVE_MAX_COST = 5000  # SAR
        
        self.AUTO_DENY_CONFIDENCE = 0.90
        
        self.REVIEW_CONFIDENCE_THRESHOLD = 0.75
        self.HIGH_COST_THRESHOLD = 20000  # SAR
        self.URGENT_COST_THRESHOLD = 50000  # SAR
        
        logger.info("✓ HITL Reviewer initialized")
    
    def evaluate_decision(
        self,
        service_decision: ServiceDecision,
        clinical_data: ParsedClinicalData,
        orchestration_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate if AI decision requires human review
        
        Returns:
            Dict with:
            - requires_review: bool
            - review_priority: ReviewPriority
            - review_reasons: List[ReviewReason]
            - final_action: str (AUTO_APPROVED, AUTO_DENIED, REQUIRES_REVIEW)
            - reviewer_notes: str
        """
        
        reasons = []
        requires_review = False
        priority = ReviewPriority.AUTO
        
        # 1. Check confidence scores
        if service_decision.confidence < self.REVIEW_CONFIDENCE_THRESHOLD:
            requires_review = True
            reasons.append(ReviewReason.LOW_CONFIDENCE)
            priority = self._escalate_priority(priority, ReviewPriority.HIGH)
        
        # 2. Check cost thresholds
        cost = service_decision.requested_amount or 0
        
        if cost >= self.URGENT_COST_THRESHOLD:
            requires_review = True
            reasons.append(ReviewReason.HIGH_COST)
            priority = self._escalate_priority(priority, ReviewPriority.URGENT)
        elif cost >= self.HIGH_COST_THRESHOLD:
            requires_review = True
            reasons.append(ReviewReason.HIGH_COST)
            priority = self._escalate_priority(priority, ReviewPriority.HIGH)
        
        # 3. Check for experimental procedures
        if self._is_experimental(service_decision, clinical_data):
            requires_review = True
            reasons.append(ReviewReason.EXPERIMENTAL)
            priority = self._escalate_priority(priority, ReviewPriority.HIGH)
        
        # 4. Check for complex cases
        if self._is_complex_case(clinical_data, orchestration_result):
            requires_review = True
            reasons.append(ReviewReason.COMPLEX_CASE)
            priority = self._escalate_priority(priority, ReviewPriority.MEDIUM)
        
        # 5. Check for policy conflicts
        if self._has_policy_conflict(orchestration_result):
            requires_review = True
            reasons.append(ReviewReason.POLICY_CONFLICT)
            priority = self._escalate_priority(priority, ReviewPriority.MEDIUM)
        
        # 6. Check LLM-only decisions (no policy guidance)
        if orchestration_result.get("deciding_layer") == "llm_only":
            if service_decision.confidence < 0.80:  # Higher threshold for LLM-only
                requires_review = True
                reasons.append(ReviewReason.COMPLEX_CASE)
                priority = self._escalate_priority(priority, ReviewPriority.HIGH)
        
        # Determine final action
        final_action = self._determine_final_action(
            service_decision,
            requires_review,
            cost,
            clinical_data
        )
        
        # Generate reviewer notes
        reviewer_notes = self._generate_reviewer_notes(
            service_decision,
            clinical_data,
            orchestration_result,
            reasons
        )
        
        result = {
            "requires_review": requires_review,
            "review_priority": priority,
            "review_reasons": [r.value for r in reasons],
            "final_action": final_action,
            "reviewer_notes": reviewer_notes,
            "estimated_review_time": self._estimate_review_time(priority),
            "recommended_reviewer": self._recommend_reviewer(clinical_data, reasons)
        }
        
        if requires_review:
            logger.warning(f"⚠ REVIEW REQUIRED: {priority.value} - {', '.join([r.value for r in reasons])}")
        else:
            logger.info(f"✓ AUTO-DECISION: {final_action}")
        
        return result
    
    def _determine_final_action(
        self,
        service_decision: ServiceDecision,
        requires_review: bool,
        cost: float,
        clinical_data: ParsedClinicalData
    ) -> str:
        """Determine the final action to take"""
        
        # Case 1: Auto-approve (safe, low-risk)
        if not requires_review:
            if (service_decision.decision == DecisionType.APPROVED and 
                service_decision.confidence >= self.AUTO_APPROVE_CONFIDENCE and
                cost <= self.AUTO_APPROVE_MAX_COST):
                return "AUTO_APPROVED"
        
        # Case 2: Auto-deny (clear policy violation)
        if (service_decision.decision == DecisionType.DENIED and
            service_decision.confidence >= self.AUTO_DENY_CONFIDENCE and
            not requires_review):  # No review reasons
            return "AUTO_DENIED"
        
        # Case 3: Requires human review
        return "REQUIRES_REVIEW"
    
    def _is_experimental(
        self,
        service_decision: ServiceDecision,
        clinical_data: ParsedClinicalData
    ) -> bool:
        """Check if procedure is experimental"""
        experimental_keywords = [
            "experimental", "investigational", "trial", 
            "research", "novel", "unproven"
        ]
        
        description = service_decision.service_description.lower()
        return any(keyword in description for keyword in experimental_keywords)
    
    def _is_complex_case(
        self,
        clinical_data: ParsedClinicalData,
        orchestration_result: Dict[str, Any]
    ) -> bool:
        """Check if this is a complex medical case"""
        
        # Multiple diagnoses
        if len(clinical_data.diagnoses) >= 3:
            return True
        
        # Multiple procedures
        if len(clinical_data.procedures) >= 2:
            return True
        
        # LLM had low confidence
        if orchestration_result.get("final_confidence", 1.0) < 0.70:
            return True
        
        return False
    
    def _has_policy_conflict(self, orchestration_result: Dict[str, Any]) -> bool:
        """Check if there are conflicting policy guidelines"""
        
        rag_results = orchestration_result.get("layer_results", {}).get("rag_system", [])
        
        # Check if multiple high-confidence policies with different implications
        high_conf_policies = [p for p in rag_results if p.get("relevance_score", 0) >= 0.80]
        
        if len(high_conf_policies) >= 2:
            # Simple heuristic: if policies from different sources, might conflict
            sources = set(p.get("source", "") for p in high_conf_policies)
            if len(sources) >= 2:
                return True
        
        return False
    
    def _escalate_priority(
        self,
        current: ReviewPriority,
        new: ReviewPriority
    ) -> ReviewPriority:
        """Escalate to higher priority if needed"""
        priority_order = {
            ReviewPriority.AUTO: 0,
            ReviewPriority.LOW: 1,
            ReviewPriority.MEDIUM: 2,
            ReviewPriority.HIGH: 3,
            ReviewPriority.URGENT: 4
        }
        
        if priority_order[new] > priority_order[current]:
            return new
        return current
    
    def _estimate_review_time(self, priority: ReviewPriority) -> str:
        """Estimate time for human review"""
        times = {
            ReviewPriority.AUTO: "N/A",
            ReviewPriority.LOW: "Within 7 days",
            ReviewPriority.MEDIUM: "Within 3 days",
            ReviewPriority.HIGH: "Within 24 hours",
            ReviewPriority.URGENT: "Within 4 hours"
        }
        return times.get(priority, "Unknown")
    
    def _recommend_reviewer(
        self,
        clinical_data: ParsedClinicalData,
        reasons: List[ReviewReason]
    ) -> str:
        """Recommend type of reviewer needed"""
        
        # High-cost cases → Financial reviewer
        if ReviewReason.HIGH_COST in reasons:
            return "Financial + Clinical Reviewer"
        
        # Experimental → Medical Director
        if ReviewReason.EXPERIMENTAL in reasons:
            return "Medical Director"
        
        # Complex cases → Specialist
        if ReviewReason.COMPLEX_CASE in reasons:
            # Determine specialty from diagnosis
            specialty = self._determine_specialty(clinical_data)
            return f"Clinical Reviewer ({specialty})"
        
        # Default
        return "Clinical Reviewer"
    
    def _determine_specialty(self, clinical_data: ParsedClinicalData) -> str:
        """Determine medical specialty based on diagnosis"""
        
        if not clinical_data.diagnoses:
            return "General Medicine"
        
        # Simple keyword matching (would be more sophisticated in production)
        primary_diag = clinical_data.diagnoses[0].get("display", "").lower()
        
        if "cardiac" in primary_diag or "heart" in primary_diag:
            return "Cardiology"
        elif "orthopedic" in primary_diag or "joint" in primary_diag or "knee" in primary_diag:
            return "Orthopedics"
        elif "cancer" in primary_diag or "tumor" in primary_diag:
            return "Oncology"
        elif "diabetes" in primary_diag:
            return "Endocrinology"
        else:
            return "General Medicine"
    
    def _generate_reviewer_notes(
        self,
        service_decision: ServiceDecision,
        clinical_data: ParsedClinicalData,
        orchestration_result: Dict[str, Any],
        reasons: List[ReviewReason]
    ) -> str:
        """Generate notes for human reviewer"""
        
        notes = []
        
        notes.append(f"AI Decision: {service_decision.decision.value}")
        notes.append(f"AI Confidence: {service_decision.confidence:.2%}")
        notes.append(f"Deciding Layer: {orchestration_result.get('deciding_layer', 'unknown')}")
        
        if reasons:
            notes.append(f"\nReview Reasons:")
            for reason in reasons:
                notes.append(f"  - {reason.value}")
        
        notes.append(f"\nPatient: Age {clinical_data.patient_age}, {clinical_data.patient_gender}")
        notes.append(f"Service: {service_decision.service_description}")
        notes.append(f"Cost: {service_decision.requested_amount or 0:,.0f} SAR")
        
        if clinical_data.diagnoses:
            notes.append(f"\nDiagnoses:")
            for diag in clinical_data.diagnoses[:3]:
                notes.append(f"  - {diag.get('code')}: {diag.get('display')}")
        
        if service_decision.policy_reference:
            notes.append(f"\nPolicy References Used:")
            for policy in service_decision.policy_reference[:2]:
                notes.append(f"  - {policy[:100]}...")
        
        return "\n".join(notes)


# Global instance
hitl_reviewer = HITLReviewer()
