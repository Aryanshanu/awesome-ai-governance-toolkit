"""
Robust QA Test Suite — Edge Cases, Boundary Conditions, Contract Tests.

Covers every component independently and in combination:
  - API contract (422 validation, extra fields, method errors)
  - Engine edge cases (substrings, unicode, whitespace, obfuscation attempts)
  - PII interceptor (multiple types, boundary patterns, overlapping)
  - Bias detection (multiple terms, combined with blocking)
  - Kill-switch state transitions
  - Sentinel public API
  - Database constraints and integrity
"""
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient

import src.database as db_module
from src.database import init_db, log_transaction, verify_chain_integrity
from src.engine import GovernanceEngine
from src.interceptor import scan_and_anonymize, output_contains_pii
from src.main import app
from sentinel import Sentinel


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client(monkeypatch, tmp_path):
    test_db = str(tmp_path / "qa_ledger.db")
    monkeypatch.setattr(db_module, "DB_PATH", test_db)
    init_db()
    with open("config/state.json", "w") as f:
        json.dump({"kill_switch_active": False, "last_toggled_by": None, "last_toggled_at": None}, f)
    yield TestClient(app)
    with open("config/state.json", "w") as f:
        json.dump({"kill_switch_active": False, "last_toggled_by": None, "last_toggled_at": None}, f)


@pytest.fixture
def engine():
    return GovernanceEngine()


