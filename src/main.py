import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.engine import GovernanceEngine
from src.database import init_db, log_transaction

app = FastAPI(
    title="Awesome AI Governance Toolkit",
    description="Runtime firewall and cryptographic audit ledger for enterprise AI.",
    version="2026.1",
    docs_url="/docs",
    redoc_url="/redoc",
)
engine = GovernanceEngine()
init_db()


from fastapi.responses import RedirectResponse

# ---------------------------------------------------------------------------
# Root — UI Redirect
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Redirects browser traffic from the API root to the Streamlit UI."""
    return RedirectResponse(url="http://localhost:8501")


# ---------------------------------------------------------------------------
# Kill-switch state registry
# ---------------------------------------------------------------------------
def _kill_switch_active() -> bool:
    try:
        with open("config/state.json") as f:
            return json.load(f).get("kill_switch_active", False)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class PromptPayload(BaseModel):
    prompt: str


# ---------------------------------------------------------------------------
# Mock LLM endpoint (no external API key required)
# ---------------------------------------------------------------------------
@app.get("/v1/mock-llm")
async def mock_llm(prompt: str) -> dict:
    """Simulates an upstream LLM response for local development and testing."""
    return {
        "model": "mock-gpt-governance-v1",
        "response": f"[MOCK LLM] Processed input: '{prompt[:80]}...' — Response: Safe, verified, compliant.",
        "tokens_used": len(prompt.split()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Main intercept gateway
# ---------------------------------------------------------------------------
@app.post("/v1/intercept")
async def intercept_gateway(payload: PromptPayload) -> dict:
    # Kill-switch check — returns 503 without logging
    if _kill_switch_active():
        raise HTTPException(
            status_code=503,
            detail="Service Unavailable: Global kill switch is active. Contact your compliance officer.",
        )

    # --- Input verification ---
    decision = engine.verify_transaction(payload.prompt)

    review_status = "PENDING_REVIEW" if decision.get("requires_review") else "CLOSED"

    log_transaction(
        request_id=decision["request_id"],
        tenant_id=decision["tenant_id"],
        action=decision["action"],
        violation=decision["reason"] if not decision["allowed"] else decision.get("review_reason"),
        review_status=review_status,
    )

    if not decision["allowed"]:
        raise HTTPException(status_code=403, detail=decision.get("explanation", decision["reason"]))

    # --- Forward anonymized prompt to mock LLM ---
    clean_prompt = decision.get("anonymized_prompt", payload.prompt)
    mock_response = f"[MOCK LLM] Governance-verified response for: '{clean_prompt[:60]}...'"

    # --- Output verification ---
    output_check = engine.verify_output(mock_response)
    if not output_check["allowed"]:
        log_transaction(
            request_id=f"{decision['request_id']}-OUT",
            tenant_id=decision["tenant_id"],
            action="BLOCKED",
            violation=output_check["reason"],
            review_status="CLOSED",
        )
        raise HTTPException(status_code=403, detail=output_check["reason"])

    return {
        "status": "APPROVED",
        "request_id": decision["request_id"],
        "tenant_id": decision["tenant_id"],
        "forwarded_prompt": clean_prompt,
        "llm_response": mock_response,
        "pii_redacted": decision.get("pii_detected", []),
        "flagged_for_review": decision.get("requires_review", False),
        "explanation": decision.get("explanation", "Explainability Report: The request passed all checks.")
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    from src.database import verify_chain_integrity
    intact, broken_at = verify_chain_integrity()
    return {
        "status": "ok",
        "kill_switch": _kill_switch_active(),
        "ledger_integrity": "VERIFIED" if intact else f"BROKEN at row {broken_at}",
    }
