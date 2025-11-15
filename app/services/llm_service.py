"""
Medical LLM Service - Google Gemini Only
Uses Google Gemini for clinical reasoning and adjudication
"""
from typing import Dict, Any, List, Optional
from loguru import logger
import json

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    logger.error("Google Gemini library not available! Install with: pip install google-generativeai")
    GEMINI_AVAILABLE = False

from app.config.settings import settings
from app.models.fhir_models import ParsedClinicalData
from app.models.response_models import DecisionType, ServiceDecision, ConfidenceLevel

class MedicalLLMService:
    """Medical LLM for adjudication reasoning using Google Gemini"""
    
    def __init__(self):
        self.gemini_model = None
        self.use_gemini = False
        
        try:
            self._initialize_gemini()
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            logger.warning("⚠️ System will use rule-based fallback only")
            logger.warning("⚠️ Please configure GOOGLE_API_KEY to enable AI-powered decisions")
    
    def _initialize_gemini(self):
        """Initialize Google Gemini"""
        
        if not GEMINI_AVAILABLE:
            logger.error("❌ Google Gemini library not installed")
            logger.error("   Install with: pip install google-generativeai")
            return
        
        if not settings.GOOGLE_API_KEY:
            logger.warning("❌ GOOGLE_API_KEY not configured")
            logger.warning("   Set GOOGLE_API_KEY in environment variables or .env file")
            logger.warning("   Get your API key from: https://makersuite.google.com/app/apikey")
            return
        
        logger.info("Initializing Google Gemini client...")
        
        try:
            # Configure Gemini with API key
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            
            # Use Gemini model from settings
            model_name = settings.GEMINI_MODEL
            self.gemini_model = genai.GenerativeModel(model_name)
            self.use_gemini = True
            
            logger.info("✅ Google Gemini initialized successfully")
            logger.info(f"   Model: {model_name}")
            logger.info(f"   Max tokens: {settings.GEMINI_MAX_TOKENS}")
            logger.info(f"   Temperature: {settings.GEMINI_TEMPERATURE}")
            logger.info("   Ready for AI-powered adjudication")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini: {e}")
            logger.warning("   Check your GOOGLE_API_KEY is valid")
            logger.warning("   System will use rule-based fallback only")
    
    def adjudicate_services(
        self,
        clinical_data: ParsedClinicalData,
        rules_results: Dict[str, Any],
        policy_context: List[Dict[str, Any]]
    ) -> List[ServiceDecision]:
        """
        Make adjudication decisions for each service using LLM
        
        Args:
            clinical_data: Parsed clinical information
            rules_results: Results from rules engine
            policy_context: Retrieved policy sections
            
        Returns:
            List of service decisions
        """
        
        # Check if rules engine made automatic decision
        if rules_results.get("auto_decision"):
            return self._create_auto_decisions(
                clinical_data, 
                rules_results
            )
        
        # Use LLM for complex adjudication
        service_decisions = []
        
        for service in clinical_data.services:
            decision = self._adjudicate_single_service(
                service,
                clinical_data,
                rules_results,
                policy_context
            )
            service_decisions.append(decision)
        
        return service_decisions
    
    def _adjudicate_single_service(
        self,
        service: Dict[str, Any],
        clinical_data: ParsedClinicalData,
        rules_results: Dict[str, Any],
        policy_context: List[Dict[str, Any]]
    ) -> ServiceDecision:
        """Adjudicate a single service using LLM"""
        
        # Build prompt for LLM
        prompt = self._build_adjudication_prompt(
            service,
            clinical_data,
            rules_results,
            policy_context
        )
        
        # Get LLM decision using Google Gemini
        if self.use_gemini and self.gemini_model:
            llm_response = self._query_gemini(prompt)
        else:
            # No LLM available - use rule-based fallback
            logger.warning("⚠️ Gemini not available, using rule-based fallback")
            llm_response = self._fallback_decision(service, clinical_data, rules_results)
        
        # Parse LLM response into structured decision
        decision = self._parse_llm_response(
            llm_response,
            service,
            clinical_data,
            rules_results
        )
        
        return decision
    
    def _build_adjudication_prompt(
        self,
        service: Dict[str, Any],
        clinical_data: ParsedClinicalData,
        rules_results: Dict[str, Any],
        policy_context: List[Dict[str, Any]]
    ) -> str:
        """Build comprehensive prompt for LLM"""
        
        # Format policy context
        policy_text = "\n\n".join([
            f"Policy Section (relevance: {p['relevance_score']:.2f}):\n{p['content']}"
            for p in policy_context[:3]  # Top 3 most relevant
        ])
        
        # Format diagnoses
        diagnoses_text = ", ".join([
            f"{d['code']}: {d['display']}" 
            for d in clinical_data.diagnoses
        ])
        
        # Format rules results
        risk_flags = ", ".join(rules_results.get("risk_flags", []))
        
        prompt = f"""You are a medical insurance adjudication specialist. Analyze the following pre-authorization request and make an approval decision.

**Patient Information:**
- Age: {clinical_data.patient_age or 'Unknown'}
- Gender: {clinical_data.patient_gender or 'Unknown'}

**Clinical Information:**
- Diagnoses: {diagnoses_text or 'None provided'}
- Primary Service: {service['code']} - {service['description']}
- Service Cost: {service.get('net_amount', 'Not specified')} {service.get('currency', 'SAR')}
- Service Date: {service.get('serviced_date', 'Not specified')}

**Insurance Policy Guidelines:**
{policy_text}

**Rules Engine Analysis:**
- Risk Flags: {risk_flags or 'None'}
- Rules Triggered: {', '.join(rules_results.get('rules_triggered', []))}

**Instructions:**
1. Evaluate medical necessity based on diagnosis and requested service
2. Consider policy guidelines and coverage rules
3. Assess if the service is appropriate, not experimental, and follows standards of care
4. Make a decision: APPROVE or DENY

**Provide your decision in the following format:**
DECISION: [APPROVE/DENY]
CONFIDENCE: [0.0-1.0]
REASONING: [Brief clinical reasoning]
POLICY_BASIS: [Relevant policy sections]

Decision:"""

        return prompt
    
    def _query_gemini(self, prompt: str) -> str:
        """Query Google Gemini model"""
        try:
            # Create system instruction + user prompt
            full_prompt = f"""You are a medical insurance adjudication specialist with expertise in clinical reasoning and policy interpretation for Saudi Arabia's health insurance system.

{prompt}

Provide your analysis in the following format:
DECISION: [APPROVED/DENIED/PENDING]
CONFIDENCE: [0.0-1.0]
REASONING: [Your detailed medical reasoning]
POLICY_BASIS: [Relevant policy considerations]
"""
            
            # Configure safety settings for medical content
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_MEDICAL",
                    "threshold": "BLOCK_NONE"
                }
            ]
            
            # Generate response
            response = self.gemini_model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": settings.GEMINI_TEMPERATURE,
                    "max_output_tokens": settings.GEMINI_MAX_TOKENS,
                }
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._fallback_response()
    
    def _fallback_response(self) -> str:
        """Fallback response when LLM unavailable"""
        return """
DECISION: PENDING
CONFIDENCE: 0.5
REASONING: Unable to perform automated adjudication. Requires manual review due to complexity.
POLICY_BASIS: Standard medical necessity review required.
"""
    
    def _parse_llm_response(
        self,
        llm_response: str,
        service: Dict[str, Any],
        clinical_data: ParsedClinicalData,
        rules_results: Dict[str, Any]
    ) -> ServiceDecision:
        """Parse LLM response into ServiceDecision"""
        
        # Extract decision
        decision_text = "PENDING"
        if "APPROVE" in llm_response:
            decision_text = "APPROVE"
        elif "DENY" in llm_response:
            decision_text = "DENY"
        
        # Extract confidence
        confidence = 0.5
        try:
            for line in llm_response.split("\n"):
                if "CONFIDENCE:" in line:
                    conf_str = line.split("CONFIDENCE:")[1].strip()
                    confidence = float(conf_str.split()[0])
                    break
        except:
            pass
        
        # Extract reasoning
        reasoning = ""
        try:
            if "REASONING:" in llm_response:
                reasoning = llm_response.split("REASONING:")[1].split("POLICY_BASIS:")[0].strip()
        except:
            reasoning = "Automated adjudication based on policy guidelines"
        
        # Map decision
        if decision_text == "APPROVE":
            decision_type = DecisionType.APPROVED
        elif decision_text == "DENY":
            decision_type = DecisionType.DENIED
        else:
            decision_type = DecisionType.PENDING
        
        # Determine confidence level
        if confidence >= 0.8:
            confidence_level = ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            confidence_level = ConfidenceLevel.MEDIUM
        else:
            confidence_level = ConfidenceLevel.LOW
        
        # Create decision
        service_decision = ServiceDecision(
            service_sequence=service.get("sequence", 1),
            service_code=service.get("code", ""),
            service_description=service.get("description", ""),
            requested_amount=service.get("net_amount"),
            decision=decision_type,
            approved_amount=service.get("net_amount") if decision_type == DecisionType.APPROVED else 0,
            confidence=confidence,
            confidence_level=confidence_level,
            explanation=reasoning,
            clinical_rationale=reasoning,
            policy_reference=self._extract_policy_references(llm_response),
            rules_applied=rules_results.get("rules_triggered", []),
            requires_human_review=(decision_type == DecisionType.PENDING or confidence < 0.6),
            review_reason="Low confidence or complex case" if confidence < 0.6 else None,
            medical_necessity_met=(decision_type == DecisionType.APPROVED)
        )
        
        return service_decision
    
    def _extract_policy_references(self, llm_response: str) -> List[str]:
        """Extract policy references from LLM response"""
        refs = []
        try:
            if "POLICY_BASIS:" in llm_response:
                policy_text = llm_response.split("POLICY_BASIS:")[1].strip()
                # Simple extraction - could be more sophisticated
                refs = [policy_text[:200]]
        except:
            pass
        
        return refs
    
    def _create_auto_decisions(
        self,
        clinical_data: ParsedClinicalData,
        rules_results: Dict[str, Any]
    ) -> List[ServiceDecision]:
        """Create service decisions based on automatic rules"""
        
        auto_decision = rules_results["auto_decision"]
        confidence = rules_results.get("confidence", 0.9)
        
        decisions = []
        for service in clinical_data.services:
            
            explanation = self._get_auto_decision_explanation(rules_results)
            
            decision = ServiceDecision(
                service_sequence=service.get("sequence", 1),
                service_code=service.get("code", ""),
                service_description=service.get("description", ""),
                requested_amount=service.get("net_amount"),
                decision=auto_decision,
                approved_amount=service.get("net_amount") if auto_decision == DecisionType.APPROVED else 0,
                confidence=confidence,
                confidence_level=ConfidenceLevel.HIGH if confidence >= 0.8 else ConfidenceLevel.MEDIUM,
                explanation=explanation,
                clinical_rationale="Automatic adjudication based on policy rules",
                policy_reference=["Policy section: " + r for r in rules_results.get("rules_triggered", [])],
                rules_applied=rules_results.get("rules_triggered", []),
                requires_human_review=False,
                medical_necessity_met=(auto_decision == DecisionType.APPROVED)
            )
            
            decisions.append(decision)
        
        return decisions
    
    def _get_auto_decision_explanation(self, rules_results: Dict[str, Any]) -> str:
        """Generate explanation for automatic decision"""
        auto_decision = rules_results["auto_decision"]
        
        if auto_decision == DecisionType.APPROVED:
            return "Service approved based on policy rules: meets all coverage criteria and medical necessity requirements."
        else:
            reasons = []
            
            # Check different rule categories
            if rules_results.get("rule_results", {}).get("auto_deny", {}).get("triggered"):
                reasons.extend(rules_results["rule_results"]["auto_deny"].get("reasons", []))
            
            if reasons:
                return "Service denied: " + "; ".join(reasons)
            else:
                return "Service denied based on policy coverage rules."
    
    def _fallback_decision(
        self,
        service: Dict[str, Any],
        clinical_data: ParsedClinicalData,
        rules_results: Dict[str, Any]
    ) -> str:
        """Create fallback decision when LLM unavailable"""
        
        # Simple rule-based decision
        risk_flags = rules_results.get("risk_flags", [])
        
        if risk_flags:
            decision = "PENDING"
            reasoning = f"Requires manual review due to: {', '.join(risk_flags)}"
        else:
            # Default to approval for simple cases
            if service.get("net_amount", 0) < 5000:
                decision = "APPROVE"
                reasoning = "Low-cost service with no risk flags identified"
            else:
                decision = "PENDING"
                reasoning = "Requires medical review for cost and medical necessity"
        
        return f"""
DECISION: {decision}
CONFIDENCE: 0.5
REASONING: {reasoning}
POLICY_BASIS: Standard coverage guidelines applied
"""

# Global instance
llm_service = MedicalLLMService()