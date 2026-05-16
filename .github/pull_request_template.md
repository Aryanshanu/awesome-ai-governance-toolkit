# Pull Request

## Summary

Brief description of what this PR does and which layer it affects.

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Policy rule addition (edit to `config/policy.json` only — no Python change)
- [ ] Regulatory mapping update (compliance table or documentation)
- [ ] Breaking change (fix or feature that would cause existing behavior to change)
- [ ] Infrastructure / CI improvement

## CI Checklist

All of the following must pass before this PR can merge:

- [ ] `pytest tests/ -v` — 0 failures
- [ ] Malware prompt → `403` (red-team check)
- [ ] Social engineering prompt → `403` (red-team check)
- [ ] Safe business prompt → `200` (green-team check)
- [ ] SHA-256 audit chain verification passes
- [ ] No hardcoded secrets, API keys, or credentials in any committed file

## What Was Tested?

Describe how you tested this change. Include the curl commands or test names.

## Regulatory Impact

Does this change affect compliance posture? If so, which articles/clauses?

## Screenshots / Logs (if applicable)
