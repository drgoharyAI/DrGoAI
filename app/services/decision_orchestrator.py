"""
Enhanced Decision Orchestrator - Multi-Layer Decision Making with Health Declaration Layer

Implements a hierarchical decision-making approach with comprehensive validation:
Layer 0 (PRE-SCREENING): Health Declaration Validation - Checks declared conditions
Layer 1 (HIGHEST): Medical Rules Engine - Hard rules, 95% confidence
Layer 2 (HIGH): RAG ChromaDB - Policy-based decisions, 75-90% confidence  
Layer 3 (MEDIUM): Medical LLM / Ensemble - Clinical reasoning, 50-75% confidence

Plus Validation Layers:
- Medical Necessity Validation
- Patient History Analysis
- Financial Risk Assessment
- Fraud Detection
- HITL Review Decision

Each layer can make a final decision or pass to the next layer.
Higher layers ALWAYS override lower layers.
"""
from typing import Dict, Any, List, Tuple, Optional
from loguru import logger
from datetime import datetime

from app.models.fhir_models import ParsedClinicalData
from app.models.response_models import (
    DecisionType,
    ServiceDecision,
    ConfidenceLevel
)
from app.services.rules_engine import rules_engine
from app.services.rag_system import rag_system
from app.services.llm_service import llm_service

# Import all enhancement modules
from app.services.hitl_reviewer import hitl_reviewer
from app.services.medical_necessity_validator import medical_necessity_validator
from app.services.patient_history_analyzer import patient_history_analyzer
from app.services.financial_risk_analyzer import financial_risk_analyzer
from app.services.fraud_detector import fraud_detector
from app.services.ensemble_llm_system import ensemble_llm
from app.services.feedback_learning_system import feedback_learning_system
from app.services.health_declaration_validator import health_declaration_validator
from app.services.claim_classifier import claim_classifier  # NEW: Claim classification


class DecisionLayer:
    """Represents a decision-making layer"""
    def __init__(self, name: str, confidence_range: Tuple[float, float], priority: int):
        self.name = name
        self.confidence_range = confidence_range  # (min, max)
        self.priority = priority  # Lower number = higher priority


