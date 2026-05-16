"""
Seed realistic demo data into ledger.db for Streamlit Cloud / demonstration.
Run once: python demo_seed.py
Skips automatically if the database already has entries.
"""
import hashlib
import sqlite3
import uuid

from src.database import init_db

DEMO_ENTRIES = [
    ("APPROVED", None,                                    "CLOSED"),
    ("APPROVED", None,                                    "CLOSED"),
    ("BLOCKED",  "token_match: malware",                  "CLOSED"),
    ("APPROVED", None,                                    "CLOSED"),
    ("APPROVED", "HITL trigger: medical advice",          "PENDING_REVIEW"),
    ("BLOCKED",  "token_match: steal password",           "CLOSED"),
    ("APPROVED", None,                                    "CLOSED"),
    ("BLOCKED",  "token_match: social engineering",       "CLOSED"),
    ("APPROVED", None,                                    "CLOSED"),
    ("APPROVED", "HITL trigger: financial advice",        "PENDING_REVIEW"),
    ("APPROVED", None,                                    "CLOSED"),
    ("BLOCKED",  "token_match: exploit payload",          "CLOSED"),
]


def seed_demo_db(db_path: str = "ledger.db") -> int:
    """Insert demo rows. Returns number of rows inserted (0 if already seeded)."""
    init_db()
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM compliance_log").fetchone()[0]
    if count > 0:
        conn.close()
        return 0

    prev_hash = "0" * 64
    inserted  = 0
    for action, violation, review in DEMO_ENTRIES:
        rid            = str(uuid.uuid4())
        tid            = "tenant_demo"
        violation_str  = violation or ""
        curr_hash      = hashlib.sha256(
            f"{rid}{tid}{action}{violation_str}{prev_hash}".encode()
        ).hexdigest()
        conn.execute(
            """INSERT INTO compliance_log
               (request_id, tenant_id, action_taken, rule_violated,
                review_status, previous_hash, current_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (rid, tid, action, violation, review, prev_hash, curr_hash),
        )
        prev_hash = curr_hash
        inserted += 1

    conn.commit()
    conn.close()
    return inserted


if __name__ == "__main__":
    n = seed_demo_db()
    if n:
        print(f"Seeded {n} demo entries into ledger.db")
    else:
        print("Database already contains data — skipped.")
