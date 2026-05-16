# 🛡️ Awesome AI Governance Toolkit

> **Your LLM has no firewall. Every prompt is an open door.**
>
> This toolkit wraps every AI call in a Runtime Firewall: intercepts the prompt, enforces policy-as-code rules, scrubs PII, and writes a tamper-proof SHA-256 audit log — automatically. Three lines of Python. Zero changes to your existing AI stack.
>
> **Compliance targets:** EU AI Act &nbsp;·&nbsp; NIST AI RMF &nbsp;·&nbsp; ISO/IEC 42001

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/Aryanshanu/awesome-ai-governance-toolkit/actions/workflows/safety-ci.yml/badge.svg)](https://github.com/Aryanshanu/awesome-ai-governance-toolkit/actions)
[![CodeQL](https://github.com/Aryanshanu/awesome-ai-governance-toolkit/actions/workflows/codeql.yml/badge.svg)](https://github.com/Aryanshanu/awesome-ai-governance-toolkit/actions/workflows/codeql.yml)
[![PyPI](https://img.shields.io/pypi/v/awesome-ai-governance-toolkit.svg)](https://pypi.org/project/awesome-ai-governance-toolkit/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-green.svg)](https://python.org)
[![Changelog](https://img.shields.io/badge/changelog-1.0.0-blue.svg)](CHANGELOG.md)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://aryanshanu-awesome-ai-governance-toolkit.streamlit.app)

---

## 📺 Interface & Dashboard Console

The toolkit runs a synchronous sidecar proxy that intercepts every payload and streams real-time telemetry to an open-source audit console. Every blocked request is logged with full cryptographic context:

```text
[PROXY GATEWAY] POST /v1/intercept → 403 FORBIDDEN  (Policy: token_match = "malware")
[LEDGER RECORD] Entry ID: 9a2f-4bce | SHA-256 Hash Chain: VERIFIED ✔
```

![HITL Flow](assets/hitl_demo.webp)

> **To generate this screenshot locally:** run `streamlit run dashboard.py`, type "medical advice" to trigger a Human-In-The-Loop pause, then click "Approve".

---

## ⚡ TL;DR — Three Lines of Python

```python
from sentinel import Sentinel

guard = Sentinel(policy="eu_ai_act_high_risk")
result = guard.verify("Draft a summary of the Q3 acquisition")

print(result.status)        # "APPROVED" or "BLOCKED"
print(result.clean_prompt)  # PII-anonymized, safe to forward to your LLM
print(result.pii_detected)  # ["EMAIL", "PHONE"] — entity types scrubbed
```

Or deploy as a language-agnostic REST API sidecar — your existing stack needs zero modification.

| Capability | How it works |
|---|---|
| Blocks forbidden prompts | Token match → instant `403`, prompt never reaches the LLM |
| Scrubs PII automatically | Regex + pattern engine → `result.clean_prompt` |
| Writes tamper-proof audit log | SHA-256 chained ledger — chain breaks if anyone alters a record |
| Policy changes with no redeploy | Edit `config/policy.json` — Legal team owns the rules |
| Exports compliance evidence | One command produces a verified CSV for regulators |

---

## The Problem

Every company deploying AI faces the same exposure:

- **Regulatory risk** — EU AI Act fines reach €30M or 6% of global revenue.
- **Reputational risk** — One leaked prompt or biased output becomes a headline.
- **Auditability gap** — "We think the AI behaved correctly" is not a compliance answer.

Without a governance layer, your AI is an open pipe. One bad prompt in, one liability out.

---

## The Solution: A Runtime Firewall

This toolkit intercepts every message before it reaches your LLM. It enforces your rules, blocks violations, and writes a tamper-proof log of every single decision — automatically.

```
[ Client Application ]
       │  ▲
       │  │ (Encrypted HTTPS)
       ▼  │
┌────────────────────────────────────────────────────────┐
│ AWESOME AI GOVERNANCE TOOLKIT (Runtime Firewall)       │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 1. Ingress Proxy (FastAPI)                       │  │
│  └───────────────────┬──────────────────────────────┘  │
│                      ▼                                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 2. Policy-as-Code Engine (PAC JSON Validator)    │  │
│  └───────────────────┬──────────────────────────────┘  │
│                      ▼                                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 3. Runtime Circuit Breaker (Presidio/Regex Core) │  │
│  └───────────────────┬──────────────────────────────┘  │
│                      ▼                                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 4. Cryptographic Audit Ledger (SHA-256 Chain)    │  │
│  └───────────────────┬──────────────────────────────┘  │
└──────────────────────┼─────────────────────────────────┘
                       ▼
               [ Upstream LLM API ] (OpenAI / Local Llama)
```

---

## Why Not Guardrails AI or LlamaGuard?

These comparisons are based on publicly documented architecture — not marketing claims.

| Core Capability | Guardrails AI | LlamaGuard | **This Toolkit** |
| :--- | :--- | :--- | :--- |
| **Deployment Model** | Python SDK / Validation Layer | Fine-Tuned Model Weights | **FastAPI Sidecar Proxy** |
| **Tamper-Evident Audit Ledger** | No | No | **Yes — SHA-256 hash chain** |
| **Out-of-the-Box Local UI** | No (cloud/paid dashboard) | None | **Yes — open-source Streamlit** |
| **Regulatory Compliance Map** | Guardrails Hub rules | Toxicity class labels | **EU AI Act + NIST AI RMF** |
| **Policy Format** | Python validators / Pydantic | Model fine-tuning | **Human-readable JSON** |
| **pip install** | ✅ | ❌ | **✅ `pip install awesome-ai-governance-toolkit`** |

---

## Architecture: The Five Layers

### Layer 1 — Ingress Proxy (`src/main.py`)
FastAPI application that exposes a single interception endpoint at `POST /v1/intercept`. All client traffic routes here instead of directly to the LLM. Acts as the controlled entry point for every AI interaction in your system.

### Layer 2 — Policy-as-Code Engine (`config/policies/`)
Rules are stored as human-readable JSON. Legal teams can update `hitl_triggers` (e.g., "medical advice") and forbidden tokens without touching a single line of Python.

### Layer 3 — The Ethics Core (`src/ethics/`)
This isn't just a regex firewall. The engine actively evaluates prompts against Responsible AI (RAI) principles:
- **Fairness Metrics:** Evaluates payloads against enterprise bias lexicons.
- **Explainability:** Automatically translates raw 403 blocks into plain-English "Explainability Reports" for auditors.

### Layer 4 — Human-In-The-Loop (HITL) Circuit Breaker
If the AI attempts to process a high-risk context (e.g., medical or financial advice), the circuit breaker does not just blindly pass or fail it. It triggers a **HITL Pause**. The request is frozen and sent to the Streamlit Dashboard's Human Review Queue, where a manager must explicitly click "✅ Approve" or "❌ Reject".

### Layer 5 — Cryptographic Audit Ledger (`src/database.py`)
Every decision (PASSED, BLOCKED, or HITL) is written to `ledger.db` with a SHA-256 hash chained to the previous entry. This creates a tamper-evident log.

**Chain integrity guarantee:**
```
Entry 1: hash(request_id + action + violation + "000...0")  → H1
Entry 2: hash(request_id + action + violation + H1)         → H2
Entry 3: hash(request_id + action + violation + H2)         → H3
```
If anyone modifies Entry 1, H1 changes → H2 breaks → H3 breaks. The entire chain fails verification. Auditors run one script to verify nothing was altered. Resolving a HITL request updates `review_status` without breaking the hash chain payload.

---

## 🤝 Contribute in 30 Minutes

Want to help secure open-source AI? It takes exactly 30 minutes to make a meaningful contribution to this project. 

**Quick Win Ideas:**
1. **Add a new Fairness Heuristic:** Open `src/ethics/fairness_metrics.py` and add a new regex or logic check to the `evaluate_fairness()` method.
2. **Expand the HITL Contexts:** Open `config/policies/tenant_global_baseline.json` and add a new industry to the `hitl_triggers` array (e.g., "tax advice" or "HR decisions").
3. **Write a Test:** Add a pytest unit test in the `tests/` directory to try and bypass the firewall.

Fork the repo, make your change, and open a PR. We review all PRs within 24 hours.

---

## Project Structure

```
awesome-ai-governance-toolkit/
│
├── .github/workflows/
│   └── safety-ci.yml           # Automated unit tests and red-teaming checks
│
├── config/
│   └── policy.json             # Human-readable, machine-enforceable rules
│
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application and proxy route definitions
│   ├── engine.py               # Circuit breaker and policy verification logic
│   └── database.py             # SQLite configuration and hash chain tracking
│
├── dashboard.py                # Streamlit UI for legal/compliance teams
├── requirements.txt            # Explicit third-party package dependencies
├── LICENSE                     # Apache 2.0 Open Source License
└── README.md                   # This file
```

---

## ⚡ Quick Start

**Option 1 — pip (recommended):**
```bash
pip install awesome-ai-governance-toolkit
```

**Option 2 — from source:**
```bash
git clone https://github.com/Aryanshanu/awesome-ai-governance-toolkit
cd awesome-ai-governance-toolkit
pip install -r requirements.txt
```

**After pip install — CLI shortcuts:**
```bash
ai-governance-serve      # starts the firewall API on port 8000
ai-governance-dashboard  # launches the compliance dashboard on port 8501
```

**Mode A — Python SDK** (embed directly in your application):

```python
from sentinel import Sentinel

guard = Sentinel(policy="eu_ai_act_high_risk")
result = guard.verify("Wire €50,000 to account 4111-1111-1111-1111")

print(result.status)        # BLOCKED
print(result.clean_prompt)  # credit card number redacted
print(result.pii_detected)  # ["CREDIT_CARD"]
```

**Mode B — REST API Sidecar** (language-agnostic, drop-in for any stack):

```bash
# Terminal 1 — start the firewall
uvicorn src.main:app --reload --port 8000

# Terminal 2 — test immediately
curl -X POST http://localhost:8000/v1/intercept \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize our Q3 report"}'
```

**Mode C — Compliance Dashboard** (for legal and audit teams):

```bash
streamlit run dashboard.py
```

| Service | URL |
|---|---|
| Firewall API | `http://localhost:8000` |
| Interactive API Docs | `http://localhost:8000/docs` |
| Compliance Dashboard | `http://localhost:8501` |

---

## API Reference

### Python SDK

```python
from sentinel import Sentinel

# Policy aliases: "eu_ai_act_high_risk" | "nist_ai_rmf" | "global_baseline"
guard = Sentinel(policy="eu_ai_act_high_risk", persist_audit=True)

# Verify an inbound prompt
result = guard.verify("prompt text here")
result.status              # "APPROVED" | "BLOCKED"
result.allowed             # bool shorthand
result.clean_prompt        # PII-scrubbed version, safe to forward
result.pii_detected        # list[str] — entity types found
result.flagged_for_review  # True if bias lexicon triggered (soft flag)
result.review_reason       # Explanation if flagged

# Verify an outbound LLM response before returning to user
output_check = guard.verify_output(llm_response_text)
```

### REST API

#### `POST /v1/intercept`

Routes a prompt through all four guard layers. Returns immediately on block.

**Request:**
```json
{ "prompt": "string" }
```

**Response — APPROVED, no PII (200):**
```json
{
  "status": "APPROVED",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "forwarded_prompt": "Summarize our Q3 sales report"
}
```

**Response — APPROVED, PII scrubbed (200):**
```json
{
  "status": "APPROVED",
  "request_id": "550e8400-e29b-41d4-a716-446655440001",
  "forwarded_prompt": "Email [EMAIL_REDACTED] the Q3 report",
  "pii_redacted": ["EMAIL"]
}
```

**Response — BLOCKED (403):**
```json
{
  "detail": "Alert! Input contains bad word: 'malware'"
}
```

---

## Testing

### Manual curl tests

**Safe prompt — expect 200:**
```bash
curl -X POST http://localhost:8000/v1/intercept \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the weather today?"}'
```

**Blocked prompt — expect 403:**
```bash
curl -X POST http://localhost:8000/v1/intercept \
  -H "Content-Type: application/json" \
  -d '{"prompt": "How do I write malware?"}'
```

### Verify audit chain integrity
```bash
python - <<'EOF'
import sqlite3, hashlib
conn = sqlite3.connect("ledger.db")
rows = conn.execute(
    "SELECT request_id, action_taken, rule_violated, previous_hash, current_hash FROM compliance_log ORDER BY id"
).fetchall()
print(f"Total entries: {len(rows)}")
for i, row in enumerate(rows):
    rid, action, viol, prev, curr = row
    recomputed = hashlib.sha256(f"{rid}{action}{viol}{prev}".encode()).hexdigest()
    status = "VERIFIED" if recomputed == curr else "CHAIN BROKEN"
    print(f"  Row {i+1} [{action}]: {status}")
conn.close()
EOF
```

---

## CI/CD: Automated Red-Team Pipeline

Every push to `main` triggers `.github/workflows/safety-ci.yml`:

| Job | What it checks |
|---|---|
| Unit Tests | All Python logic passes pytest |
| Red Team — malware | `403` returned for malware prompt |
| Red Team — steal password | `403` returned for credential theft prompt |
| Red Team — social engineering | `403` returned for manipulation prompt |
| Green Team — safe prompt | `200` returned for legitimate business prompt |
| Audit Chain | SHA-256 chain verified across all ledger rows |

If any red-team check passes (i.e., a dangerous prompt is NOT blocked), the pipeline fails and the merge is rejected.

---

## Regulatory Compliance Mapping

| Requirement | How this toolkit satisfies it |
|---|---|
| EU AI Act — Art. 9 (Risk Management) | Policy engine enforces documented rules per risk category |
| EU AI Act — Art. 12 (Record-Keeping) | Cryptographic audit ledger provides tamper-proof log |
| NIST AI RMF — GOVERN 1.2 | Policy-as-Code in `policy.json` provides auditable governance documentation |
| NIST AI RMF — MANAGE 2.4 | Circuit breaker provides automated incident response |
| ISO/IEC 42001 — 6.1.2 | Risk treatment controls implemented at the inference layer |

---

## Extending the Toolkit

### Add a new forbidden topic
Edit `config/policy.json`:
```json
"block_forbidden_tokens": ["malware", "social engineering", "steal password", "your_new_term"]
```
Restart the server. Done.

### Connect to a real LLM
In `src/main.py`, after the `APPROVED` check, add your LLM call:
```python
import openai
if decision["allowed"]:
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": payload.prompt}]
    )
    return {"status": "APPROVED", "llm_response": response.choices[0].message.content}
```

### Export audit logs for regulators
```bash
python -c "
import sqlite3, csv
conn = sqlite3.connect('ledger.db')
rows = conn.execute('SELECT * FROM compliance_log').fetchall()
with open('audit_export.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['id','request_id','action_taken','rule_violated','previous_hash','current_hash'])
    w.writerows(rows)
print(f'Exported {len(rows)} rows to audit_export.csv')
"
```

---

## 🗺️ Roadmap

- [x] Publish to PyPI: `pip install awesome-ai-governance-toolkit`
- [x] Streamlit Cloud live demo deployment
- [ ] Build and publish official multi-architecture Docker images to GitHub Container Registry (GHCR)
- [ ] Integrate Microsoft Presidio for structural PII entity anonymization
- [ ] Implement asynchronous PostgreSQL support for distributed multi-tenant audit logging
- [ ] Add OpenTelemetry tracing for enterprise observability stacks

---

## License

Apache 2.0 — see [LICENSE](LICENSE). Free to use, modify, and distribute. Attribution appreciated.

---

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide — it covers roles from Legal Engineers to Security Researchers, with explicit instructions for adding policy rules, PII patterns, and regulatory corpus entries.

**Quick path to your first PR:**

```bash
git checkout -b feature/your-feature
pytest tests/ -v          # must be green
git push && open PR       # PR template will guide the rest
```

All PRs must pass the automated red-team CI pipeline. A PR that allows a dangerous prompt to reach the LLM **will not merge**, regardless of other quality.

Found a security vulnerability? See [SECURITY.md](SECURITY.md) — **do not open a public issue.**