class DecisionOrchestrator:
    """
    Orchestrates multi-layer adjudication decisions with Health Declaration pre-screening
    
    Decision Flow:
    0. Health Declaration (PRE-SCREENING) - Validates declared conditions
       - If HD required and NOT declared → HITL Review
       - If pre-existing within waiting period → Deny
       - If all OK → Continue to normal layers
    
    1. Rules Engine evaluates first
       - If auto-approve/deny → FINAL DECISION (95% confidence)
       - If uncertain → Pass to RAG
    
    2. RAG System retrieves policies
       - If high-relevance match (≥75%) → STRONG RECOMMENDATION (75-90% confidence)
       - Can override LLM but not Rules Engine
       - If uncertain → Pass to LLM
    
    3. LLM provides final reasoning
       - Clinical assessment (50-75% confidence)
       - Used when rules and policies don't provide clear answer
    
    Final Decision Priority:
    Health Declaration > Rules Engine > RAG System > LLM
    """
    
    def __init__(self):
        # Define decision layers
        self.layers = {
            "health_declaration": DecisionLayer("Health Declaration", (0.95, 0.99), priority=0),
            "rules_engine": DecisionLayer("Rules Engine", (0.90, 0.99), priority=1),
            "rag_system": DecisionLayer("RAG Policy System", (0.75, 0.90), priority=2),
            "llm_reasoning": DecisionLayer("Medical LLM", (0.50, 0.75), priority=3)
        }
        
        logger.info("✓ Decision Orchestrator initialized with HD pre-screening + 3-layer hierarchy")
    
    def adjudicate_request(
        self,
        clinical_data: ParsedClinicalData,
        policy_start_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main orchestration method - coordinates all decision layers with HD pre-screening
        
        Enhanced Flow:
        0. Health Declaration Validation (PRE-SCREENING)
        1. Rules Engine → Auto decisions
        2. RAG System → Policy retrieval
        3. LLM/Ensemble → Clinical reasoning
        4. Medical Necessity Validation
        5. Patient History Analysis
        6. Financial Risk Assessment
        7. Fraud Detection
        8. HITL Review Decision
        
        Args:
            clinical_data: Parsed clinical data
            policy_start_date: Member's policy start date (ISO format)
        
        Returns comprehensive adjudication with all safety checks
        """
        logger.info(f"=== Enhanced Adjudication with HD for {clinical_data.request_id} ===")
        
        decision_path = []
        layer_results = {}
        validation_results = {}
        
        # === LAYER 0: HEALTH DECLARATION PRE-SCREENING ===
        
        logger.info("LAYER 0 (PRE-SCREENING): Health Declaration Validation...")
        
        # Use policy start date from clinical data or parameter
        if not policy_start_date and hasattr(clinical_data, 'policy_start_date'):
            policy_start_date = clinical_data.policy_start_date
        elif not policy_start_date:
            # Default to 6 months ago if not provided
            from datetime import timedelta
            policy_start_date = (datetime.utcnow() - timedelta(days=180)).isoformat()
        
        hd_result = health_declaration_validator.validate_health_declaration(
            clinical_data=clinical_data,
            member_id=clinical_data.patient_id,
            policy_start_date=policy_start_date
        )
        
        layer_results["health_declaration"] = hd_result
        validation_results["health_declaration"] = hd_result
        
        # Add HD to decision path
        decision_path.append({
            "layer": "Health Declaration (Pre-Screening)",
            "decision": hd_result["action"].upper(),
            "confidence": 0.95 if hd_result["hd_validation_required"] else 0.99,
            "hd_status": hd_result["hd_status"],
            "final": hd_result["requires_hitl"] or hd_result["action"] == "deny_pre_existing",
            "reason": hd_result["reason"] if hd_result["reason"] else "No HD validation required"
        })
        
        # Handle HD validation results
        if hd_result["requires_hitl"]:
            # HD validation failed - requires HITL review
            logger.error(f"  🚨 HD VALIDATION FAILED - HITL REQUIRED")
            logger.error(f"     Reason: {hd_result['reason']}")
            logger.error(f"     Flagged conditions: {', '.join(hd_result['flagged_conditions'])}")
            
            # Create service decisions flagged for HD review
            service_decisions = self._create_hd_flagged_decisions(
                clinical_data, 
                hd_result
            )
            
            return {
                "service_decisions": service_decisions,
                "decision_path": decision_path,
                "layer_results": layer_results,
                "validation_results": validation_results,
                "final_confidence": 0.95,
                "deciding_layer": "health_declaration",
                "rag_consulted": False,
                "llm_consulted": False,
                "hitl_results": [{"requires_review": True, "review_reasons": [hd_result["reason"]]}],
                "requires_human_review": True,
                "hd_blocked": True
            }
        
        elif hd_result["action"] == "deny_pre_existing":
            # Pre-existing condition within waiting period - deny
            logger.warning(f"  ⚠ HD DENIAL: {hd_result['reason']}")
            
            service_decisions = self._create_hd_denied_decisions(
                clinical_data,
                hd_result
            )
            
            return {
                "service_decisions": service_decisions,
                "decision_path": decision_path,
                "layer_results": layer_results,
                "validation_results": validation_results,
                "final_confidence": 0.95,
                "deciding_layer": "health_declaration",
                "rag_consulted": False,
                "llm_consulted": False,
                "hitl_results": [],
                "requires_human_review": False,
                "hd_blocked": True
            }
        
        else:
            # HD validation passed or not required - continue to normal adjudication
            logger.info(f"  ✓ HD VALIDATION: {hd_result['reason']}")
            if hd_result["hd_conditions_found"]:
                logger.info(f"    Validated {len(hd_result['hd_conditions_found'])} declared condition(s)")
        
        # === CONTINUE WITH NORMAL ADJUDICATION LAYERS ===
        
        # === LAYER 0.5: CLAIM CLASSIFICATION (ROUTING) ===
        
        logger.info("LAYER 0.5: Classifying Claim for Intelligent Routing...")
        
        try:
            classification = claim_classifier.classify_claim(
                clinical_data=clinical_data,
                use_llm=True,  # Use LLM for better accuracy if available
                confidence_threshold=0.6
            )
            
            layer_results["classification"] = classification
            primary_category = classification['primary_category']
            category_name = classification['primary_category_name']
            
            decision_path.append({
                "layer": "Claim Classification",
                "primary_category": category_name,
                "total_categories": classification['total_categories_matched'],
                "method": classification['classification_method'],
                "categories": [c['name'] for c in classification['categories'][:3]],  # Top 3
                "final": False
            })
            
            logger.info(f"  ✓ Classified as: {category_name}")
            logger.info(f"    Additional categories: {classification['total_categories_matched'] - 1}")
            
            # Get category-specific config for routing
            category_rules_file = None
            rag_filter = {}
            if classification['categories']:
                category_rules_file = classification['categories'][0].get('rules_file')
                rag_filter = classification['categories'][0].get('rag_filter', {})
            
        except Exception as e:
            logger.warning(f"  ⚠ Classification failed: {e}, continuing without classification")
            classification = None
            primary_category = None
            category_name = "General"
            category_rules_file = None
            rag_filter = {}
        
        # LAYER 1: Rules Engine (HIGHEST PRIORITY)
        logger.info("LAYER 1: Evaluating Rules Engine...")
        if category_rules_file:
            logger.info(f"  → Using category-specific rules: {category_rules_file}")
        # NOTE: To enable category-specific rules, modify rules_engine.evaluate_request to accept:
        # rules_result = rules_engine.evaluate_request(clinical_data, category_rules_file=category_rules_file)
        rules_result = rules_engine.evaluate_request(clinical_data)
        layer_results["rules_engine"] = rules_result
        
        if rules_result.get("auto_decision"):
            decision_path.append({
                "layer": "Rules Engine",
                "decision": rules_result["auto_decision"],
                "confidence": rules_result.get("confidence", 0.95),
                "rules_triggered": rules_result.get("rules_triggered", []),
                "final": True
            })
            
            logger.info(f"  ✓ RULES ENGINE DECIDED: {rules_result['auto_decision']}")
            service_decisions = self._create_rules_based_decisions(clinical_data, rules_result)
        else:
            decision_path.append({
                "layer": "Rules Engine",
                "decision": "UNCERTAIN",
                "confidence": 0.5,
                "rules_triggered": rules_result.get("rules_triggered", []),
                "final": False,
                "reason": "No definitive rule match, passing to RAG"
            })
            logger.info("  → No definitive decision, passing to RAG System...")
            
            # LAYER 2: RAG Policy System
            logger.info("LAYER 2: Querying RAG Policy Database...")
            if rag_filter:
                logger.info(f"  → Filtering by category: {rag_filter}")
            # NOTE: To enable category filtering in RAG, modify rag_system.retrieve_relevant_policies to accept:
            # policy_results = rag_system.retrieve_relevant_policies(clinical_data, top_k=10, min_relevance=0.6, metadata_filter=rag_filter)
            policy_results = rag_system.retrieve_relevant_policies(
                clinical_data, top_k=10, min_relevance=0.6
            )
            layer_results["rag_system"] = policy_results
            
            high_confidence_policies = [p for p in policy_results if p.get("can_override_llm", False)]
            
            if high_confidence_policies:
                avg_relevance = sum(p["relevance_score"] for p in high_confidence_policies) / len(high_confidence_policies)
                decision_path.append({
                    "layer": "RAG Policy System",
                    "decision": "POLICY_GUIDED",
                    "confidence": float(avg_relevance),
                    "policies_matched": len(high_confidence_policies),
                    "final": False
                })
                logger.info(f"  ✓ RAG FOUND {len(high_confidence_policies)} HIGH-CONFIDENCE POLICIES")
                rag_confidence = avg_relevance
            else:
                decision_path.append({
                    "layer": "RAG Policy System",
                    "decision": "LOW_CONFIDENCE",
                    "confidence": 0.6,
                    "policies_matched": len(policy_results),
                    "final": False
                })
                logger.info(f"  → Found {len(policy_results)} policies but no high-confidence matches")
                rag_confidence = 0.6
            
            # LAYER 3: Medical LLM (with optional Ensemble)
            logger.info("LAYER 3: Consulting Medical LLM...")
            
            # Use ensemble if available, otherwise single LLM
            ensemble_result = ensemble_llm.adjudicate_ensemble(clinical_data, rules_result, policy_results)
            service_decisions = ensemble_result["service_decisions"]
            layer_results["llm"] = ensemble_result
            
            # Adjust confidence based on RAG
            for decision in service_decisions:
                if high_confidence_policies:
                    original_confidence = decision.confidence
                    decision.confidence = (0.4 * original_confidence) + (0.6 * rag_confidence)
                    decision.explanation = f"[Policy-Guided] {decision.explanation}"
                    decision.policy_reference = [p["content"][:200] + "..." for p in high_confidence_policies[:2]]
                
                # Add HD info to explanation if HD conditions were found
                if hd_result["hd_conditions_found"]:
                    decision.explanation = f"[HD Validated] {decision.explanation}"
            
            decision_path.append({
                "layer": "Medical LLM/Ensemble",
                "decision": "COMPLETED",
                "confidence": sum(d.confidence for d in service_decisions) / len(service_decisions),
                "services_evaluated": len(service_decisions),
                "final": True
            })
            
            logger.info(f"  ✓ LLM COMPLETED: {len(service_decisions)} service decisions")
        
        # === VALIDATION LAYERS ===
        
        # VALIDATION 1: Medical Necessity
        logger.info("VALIDATION: Medical Necessity Check...")
        medical_necessity_result = medical_necessity_validator.validate(clinical_data, service_decisions)
        validation_results["medical_necessity"] = medical_necessity_result
        
        if not medical_necessity_result["overall_valid"]:
            logger.warning(f"  ⚠ Medical necessity concerns: {medical_necessity_result['flags']}")
            # Downgrade confidence for services that failed validation
            for i, svc_val in enumerate(medical_necessity_result["validations"]):
                if i < len(service_decisions) and not svc_val["valid"]:
                    service_decisions[i].confidence *= svc_val["score"]
                    service_decisions[i].requires_human_review = True
        
        # VALIDATION 2: Patient History
        logger.info("VALIDATION: Patient History Analysis...")
        history_result = patient_history_analyzer.analyze_history(clinical_data)
        validation_results["patient_history"] = history_result
        
        if history_result["flags"]:
            logger.warning(f"  ⚠ History flags: {', '.join(history_result['flags'])}")
            # Flag services for review if history issues
            for service in service_decisions:
                if history_result["risk_score"] > 0.5:
                    service.requires_human_review = True
        
        # VALIDATION 3: Financial Risk
        logger.info("VALIDATION: Financial Risk Assessment...")
        financial_result = financial_risk_analyzer.analyze_financial_risk(clinical_data, service_decisions)
        validation_results["financial_risk"] = financial_result
        
        if financial_result["risk_level"] in ["MEDIUM", "HIGH"]:
            logger.warning(f"  ⚠ Financial risk: {financial_result['risk_level']}")
        
        # VALIDATION 4: Fraud Detection
        logger.info("VALIDATION: Fraud Detection...")
        fraud_result = fraud_detector.detect_fraud(clinical_data)
        validation_results["fraud_detection"] = fraud_result
        
        if fraud_result["requires_investigation"]:
            logger.error(f"  🚨 FRAUD RISK: {fraud_result['fraud_risk']}")
            # Flag all services for investigation
            for service in service_decisions:
                service.requires_human_review = True
                service.review_reason = "Fraud investigation required"
        
        # VALIDATION 5: HITL Review Decision
        logger.info("VALIDATION: HITL Review Assessment...")
        orchestration_result_temp = {
            "service_decisions": service_decisions,
            "deciding_layer": self._determine_deciding_layer(high_confidence_policies if 'high_confidence_policies' in locals() else []),
            "final_confidence": sum(d.confidence for d in service_decisions) / len(service_decisions)
        }
        
        # Assess each service for HITL
        hitl_results = []
        for service in service_decisions:
            hitl_result = hitl_reviewer.evaluate_decision(service, clinical_data, orchestration_result_temp)
            hitl_results.append(hitl_result)
            
            # Apply HITL decision
            if hitl_result["requires_review"]:
                service.requires_human_review = True
                service.review_reason = "; ".join(hitl_result["review_reasons"])
        
        validation_results["hitl_review"] = hitl_results
        
        # Determine final deciding layer
        if hd_result["hd_validation_required"]:
            deciding_layer = "health_declaration_validated"
        elif rules_result.get("auto_decision"):
            deciding_layer = "rules_engine"
        elif 'high_confidence_policies' in locals() and len(high_confidence_policies) > 0:
            deciding_layer = "rag_system_guided_llm"
        else:
            deciding_layer = "llm_only"
        
        final_confidence = sum(d.confidence for d in service_decisions) / len(service_decisions)
        
        logger.info(f"=== Adjudication Complete ===")
        logger.info(f"HD Status: {hd_result['hd_status']}")
        logger.info(f"Deciding Layer: {deciding_layer}")
        logger.info(f"Final Confidence: {final_confidence:.2f}")
        logger.info(f"Services Requiring Review: {sum(1 for d in service_decisions if d.requires_human_review)}/{len(service_decisions)}")
        
        return {
            "service_decisions": service_decisions,
            "decision_path": decision_path,
            "layer_results": layer_results,
            "validation_results": validation_results,
            "classification": classification if classification else {"primary_category": "general", "primary_category_name": "General"},  # NEW
            "final_confidence": float(final_confidence),
            "deciding_layer": deciding_layer,
            "rag_consulted": True,
            "llm_consulted": True,
            "hitl_results": hitl_results,
            "requires_human_review": any(d.requires_human_review for d in service_decisions),
            "hd_blocked": False
        }
    
    def _create_hd_flagged_decisions(
        self,
        clinical_data: ParsedClinicalData,
        hd_result: Dict[str, Any]
    ) -> List[ServiceDecision]:
        """Create service decisions when HD validation requires HITL"""
        
        decisions = []
        for service in clinical_data.services:
            decision = ServiceDecision(
                service_sequence=service.get("sequence", 1),
                service_code=service.get("code", ""),
                service_description=service.get("description", ""),
                requested_amount=service.get("net_amount"),
                decision=DecisionType.PENDING,
                approved_amount=0,
                confidence=0.95,
                confidence_level=ConfidenceLevel.HIGH,
                explanation=f"Health Declaration Review Required: {hd_result['reason']}",
                clinical_rationale=f"Member has undeclared conditions requiring health declaration: {', '.join(hd_result['flagged_conditions'])}",
                policy_reference=["Health Declaration Policy - Pre-existing Condition Disclosure"],
                rules_applied=["hd_validation_required"],
                requires_human_review=True,
                review_reason=hd_result["reason"],
                medical_necessity_met=None
            )
            
            decisions.append(decision)
        
        return decisions
    
    def _create_hd_denied_decisions(
        self,
        clinical_data: ParsedClinicalData,
        hd_result: Dict[str, Any]
    ) -> List[ServiceDecision]:
        """Create service decisions when HD validation denies due to pre-existing"""
        
        decisions = []
        for service in clinical_data.services:
            decision = ServiceDecision(
                service_sequence=service.get("sequence", 1),
                service_code=service.get("code", ""),
                service_description=service.get("description", ""),
                requested_amount=service.get("net_amount"),
                decision=DecisionType.DENIED,
                approved_amount=0,
                confidence=0.95,
                confidence_level=ConfidenceLevel.HIGH,
                explanation=f"Denied: {hd_result['reason']}",
                clinical_rationale=f"Pre-existing condition within waiting period: {', '.join(hd_result['flagged_conditions'])}",
                policy_reference=["Health Declaration Policy - Waiting Period for Pre-existing Conditions"],
                rules_applied=["hd_pre_existing_waiting_period"],
                requires_human_review=False,
                medical_necessity_met=False
            )
            
            decisions.append(decision)
        
        return decisions
    
    def _determine_deciding_layer(self, high_confidence_policies: List) -> str:
        """Helper to determine which layer made the decision"""
        if len(high_confidence_policies) > 0:
            return "rag_system_guided_llm"
        else:
            return "llm_only"
    
    def _create_rules_based_decisions(
        self,
        clinical_data: ParsedClinicalData,
        rules_result: Dict[str, Any]
    ) -> List[ServiceDecision]:
        """Create service decisions when Rules Engine made final decision"""
        
        auto_decision = rules_result["auto_decision"]
        confidence = rules_result.get("confidence", 0.95)
        
        decisions = []
        for service in clinical_data.services:
            explanation = self._get_rules_explanation(rules_result)
            
            decision = ServiceDecision(
                service_sequence=service.get("sequence", 1),
                service_code=service.get("code", ""),
                service_description=service.get("description", ""),
                requested_amount=service.get("net_amount"),
                decision=auto_decision,
                approved_amount=service.get("net_amount") if auto_decision == DecisionType.APPROVED else 0,
                confidence=confidence,
                confidence_level=ConfidenceLevel.HIGH,
                explanation=explanation,
                clinical_rationale=f"[Rules Engine] {explanation}",
                policy_reference=[],
                rules_applied=rules_result.get("rules_triggered", []),
                requires_human_review=False,
                medical_necessity_met=(auto_decision == DecisionType.APPROVED)
            )
            
            decisions.append(decision)
        
        return decisions
    
    def _get_rules_explanation(self, rules_result: Dict[str, Any]) -> str:
        """Generate explanation from rules engine results"""
        auto_decision = rules_result["auto_decision"]
        
        if auto_decision == DecisionType.APPROVED:
            return "Service automatically approved based on policy rules: meets all coverage criteria and requirements."
        elif auto_decision == DecisionType.DENIED:
            # Get denial reasons
            reasons = []
            if rules_result.get("rule_results", {}).get("auto_deny", {}).get("triggered"):
                reasons = rules_result["rule_results"]["auto_deny"].get("reasons", [])
            
            if reasons:
                return f"Service denied by policy rules: {'; '.join(reasons)}"
            else:
                return "Service denied based on policy coverage rules."
        else:
            return "Service requires additional review based on policy rules."
    
    def get_layer_statistics(self) -> Dict[str, Any]:
        """Get statistics about the decision layers"""
        return {
            "layers": [
                {
                    "name": layer.name,
                    "priority": layer.priority,
                    "confidence_range": layer.confidence_range,
                    "description": self._get_layer_description(name)
                }
                for name, layer in sorted(
                    self.layers.items(),
                    key=lambda x: x[1].priority
                )
            ],
            "hierarchy": "Health Declaration > Rules Engine > RAG Policy System > Medical LLM"
        }
    
    def _get_layer_description(self, layer_name: str) -> str:
        """Get description of each layer"""
        descriptions = {
            "health_declaration": "Pre-screening for health declaration requirements",
            "rules_engine": "Hard policy rules for automatic approval/denial",
            "rag_system": "Policy document retrieval and matching",
            "llm_reasoning": "Clinical reasoning and complex case analysis"
        }
        return descriptions.get(layer_name, "Unknown layer")


# Global instance
decision_orchestrator = DecisionOrchestrator()
