---
name: 🐛 Bug Report
about: Report a bug in the runtime engine, policy evaluation, or audit ledger.
title: '[BUG] '
labels: bug
assignees: ''
---

## Describe the Bug

A clear and concise description of what the bug is.

## Environment

- OS: [e.g. Ubuntu 22.04, macOS 14, Windows 11]
- Python version: [e.g. 3.11.4]
- Toolkit version / commit SHA:

## To Reproduce

Steps to reproduce the behavior:

1. Start the server with `uvicorn src.main:app --reload --port 8000`
2. Fire this prompt: `curl -X POST ... -d '{"prompt": "..."}'`
3. Observed response: `...`

## Expected Behavior

What should have happened according to the `policy.json` parameters or documented API contract.

## Actual Behavior

What actually happened. Include the full HTTP response body and status code.

## Logs & Stack Trace

```
Paste any relevant server logs or Python tracebacks here.
```

## Audit Ledger State (if relevant)

If the bug involves incorrect ledger entries, paste the output of the chain verification script:

```
python - <<'EOF'
import sqlite3, hashlib
conn = sqlite3.connect("ledger.db")
rows = conn.execute("SELECT request_id, action_taken, rule_violated, previous_hash, current_hash FROM compliance_log ORDER BY id").fetchall()
for i, row in enumerate(rows):
    rid, action, viol, prev, curr = row
    recomputed = hashlib.sha256(f"{rid}{action}{viol}{prev}".encode()).hexdigest()
    print(f"Row {i+1} [{action}]: {'VERIFIED' if recomputed == curr else 'CHAIN BROKEN'}")
conn.close()
EOF
```

## Additional Context

Add any other context, screenshots, or dashboard views here.
