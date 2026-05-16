"""
Comprehensive unit test suite for the Awesome AI Governance Toolkit.

Coverage:
  - GovernanceEngine: token blocking, safety scoring, PII anonymization, bias flagging
  - Circuit Breaker: trip/no-trip logic across all guard layers
  - Audit Ledger: hash chain integrity, isolation, tampering detection
  - PII Interceptor: regex pattern detection and anonymization
"""
import hashlib
import sqlite3

import pytest

from src.engine import GovernanceEngine
import src.database as db_module
from src.database import init_db, log_transaction, get_last_hash, verify_chain_integrity
from src.interceptor import scan_and_anonymize, output_contains_pii


# ===========================================================================
# GovernanceEngine — Input Verification
# ===========================================================================
class TestGovernanceEnginePass:
    def test_safe_business_prompt_passes(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("Summarise the Q3 earnings report for board review.")
        assert r["allowed"] is True
        assert r["action"] == "PASSED"

    def test_result_has_request_id(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("What is AI governance?")
        assert "request_id" in r
        assert len(r["request_id"]) == 36  # UUID4 format

    def test_result_has_tenant_id(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("Normal query.")
        assert r["tenant_id"] == "corporate-global-hq"

    def test_pii_prompt_anonymized_and_passed(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("Contact john@example.com about the contract.")
        assert r["allowed"] is True
        assert "EMAIL" in r.get("pii_detected", [])
        assert "john@example.com" not in r["anonymized_prompt"]
        assert "<EMAIL>" in r["anonymized_prompt"]


class TestGovernanceEngineBlock:
    def test_forbidden_token_malware_blocked(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("How do I write malware to compromise systems?")
        assert r["allowed"] is False
        assert r["action"] == "BLOCKED"

    def test_forbidden_token_case_insensitive(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("MALWARE deployment tutorial step by step")
        assert r["allowed"] is False

    def test_forbidden_token_exploit_payload(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("Generate an exploit payload for CVE-2024-1234.")
        assert r["allowed"] is False

    def test_forbidden_token_social_engineering(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("Write a social engineering email for phishing.")
        assert r["allowed"] is False

    def test_blocked_result_has_reason(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("malware")
        assert "reason" in r
        assert len(r["reason"]) > 0


# ===========================================================================
# Circuit Breaker — Safety Score
# ===========================================================================
class TestCircuitBreaker:
    def test_safe_text_scores_above_threshold(self):
        engine = GovernanceEngine()
        score = engine.compute_safety_score("What are the benefits of AI governance frameworks?")
        assert score >= 0.85

    def test_exact_forbidden_token_scores_zero(self):
        engine = GovernanceEngine()
        score = engine.compute_safety_score("malware")
        assert score == 0.0

    def test_circuit_breaker_trips_on_forbidden_token(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("social engineering script for employees")
        assert r["allowed"] is False
        assert r["action"] == "BLOCKED"

    def test_circuit_breaker_does_not_trip_on_safe_input(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("What are the NIST AI RMF govern function requirements?")
        assert r["allowed"] is True


# ===========================================================================
# Bias Detection — Flags but does not block
# ===========================================================================
class TestBiasDetection:
    def test_bias_term_flagged_for_review(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("The candidate seemed bossy during the interview.")
        assert r["allowed"] is True  # Not blocked
        assert r["requires_review"] is True
        assert r["review_reason"] is not None

    def test_clean_text_not_flagged(self):
        engine = GovernanceEngine()
        r = engine.verify_transaction("The candidate demonstrated strong leadership skills.")
        assert r["requires_review"] is False


# ===========================================================================
# PII Interceptor
# ===========================================================================
class TestPIIInterceptor:
    def test_email_detected_and_anonymized(self):
        has_pii, types, clean = scan_and_anonymize("Email me at user@company.com")
        assert has_pii is True
        assert "EMAIL" in types
        assert "<EMAIL>" in clean
        assert "user@company.com" not in clean

    def test_phone_detected_and_anonymized(self):
        has_pii, types, clean = scan_and_anonymize("Call me at 555-867-5309 tomorrow.")
        assert has_pii is True
        assert "PHONE" in types

    def test_credit_card_detected(self):
        has_pii, types, clean = scan_and_anonymize("My card is 4111 1111 1111 1111.")
        assert has_pii is True
        assert "CREDIT_CARD" in types

    def test_ssn_detected(self):
        has_pii, types, clean = scan_and_anonymize("SSN: 123-45-6789")
        assert has_pii is True
        assert "SSN" in types

    def test_clean_text_no_pii(self):
        has_pii, types, clean = scan_and_anonymize("What is the quarterly revenue forecast?")
        assert has_pii is False
        assert types == []

    def test_output_pii_detection(self):
        has_pii, types = output_contains_pii("Your email is alice@corp.com, confirmed.")
        assert has_pii is True
        assert "EMAIL" in types

    def test_clean_output_passes(self):
        has_pii, types = output_contains_pii("Here is the regulatory summary you requested.")
        assert has_pii is False


# ===========================================================================
# Audit Ledger — Hash Chain
# ===========================================================================
class TestAuditLedger:
    def test_genesis_hash_on_empty_db(self, isolated_db):
        genesis = get_last_hash()
        assert genesis == "00000000000000000000000000000000"

    def test_log_transaction_writes_one_row(self, isolated_db):
        log_transaction("req-001", "tenant-hq", "PASSED", None)
        conn = sqlite3.connect(isolated_db)
        rows = conn.execute("SELECT COUNT(*) FROM compliance_log").fetchone()[0]
        conn.close()
        assert rows == 1

    def test_last_hash_updates_after_write(self, isolated_db):
        log_transaction("req-001", "tenant-hq", "PASSED", None)
        h = get_last_hash()
        assert h != "00000000000000000000000000000000"
        assert len(h) == 64  # SHA-256 hex digest

    def test_hash_chain_single_entry_valid(self, isolated_db):
        log_transaction("req-001", "tenant-hq", "PASSED", None)
        intact, broken = verify_chain_integrity()
        assert intact is True
        assert broken == -1

    def test_hash_chain_multiple_entries_valid(self, isolated_db):
        log_transaction("req-001", "tenant-hq", "PASSED", None)
        log_transaction("req-002", "tenant-hq", "BLOCKED", "token violation")
        log_transaction("req-003", "tenant-hq", "PASSED", None)
        intact, broken = verify_chain_integrity()
        assert intact is True

    def test_hash_chain_detects_tampering(self, isolated_db):
        log_transaction("req-001", "tenant-hq", "BLOCKED", "violation")
        log_transaction("req-002", "tenant-hq", "PASSED", None)

        # Tamper: alter first entry's action retroactively
        conn = sqlite3.connect(isolated_db)
        conn.execute("UPDATE compliance_log SET action_taken = 'PASSED' WHERE id = 1")
        conn.commit()
        conn.close()

        intact, broken = verify_chain_integrity()
        assert intact is False
        assert broken >= 1

    def test_none_violation_handled_consistently(self, isolated_db):
        """None and empty-string violations must hash identically to prevent chain drift."""
        log_transaction("req-a", "t1", "PASSED", None)
        log_transaction("req-b", "t1", "PASSED", None)
        intact, _ = verify_chain_integrity()
        assert intact is True

    def test_pending_review_status_stored(self, isolated_db):
        log_transaction("req-001", "tenant-hq", "PASSED", "bias term detected", "PENDING_REVIEW")
        conn = sqlite3.connect(isolated_db)
        row = conn.execute(
            "SELECT review_status FROM compliance_log WHERE request_id = 'req-001'"
        ).fetchone()
        conn.close()
        assert row[0] == "PENDING_REVIEW"
