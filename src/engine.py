"""
Governance Engine — Circuit Breaker + Policy Enforcer.

Evaluation order per request:
  1. Forbidden token exact match  → BLOCKED (hard stop)
  2. Semantic safety score        → BLOCKED if score < threshold
  3. Bidirectional PII scan       → anonymize input, hard-block if output contains PII
  4. Bias lexicon scan            → PASSED but flagged PENDING_REVIEW
"""
import json
import uuid
import difflib
from src.interceptor import scan_and_anonymize, output_contains_pii


class GovernanceEngine:
    def __init__(
        self,
        policy_path: str = "config/policies/tenant_global_baseline.json",
        bias_lexicon_path: str = "config/bias_lexicon.json",
    ) -> None:
        with open(policy_path, "r") as f:
            self.policy = json.load(f)

        with open(bias_lexicon_path, "r") as f:
            raw = json.load(f)

        # Flatten all bias terms into one searchable set
        self._bias_terms: set[str] = set()
        for key, terms in raw.items():
            if key == "bias_lexicon_metadata":
                continue
            for term in terms:
                # Strip parenthetical qualifiers like " (pejorative)"
                clean = term.split(" (")[0].lower()
                self._bias_terms.add(clean)

    # ------------------------------------------------------------------
    # Safety scoring (difflib-based semantic proximity, zero-cost)
    # ------------------------------------------------------------------
    def compute_safety_score(self, text: str) -> float:
        forbidden = self.policy["security_rules"]["block_forbidden_tokens"]
        lower_text = text.lower()
        for token in forbidden:
            ratio = difflib.SequenceMatcher(None, token, lower_text).ratio()
            if ratio > 0.80:
                return 0.0
        return 1.0

    # ------------------------------------------------------------------
    # Input verification (pre-LLM)
    # ------------------------------------------------------------------
    def verify_transaction(self, prompt: str) -> dict:
        request_id = str(uuid.uuid4())
        tenant_id = self.policy["policy_metadata"]["tenant_id"]
        threshold = self.policy["security_rules"]["minimum_safety_threshold"]
        forbidden = self.policy["security_rules"]["block_forbidden_tokens"]
        hitl_triggers = self.policy["security_rules"].get("hitl_triggers", [])

        decision = {
            "request_id": request_id,
            "tenant_id": tenant_id,
            "allowed": True,
            "action": "PASSED",
            "reason": "Complies with structural governance boundaries.",
            "requires_review": False,
            "review_reason": None,
            "anonymized_prompt": prompt,
            "pii_detected": []
        }

        from src.ethics.explainability import generate_explanation

        # --- Guard 1: forbidden token exact match ---
        for token in forbidden:
            if token in prompt.lower():
                decision.update({
                    "allowed": False,
                    "action": "BLOCKED",
                    "reason": self.policy["fallbacks"]["token_violation"]
                })
                decision["explanation"] = generate_explanation(decision)
                return decision

        # --- Guard 2: semantic safety score ---
        if self.compute_safety_score(prompt) < threshold:
            decision.update({
                "allowed": False,
                "action": "BLOCKED",
                "reason": "Execution Halted: Semantic threat proximity verification failure."
            })
            decision["explanation"] = generate_explanation(decision)
            return decision

        # --- Guard 3: PII scan + anonymization ---
        has_pii, pii_types, clean_prompt = scan_and_anonymize(prompt)
        decision["anonymized_prompt"] = clean_prompt
        decision["pii_detected"] = pii_types
        if has_pii and not self.policy["security_rules"].get("enforce_pii_masking", True):
            decision.update({
                "allowed": False,
                "action": "BLOCKED",
                "reason": self.policy["fallbacks"]["pii_violation"]
            })
            decision["explanation"] = generate_explanation(decision)
            return decision

        # --- Guard 4: HITL Trigger for High-Risk Contexts ---
        for trigger in hitl_triggers:
            if trigger in prompt.lower():
                decision.update({
                    "allowed": False,
                    "action": "PENDING_HITL",
                    "requires_review": True,
                    "reason": f"High-risk context detected: '{trigger}'"
                })
                decision["explanation"] = generate_explanation(decision)
                return decision

        # --- Guard 5: RAI Fairness metrics ---
        from src.ethics.fairness_metrics import get_fairness_evaluator
        fairness = get_fairness_evaluator().evaluate_fairness(prompt)
        if not fairness["is_fair"]:
            decision.update({
                "requires_review": True,
                "review_reason": fairness["reason"]
            })

        decision["explanation"] = generate_explanation(decision)
        return decision

    # ------------------------------------------------------------------
    # Output verification (post-LLM)
    # ------------------------------------------------------------------
    def verify_output(self, response_text: str) -> dict:
        has_pii, pii_types = output_contains_pii(response_text)
        if has_pii:
            return {
                "allowed": False,
                "reason": f"Output blocked: LLM response contains raw PII ({', '.join(pii_types)}).",
            }
        return {"allowed": True, "reason": "Output clean."}