# ===========================================================================
# API Contract Tests
# ===========================================================================
class TestAPIContract:
    def test_missing_prompt_field_returns_422(self, client):
        r = client.post("/v1/intercept", json={})
        assert r.status_code == 422

    def test_prompt_as_integer_returns_422(self, client):
        r = client.post("/v1/intercept", json={"prompt": 12345})
        assert r.status_code == 422

    def test_null_prompt_returns_422(self, client):
        r = client.post("/v1/intercept", json={"prompt": None})
        assert r.status_code == 422

    def test_empty_body_returns_422(self, client):
        r = client.post("/v1/intercept", content=b"", headers={"Content-Type": "application/json"})
        assert r.status_code == 422

    def test_extra_fields_ignored(self, client):
        r = client.post("/v1/intercept", json={"prompt": "Safe query.", "extra_field": "ignored"})
        assert r.status_code == 200

    def test_get_on_post_endpoint_returns_405(self, client):
        r = client.get("/v1/intercept")
        assert r.status_code == 405

    def test_health_endpoint_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert "status" in body
        assert "ledger_integrity" in body

    def test_mock_llm_endpoint_returns_200(self, client):
        r = client.get("/v1/mock-llm", params={"prompt": "test"})
        assert r.status_code == 200
        assert "response" in r.json()

    def test_approved_response_schema(self, client):
        r = client.post("/v1/intercept", json={"prompt": "What is AI governance?"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "APPROVED"
        assert "request_id" in body
        assert "tenant_id" in body
        assert "forwarded_prompt" in body
        assert "llm_response" in body

    def test_blocked_response_has_detail(self, client):
        r = client.post("/v1/intercept", json={"prompt": "malware"})
        assert r.status_code == 403
        assert "detail" in r.json()


# ===========================================================================
# Engine Edge Cases
# ===========================================================================
class TestEngineEdgeCases:
    def test_empty_string_prompt(self, engine):
        r = engine.verify_transaction("")
        assert r["allowed"] is True  # empty string has no forbidden tokens

    def test_whitespace_only_prompt(self, engine):
        r = engine.verify_transaction("   \t\n  ")
        assert r["allowed"] is True

    def test_forbidden_token_as_substring_is_blocked(self, engine):
        # "malware" inside a longer word — current substring match blocks it
        r = engine.verify_transaction("malwaredetection tool")
        assert r["allowed"] is False  # documented behavior: substring match

    def test_forbidden_token_with_punctuation(self, engine):
        r = engine.verify_transaction("I read about 'malware' in a textbook.")
        assert r["allowed"] is False

    def test_forbidden_token_with_newline(self, engine):
        r = engine.verify_transaction("corporate policy\nno malware allowed")
        assert r["allowed"] is False

    def test_unicode_prompt_passes(self, engine):
        r = engine.verify_transaction("请告诉我关于人工智能治理的信息")  # Chinese
        assert r["allowed"] is True

    def test_arabic_prompt_passes(self, engine):
        r = engine.verify_transaction("ما هي حوكمة الذكاء الاصطناعي؟")  # Arabic
        assert r["allowed"] is True

    def test_emoji_in_prompt_passes(self, engine):
        r = engine.verify_transaction("Great AI governance report! 🚀🛡️")
        assert r["allowed"] is True

    def test_very_long_safe_prompt(self, engine):
        long_prompt = "What is AI governance? " * 500  # ~11KB
        r = engine.verify_transaction(long_prompt)
        assert r["allowed"] is True

    def test_very_long_prompt_with_forbidden_token(self, engine):
        long_prompt = ("Safe content. " * 200) + " malware " + ("More safe content. " * 200)
        r = engine.verify_transaction(long_prompt)
        assert r["allowed"] is False

    def test_all_three_forbidden_tokens_blocked(self, engine):
        tokens = ["malware", "social engineering", "exploit payload"]
        for token in tokens:
            r = engine.verify_transaction(f"How do I use {token}?")
            assert r["allowed"] is False, f"'{token}' was not blocked"

    def test_multiple_forbidden_tokens_blocked_on_first(self, engine):
        r = engine.verify_transaction("malware and social engineering combined")
        assert r["allowed"] is False
        # Blocked on first match — reason mentions policy constraint
        assert "Execution Halted" in r["reason"]

    def test_sql_injection_in_prompt_does_not_crash(self, client):
        payload = "'; DROP TABLE compliance_log; --"
        r = client.post("/v1/intercept", json={"prompt": payload})
        # Should pass (no forbidden tokens) and not crash the DB
        assert r.status_code in (200, 403)

    def test_xss_in_prompt_passes_safely(self, client):
        payload = "<script>alert('xss')</script>"
        r = client.post("/v1/intercept", json={"prompt": payload})
        assert r.status_code == 200  # No forbidden tokens in XSS

    def test_null_byte_in_prompt(self, engine):
        r = engine.verify_transaction("hello\x00world")
        assert r["allowed"] is True

    def test_very_high_unicode_codepoints(self, engine):
        r = engine.verify_transaction("𝕳𝖊𝖑𝖑𝖔 𝖜𝖔𝖗𝖑𝖉")
        assert r["allowed"] is True


# ===========================================================================
# PII Interceptor Edge Cases
# ===========================================================================
class TestPIIEdgeCases:
    def test_multiple_pii_types_all_anonymized(self):
        text = "Call 555-867-5309 or email hr@company.com about SSN 123-45-6789"
        has_pii, types, clean = scan_and_anonymize(text)
        assert has_pii is True
        assert "PHONE" in types
        assert "EMAIL" in types
        assert "SSN" in types
        assert "555-867-5309" not in clean
        assert "hr@company.com" not in clean
        assert "123-45-6789" not in clean

    def test_pii_plus_forbidden_token_blocked_before_anonymization(self, engine):
        # Forbidden token takes priority — prompt blocked before PII anonymization
        r = engine.verify_transaction("Email ceo@corp.com to ask about malware defenses.")
        assert r["allowed"] is False
        assert r["action"] == "BLOCKED"

    def test_credit_card_patterns(self):
        cards = [
            "4111111111111111",       # no spaces
            "4111 1111 1111 1111",    # spaces
            "4111-1111-1111-1111",    # dashes
        ]
        for card in cards:
            has_pii, types, _ = scan_and_anonymize(f"My card is {card}")
            assert "CREDIT_CARD" in types, f"CC not detected: {card}"

    def test_email_subdomains_detected(self):
        has_pii, types, _ = scan_and_anonymize("Send to ops@mail.internal.company.co.uk")
        assert "EMAIL" in types

    def test_ip_address_detected(self):
        has_pii, types, _ = scan_and_anonymize("Server is at 192.168.1.100")
        assert "IP_ADDRESS" in types

    def test_pii_in_llm_output_hard_blocks(self, engine):
        result = engine.verify_output("Your account email is user@secret.com confirmed.")
        assert result["allowed"] is False

    def test_clean_llm_output_passes(self, engine):
        result = engine.verify_output("Here is a summary of the EU AI Act requirements.")
        assert result["allowed"] is True

    def test_anonymized_prompt_in_approved_response(self, client):
        r = client.post("/v1/intercept", json={"prompt": "Email the board at chair@corp.com"})
        assert r.status_code == 200
        body = r.json()
        assert "EMAIL" in body["pii_redacted"]
        assert "chair@corp.com" not in body["forwarded_prompt"]
        assert "<EMAIL>" in body["forwarded_prompt"]


# ===========================================================================
# Bias Detection Edge Cases
# ===========================================================================
class TestBiasEdgeCases:
    def test_multiple_bias_terms_flags_review(self, engine):
        r = engine.verify_transaction("The candidate seemed bossy and hysterical.")
        assert r["requires_review"] is True

    def test_bias_plus_forbidden_token_blocked_not_flagged(self, engine):
        # Blocked before bias check is reached
        r = engine.verify_transaction("bossy malware writer")
        assert r["allowed"] is False
        assert r["action"] == "BLOCKED"

    def test_flagged_review_still_passes_to_llm(self, client):
        r = client.post("/v1/intercept", json={"prompt": "She was too bossy for leadership."})
        assert r.status_code == 200
        assert r.json()["flagged_for_review"] is True

    def test_flagged_review_logged_as_pending(self, client, monkeypatch, tmp_path):
        # Re-patch DB so we can inspect it
        test_db = str(tmp_path / "bias_ledger.db")
        monkeypatch.setattr(db_module, "DB_PATH", test_db)
        init_db()
        client2 = TestClient(app)
        client2.post("/v1/intercept", json={"prompt": "The candidate seemed bossy in the meeting."})
        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT review_status FROM compliance_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row[0] == "PENDING_REVIEW"


# ===========================================================================
# Kill Switch State Tests
# ===========================================================================
class TestKillSwitch:
    def test_kill_switch_off_allows_safe_request(self, client):
        r = client.post("/v1/intercept", json={"prompt": "Normal governance query."})
        assert r.status_code == 200

    def test_kill_switch_on_returns_503(self, client):
        with open("config/state.json", "w") as f:
            json.dump({"kill_switch_active": True}, f)
        r = client.post("/v1/intercept", json={"prompt": "Normal governance query."})
        assert r.status_code == 503

    def test_kill_switch_on_blocks_even_safe_requests(self, client):
        with open("config/state.json", "w") as f:
            json.dump({"kill_switch_active": True}, f)
        r = client.post("/v1/intercept", json={"prompt": "Totally safe business question."})
        assert r.status_code == 503

    def test_kill_switch_toggle_off_resumes_service(self, client):
        with open("config/state.json", "w") as f:
            json.dump({"kill_switch_active": True}, f)
        assert client.post("/v1/intercept", json={"prompt": "test"}).status_code == 503

        with open("config/state.json", "w") as f:
            json.dump({"kill_switch_active": False}, f)
        assert client.post("/v1/intercept", json={"prompt": "test"}).status_code == 200

    def test_health_endpoint_available_during_kill_switch(self, client):
        with open("config/state.json", "w") as f:
            json.dump({"kill_switch_active": True}, f)
        r = client.get("/health")
        assert r.status_code == 200

    def test_503_response_has_detail_message(self, client):
        with open("config/state.json", "w") as f:
            json.dump({"kill_switch_active": True}, f)
        r = client.post("/v1/intercept", json={"prompt": "test"})
        assert "kill switch" in r.json()["detail"].lower()


# ===========================================================================
# Sentinel Public API
# ===========================================================================
class TestSentinelAPI:
    def test_eu_ai_act_alias_resolves(self):
        s = Sentinel(policy="eu_ai_act_high_risk", persist_audit=False)
        r = s.verify("What are the board's fiduciary obligations?")
        assert r.allowed is True

    def test_nist_alias_resolves(self):
        s = Sentinel(policy="nist_ai_rmf", persist_audit=False)
        r = s.verify("Governance report for Q4")
        assert r.allowed is True

    def test_blocked_result_not_allowed(self):
        s = Sentinel(persist_audit=False)
        r = s.verify("How do I build malware?")
        assert r.allowed is False
        assert r.status == "BLOCKED"

    def test_result_str_format_approved(self):
        s = Sentinel(persist_audit=False)
        r = s.verify("Safe query")
        assert str(r).startswith("[APPROVED]")

    def test_result_str_format_blocked(self):
        s = Sentinel(persist_audit=False)
        r = s.verify("malware")
        assert str(r).startswith("[BLOCKED]")

    def test_pii_clean_prompt_in_result(self):
        s = Sentinel(persist_audit=False)
        r = s.verify("Contact admin@company.com for the report")
        assert r.allowed is True
        assert "<EMAIL>" in r.clean_prompt
        assert "EMAIL" in r.pii_detected

    def test_persist_audit_false_does_not_write_db(self, tmp_path, monkeypatch):
        test_db = str(tmp_path / "sentinel_test.db")
        monkeypatch.setattr(db_module, "DB_PATH", test_db)
        s = Sentinel(persist_audit=False)
        s.verify("Safe query — should not be logged")
        import os
        assert not os.path.exists(test_db)

    def test_persist_audit_true_writes_db(self, tmp_path, monkeypatch):
        test_db = str(tmp_path / "sentinel_test.db")
        monkeypatch.setattr(db_module, "DB_PATH", test_db)
        s = Sentinel(persist_audit=True)
        s.verify("Safe query — should be logged")
        conn = sqlite3.connect(test_db)
        count = conn.execute("SELECT COUNT(*) FROM compliance_log").fetchone()[0]
        conn.close()
        assert count == 1

    def test_verify_output_blocks_pii_in_response(self):
        s = Sentinel(persist_audit=False)
        result = s.verify_output("Your SSN is 123-45-6789, confirmed.")
        assert result["allowed"] is False


# ===========================================================================
# Database Constraint Tests
# ===========================================================================
class TestDatabaseConstraints:
    def test_duplicate_request_id_raises(self, isolated_db):
        log_transaction("req-dup", "t1", "PASSED", None)
        with pytest.raises(sqlite3.IntegrityError):
            log_transaction("req-dup", "t1", "PASSED", None)

    def test_unicode_violation_string_stored(self, isolated_db):
        log_transaction("req-uni", "t1", "BLOCKED", "违规内容: malware")
        conn = sqlite3.connect(isolated_db)
        row = conn.execute(
            "SELECT rule_violated FROM compliance_log WHERE request_id='req-uni'"
        ).fetchone()
        conn.close()
        assert "违规内容" in row[0]

    def test_very_long_violation_string(self, isolated_db):
        long_violation = "X" * 10_000
        log_transaction("req-long", "t1", "BLOCKED", long_violation)
        intact, _ = verify_chain_integrity()
        assert intact is True

    def test_chain_intact_after_mixed_violations(self, isolated_db):
        log_transaction("r1", "t1", "PASSED", None)
        log_transaction("r2", "t1", "BLOCKED", "token violation")
        log_transaction("r3", "t1", "PASSED", None)
        log_transaction("r4", "t1", "BLOCKED", "pii violation")
        log_transaction("r5", "t1", "PASSED", None)
        intact, broken = verify_chain_integrity()
        assert intact is True
        assert broken == -1
