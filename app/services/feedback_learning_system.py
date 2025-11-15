"""
Feedback Learning System
"""
from typing import Dict, Any, List
from datetime import datetime
from loguru import logger

class FeedbackLearningSystem:
    def __init__(self):
        self.feedback_history = []
        self.accuracy_stats = {"correct": 0, "incorrect": 0}
        logger.info("✓ Feedback Learning System initialized")
    
    def record_feedback(self, request_id: str, ai_decision: Dict, 
                       human_decision: Dict, human_rationale: str = "") -> Dict[str, Any]:
        
        feedback = {
            "request_id": request_id,
            "ai_decision": ai_decision.get("decision"),
            "human_decision": human_decision.get("decision"),
            "rationale": human_rationale,
            "timestamp": datetime.utcnow().isoformat(),
            "agreement": ai_decision.get("decision") == human_decision.get("decision")
        }
        
        self.feedback_history.append(feedback)
        
        if feedback["agreement"]:
            self.accuracy_stats["correct"] += 1
        else:
            self.accuracy_stats["incorrect"] += 1
        
        logger.info(f"Feedback recorded: AI={feedback['ai_decision']}, Human={feedback['human_decision']}, "
                   f"Agreement={feedback['agreement']}")
        
        return {
            "recorded": True,
            "agreement": feedback["agreement"],
            "total_feedback": len(self.feedback_history)
        }
    
    def get_accuracy(self) -> float:
        total = self.accuracy_stats["correct"] + self.accuracy_stats["incorrect"]
        if total == 0:
            return 0.0
        return self.accuracy_stats["correct"] / total
    
    def get_insights(self) -> Dict[str, Any]:
        accuracy = self.get_accuracy()
        
        # Analyze disagreement patterns
        disagreements = [f for f in self.feedback_history if not f["agreement"]]
        
        return {
            "total_feedback": len(self.feedback_history),
            "accuracy": accuracy,
            "correct_decisions": self.accuracy_stats["correct"],
            "incorrect_decisions": self.accuracy_stats["incorrect"],
            "recent_disagreements": len([f for f in self.feedback_history[-20:] if not f["agreement"]]),
            "recommendations": self._generate_recommendations(disagreements)
        }
    
    def _generate_recommendations(self, disagreements: List[Dict]) -> List[str]:
        recommendations = []
        
        if len(disagreements) > 5:
            recommendations.append("Review confidence thresholds - high disagreement rate")
        
        if len(self.feedback_history) > 100 and self.get_accuracy() < 0.75:
            recommendations.append("Consider model retraining or policy updates")
        
        return recommendations

feedback_learning_system = FeedbackLearningSystem()
