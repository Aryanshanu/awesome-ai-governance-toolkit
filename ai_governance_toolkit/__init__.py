"""
Awesome AI Governance Toolkit
Runtime firewall for LLMs — policy-as-code, PII scrubbing,
SHA-256 audit chain, and HITL dashboard.

Quick start:
    from ai_governance_toolkit import Sentinel

    guard = Sentinel(policy="eu_ai_act_high_risk")
    result = guard.verify("Draft a summary of the Q3 acquisition")
    print(result.status)        # "APPROVED" or "BLOCKED"
    print(result.clean_prompt)  # PII-anonymized, safe to forward to LLM
"""
from sentinel import Sentinel, VerificationResult

__all__ = ["Sentinel", "VerificationResult"]
__version__ = "1.0.0"
