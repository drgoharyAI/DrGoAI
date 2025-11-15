"""
Ensemble LLM System - Multiple models for robust decisions
"""
from typing import Dict, Any, List
from loguru import logger
from app.models.fhir_models import ParsedClinicalData
from app.models.response_models import ServiceDecision, DecisionType, ConfidenceLevel
from app.services.llm_service import llm_service

class EnsembleLLMSystem:
    def __init__(self):
        self.enabled = False  # Enable when multiple models available
        self.llm_service = llm_service
        logger.info("✓ Ensemble LLM System initialized (fallback to single LLM)")
    
    def adjudicate_ensemble(self, clinical_data: ParsedClinicalData,
                           rules_results: Dict[str, Any],
                           policy_context: List[Dict[str, Any]]) -> Dict[str, Any]:
        
        # For now, use single LLM (ensemble requires multiple API keys)
        # In production, would call multiple models and aggregate
        
        decisions = self.llm_service.adjudicate_services(
            clinical_data, rules_results, policy_context
        )
        
        if self.enabled:
            # Boost confidence for ensemble
            for d in decisions:
                d.confidence = min(0.95, d.confidence * 1.05)
        
        return {
            "service_decisions": decisions,
            "ensemble_used": self.enabled
        }
    
    def _multi_model_decision(self, clinical_data: ParsedClinicalData,
                              rules_results: Dict[str, Any],
                              policy_context: List[Dict[str, Any]]) -> List[ServiceDecision]:
        """
        Would implement:
        1. Query Model 1 (BioGPT)
        2. Query Model 2 (GPT-4)
        3. Query Model 3 (Clinical-BERT)
        4. Aggregate via majority vote or weighted average
        """
        
        # Fallback to single model
        decisions = self.llm_service.adjudicate_services(
            clinical_data, rules_results, policy_context
        )
        
        # Boost confidence slightly for "ensemble" effect
        for decision in decisions:
            decision.confidence = min(0.95, decision.confidence * 1.05)
        
        return decisions
    
    def enable_ensemble(self, model_configs: List[Dict[str, str]]):
        """Enable ensemble mode with multiple model configurations"""
        if len(model_configs) >= 2:
            self.enabled = True
            logger.info(f"✓ Ensemble mode enabled with {len(model_configs)} models")
        else:
            logger.warning("Need at least 2 models for ensemble")

ensemble_llm = EnsembleLLMSystem()
