# Contributing to Awesome AI Governance Toolkit

Thank you for helping build responsible AI infrastructure. This guide covers everything needed to contribute effectively.

## Who We Need

- **Legal Engineers** — map new regulatory frameworks (ISO 42001, CCPA, SOC 2) into `policy.json` schemas
- **AI/ML Engineers** — improve the safety scorer, add new guard layers to `src/engine.py`
- **Security Researchers** — red-team the intercept pipeline, find bypass vectors
- **Compliance Officers** — review and expand `config/bias_lexicon.json`
- **DevOps Engineers** — improve the CI pipeline, Docker hardening, Kubernetes manifests

---

## Development Setup

```bash
git clone https://github.com/your-org/awesome-ai-governance-toolkit
cd awesome-ai-governance-toolkit
pip install -r requirements.txt
```

Verify everything works:
```bash
pytest tests/ -v
```

---

## Project Structure

```
src/engine.py       ← Core guard logic — most contributions land here
src/interceptor.py  ← PII detection patterns
src/rag.py          ← Regulatory vector index
src/database.py     ← Audit ledger — change with extreme care
config/policies/    ← Policy JSON files (no Python required)
config/bias_lexicon.json  ← Bias terms (compliance team owns this)
tests/              ← All tests live here
```

---

## Contribution Workflow

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write tests first.** Every change to `src/` must be covered by `tests/test_governance.py`. The CI pipeline rejects PRs with failing tests.

3. **Run the full test suite locally:**
   ```bash
   pytest tests/ -v --tb=short
   ```

4. **Run a manual red-team check** if you touched `src/engine.py`:
   ```bash
   uvicorn src.main:app --port 8000 &
   curl -X POST http://localhost:8000/v1/intercept \
     -H "Content-Type: application/json" \
     -d '{"prompt": "malware"}'
   # Must return 403
   ```

5. **Submit a Pull Request** against `main`. Fill out the PR template completely.

---

## Adding a New Policy Rule

No Python required. Edit `config/policies/tenant_global_baseline.json`:

```json
"block_forbidden_tokens": [
  "malware",
  "social engineering",
  "exploit payload",
  "your_new_term_here"
]
```

Restart the server. The new rule is live. Add a corresponding test in `tests/test_governance.py`.

---

## Adding a New Regulatory Corpus to the RAG Index

Edit `src/rag.py` and add an entry to `REGULATORY_CORPUS`:

```python
REGULATORY_CORPUS: dict[str, str] = {
    ...
    "your_framework_key": """
    Framework Name — Key Provisions
    Article X: ...
    """,
}
```

Then clear the existing index so it rebuilds with your new content:
```bash
rm -rf chroma_db/
```

---

## Adding New PII Pattern Types

Edit `src/interceptor.py` and add to `PII_PATTERNS`:

```python
PII_PATTERNS: dict[str, str] = {
    ...
    "NHS_NUMBER": r"\b\d{3}\s\d{3}\s\d{4}\b",  # UK NHS number example
}
```

Add a corresponding test in `tests/test_governance.py` under `TestPIIInterceptor`.

---

## Bias Lexicon Updates

The `config/bias_lexicon.json` file is owned by the compliance team. To propose additions:

1. Open a GitHub Issue with the label `bias-lexicon-update`
2. Include: the term, the category, the harm potential, and a citation
3. A compliance reviewer will approve before merge

---

## CI Pipeline Requirements

All PRs must pass:

| Check | Requirement |
|---|---|
| Unit tests | `pytest tests/ -v` — 0 failures |
| Malware block | `POST /v1/intercept {"prompt": "malware"}` → 403 |
| Exploit block | `POST /v1/intercept {"prompt": "exploit payload..."}` → 403 |
| Social engineering block | → 403 |
| Safe prompt pass | → 200 |
| PII anonymization | Email in prompt → `pii_redacted: ["EMAIL"]` in response |
| Kill switch | Active kill switch → 503 |
| Hash chain | All ledger entries verify |

A PR that allows a red-team prompt to reach the LLM **will not merge**, regardless of other quality.

---

## Code Standards

- Python 3.13+
- Type hints on all function signatures
- No external AI API keys in any committed code
- No hardcoded credentials, tokens, or secrets
- `config/` files are the right place for tunable parameters — not source code

---

## Reporting Security Vulnerabilities

Do **not** open a public GitHub Issue for security vulnerabilities. Email the maintainers directly with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

We will respond within 48 hours and coordinate a responsible disclosure timeline.

---

*Built for the future of responsible AI. Every contribution makes enterprise AI safer.*
