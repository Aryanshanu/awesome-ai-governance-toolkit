"""
Sentinel — Top-level public interface for the Awesome AI Governance Toolkit.

Quick start:
    from sentinel import Sentinel

    guard = Sentinel(policy="eu_ai_act_high_risk")
    result = guard.verify("What is the quarterly revenue?")
    print(result.status)        # "APPROVED" or "BLOCKED"
    print(result.clean_prompt)  # PII-anonymized version
"""
from dataclasses import dataclass, field
from src.engine import GovernanceEngine
from src.database import init_db, log_transaction

# Policy alias → config file mapping
_POLICY_ALIASES: dict[str, str] = {
    "eu_ai_act_high_risk":  "config/policies/tenant_global_baseline.json",
    "nist_ai_rmf":          "config/policies/tenant_global_baseline.json",
    "global_baseline":      "config/policies/tenant_global_baseline.json",
}


@dataclass
class VerificationResult:
    status: str                        # "APPROVED" or "BLOCKED"
    request_id: str
    tenant_id: str
    reason: str
    clean_prompt: str
    pii_detected: list[str] = field(default_factory=list)
    flagged_for_review: bool = False
    review_reason: str | None = None

    @property
    def allowed(self) -> bool:
        return self.status == "APPROVED"

    def __str__(self) -> str:
        tag = "[APPROVED]" if self.allowed else "[BLOCKED]"
        review = f" | PENDING_REVIEW: {self.review_reason}" if self.flagged_for_review else ""
        return f"{tag} {self.reason}{review}"


class Sentinel:
    """
    Runtime firewall for enterprise AI deployments.

    Parameters
    ----------
    policy : str
        Policy alias or direct path to a policy JSON file.
        Built-in aliases: "eu_ai_act_high_risk", "nist_ai_rmf", "global_baseline".
    persist_audit : bool
        Write every verification result to the cryptographic audit ledger.
        Defaults to True.
    """

    def __init__(
        self,
        policy: str = "global_baseline",
        persist_audit: bool = True,
    ) -> None:
        policy_path = _POLICY_ALIASES.get(policy, policy)
        self._engine = GovernanceEngine(policy_path=policy_path)
        self._persist = persist_audit
        if persist_audit:
            init_db()

    def verify(self, prompt: str) -> VerificationResult:
        """
        Verify an input prompt against the active governance policy.

        Runs all four guard layers:
          1. Forbidden token exact match
          2. Semantic safety score
          3. Bidirectional PII anonymization
          4. Bias lexicon detection (flags, does not block)

        Returns a VerificationResult with status, cleaned prompt, and audit metadata.
        """
        decision = self._engine.verify_transaction(prompt)

        status = "APPROVED" if decision["allowed"] else "BLOCKED"
        review_status = "PENDING_REVIEW" if decision.get("requires_review") else "CLOSED"

        if self._persist:
            log_transaction(
                request_id=decision["request_id"],
                tenant_id=decision["tenant_id"],
                action=decision["action"],
                violation=decision["reason"] if not decision["allowed"] else decision.get("review_reason"),
                review_status=review_status,
            )

        return VerificationResult(
            status=status,
            request_id=decision["request_id"],
            tenant_id=decision["tenant_id"],
            reason=decision["reason"],
            clean_prompt=decision.get("anonymized_prompt", prompt),
            pii_detected=decision.get("pii_detected", []),
            flagged_for_review=decision.get("requires_review", False),
            review_reason=decision.get("review_reason"),
        )

    def verify_output(self, llm_response: str) -> dict:
        """Check a raw LLM output for PII before returning it to the end user."""
        return self._engine.verify_output(llm_response)
