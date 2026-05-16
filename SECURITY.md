# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ Active |
| Older releases | ❌ No patches |

## Reporting a Vulnerability

**Do not open a public GitHub Issue for security vulnerabilities.**

The Runtime Firewall and Audit Ledger handle security-sensitive workloads. A bypass vector or ledger integrity flaw is a critical issue that requires coordinated disclosure.

### How to Report

Email the maintainers with the subject line: `[SECURITY] awesome-ai-governance-toolkit`

Include:
1. **Description** — What the vulnerability is and which component it affects (`src/engine.py`, `src/database.py`, the intercept proxy, etc.)
2. **Steps to reproduce** — Exact prompt, request, or config state that triggers the issue
3. **Impact** — What an attacker could achieve (e.g., bypass the circuit breaker, corrupt the audit chain, exfiltrate policy rules)
4. **Suggested fix** — Optional, but appreciated

### What to Expect

- **Acknowledgement within 48 hours** of your report
- **Status update within 7 days** with our assessment and timeline
- **Credit in the release notes** if you'd like it (opt-in)
- Coordinated public disclosure after a fix is deployed

### Scope

In scope:
- Prompt injection bypasses that allow a forbidden token to reach the LLM
- Audit ledger integrity vulnerabilities (hash chain manipulation, log suppression)
- Policy engine logic flaws (rules not evaluated, wrong precedence)
- PII detection bypasses that allow sensitive data to pass unredacted

Out of scope:
- Vulnerabilities in third-party dependencies (report upstream)
- Issues requiring physical access to the server
- Social engineering of maintainers

## Security Design Principles

This project is built with the following security invariants that must never be broken:

1. **A BLOCKED prompt must never reach the LLM** — the circuit breaker is a hard stop, not a score
2. **Every decision (APPROVED and BLOCKED) must be written to the audit ledger** — no silent failures
3. **The hash chain must be verifiable** — any modification to any ledger entry must be detectable
4. **No credentials, API keys, or secrets in committed code** — ever
