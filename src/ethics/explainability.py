def generate_explanation(decision: dict) -> str:
    """
    Generates a human-readable explainability report for the circuit breaker decision.
    This fulfills the RAI 'Transparency and Explainability' principle.
    """
    action = decision.get("action", "PASSED")
    reason = decision.get("reason", "No reason provided.")
    review_reason = decision.get("review_reason")
    
    if action == "BLOCKED":
        explanation = f"Explainability Report: The request was halted by the runtime firewall. Reason: {reason}"
        if decision.get("pii_detected"):
            explanation += f" The system scrubbed the following identifiers before halting: {', '.join(decision['pii_detected'])}."
        return explanation
        
    if action == "PENDING_HITL":
        return f"Explainability Report: The request triggered a Human-in-the-Loop (HITL) pause. It matched high-risk contexts. Human authorization is required to proceed. Context: {reason}"
        
    if decision.get("requires_review"):
        return f"Explainability Report: The request passed but was flagged for human review. {review_reason or reason}"
        
    return "Explainability Report: The request passed all safety, privacy, and fairness checks."
