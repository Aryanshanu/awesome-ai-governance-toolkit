# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-05-15

### Added

**Core Runtime Firewall**
- `POST /v1/intercept` FastAPI endpoint — single entry point for all LLM traffic
- Four-layer guard pipeline: Ingress Proxy → Policy Engine → Circuit Breaker → Audit Ledger
- Policy-as-Code engine: rules loaded from `config/policy.json` at startup, no code change required
- Runtime circuit breaker: hard `403` stop on forbidden token match — prompt never reaches LLM
- Cryptographic audit ledger: SHA-256 hash-chained SQLite log, tamper-evident by design

**Python SDK**
- `sentinel.py` — `Sentinel` class with `verify()` and `verify_output()` methods
- `VerificationResult` dataclass with `.status`, `.clean_prompt`, `.pii_detected`, `.flagged_for_review`
- Built-in policy aliases: `eu_ai_act_high_risk`, `nist_ai_rmf`, `global_baseline`

**PII & Bias Detection**
- Bidirectional PII anonymization on inbound prompts
- Bias lexicon detection (soft flag, not hard block) for compliance review workflow
- Output-side PII verification via `verify_output()`

**Compliance Dashboard**
- Streamlit dashboard (`dashboard.py`) for legal and compliance teams
- Real-time view of audit ledger entries, blocked prompts, and PII redaction events

**CI/CD**
- Automated red-team pipeline (`.github/workflows/safety-ci.yml`)
- Unit tests, red-team attack battery, green-team pass checks, and hash chain verification on every push
- PRs that allow a forbidden prompt to reach the LLM are automatically rejected

**Regulatory Coverage**
- EU AI Act — Art. 9 (Risk Management) and Art. 12 (Record-Keeping) mapping
- NIST AI RMF — GOVERN 1.2 and MANAGE 2.4 mapping
- ISO/IEC 42001 — 6.1.2 mapping

**Community**
- `CONTRIBUTING.md` with role-specific guidance (Legal Engineers, Security Researchers, DevOps)
- `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1)
- Issue templates: Bug Report, Feature Request
- Pull Request template with red-team CI checklist
- `SECURITY.md` — responsible disclosure policy

---

## [1.0.1] — 2026-05-16

### Added
- `pyproject.toml` — pip-installable package (`pip install awesome-ai-governance-toolkit`)
- `ai_governance_toolkit/` — importable package with CLI entry points (`ai-governance-serve`, `ai-governance-dashboard`)
- `.streamlit/config.toml` — Streamlit Cloud theme configuration
- `demo_seed.py` — auto-seeds SHA-256 chained demo data on fresh installs
- GitHub Actions publish workflow — auto-publishes to PyPI on `v*` tag push

### Fixed
- Removed invalid email from package metadata (caused PyPI 400 error on first publish attempt)
- `demo_seed.py` genesis prev_hash aligned with `get_last_hash()` (32 zeros, not 64)
- `transparency_report.py` now imports `DB_PATH` from `src.database` instead of hardcoding
- README "Add forbidden topic" section pointed to wrong config file (`policy.json` → `tenant_global_baseline.json`)

---

## [Unreleased]

### Planned
- Docker multi-architecture image published to GitHub Container Registry (GHCR)
- Microsoft Presidio integration for structural PII entity recognition
- Asynchronous PostgreSQL support for distributed multi-tenant audit logging
- OpenTelemetry tracing for enterprise observability stacks
