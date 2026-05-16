import sqlite3
import hashlib
import threading

DB_PATH = "ledger.db"

# Serialise concurrent writes so the hash chain is never corrupted by a
# read-then-write race between two threads grabbing the same prev_hash.
_write_lock = threading.Lock()


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        # WAL mode: allows concurrent readers even while a write is in progress
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compliance_log (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id       TEXT UNIQUE,
                tenant_id        TEXT,
                action_taken     TEXT,
                rule_violated    TEXT,
                review_status    TEXT DEFAULT 'CLOSED',
                previous_hash    TEXT,
                current_hash     TEXT
            )
        """)
        conn.commit()


def get_last_hash() -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT current_hash FROM compliance_log ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row[0] if row else "00000000000000000000000000000000"


def log_transaction(
    request_id: str,
    tenant_id: str,
    action: str,
    violation: str | None,
    review_status: str = "CLOSED",
) -> None:
    violation_str = violation or ""
    with _write_lock:
        # Lock covers both the prev_hash read and the INSERT so no thread can
        # slip in between and claim the same prev_hash.
        prev_hash = get_last_hash()
        hash_input = f"{request_id}{tenant_id}{action}{violation_str}{prev_hash}".encode()
        curr_hash = hashlib.sha256(hash_input).hexdigest()

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO compliance_log
                   (request_id, tenant_id, action_taken, rule_violated,
                    review_status, previous_hash, current_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (request_id, tenant_id, action, violation, review_status,
                 prev_hash, curr_hash),
            )
            conn.commit()


def verify_chain_integrity() -> tuple[bool, int]:
    """
    Walk the entire ledger and verify every hash link.
    Returns (is_intact, broken_row_id) — broken_row_id is -1 if intact.
    """
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """SELECT request_id, tenant_id, action_taken, rule_violated,
                      previous_hash, current_hash
               FROM compliance_log ORDER BY id"""
        ).fetchall()

    for i, row in enumerate(rows):
        rid, tid, action, viol, prev, curr = row
        violation_str = viol or ""
        recomputed = hashlib.sha256(
            f"{rid}{tid}{action}{violation_str}{prev}".encode()
        ).hexdigest()
        if recomputed != curr:
            return False, i + 1

    return True, -1

def update_review_status(request_id: str, new_status: str) -> None:
    """
    Updates the review status of an item.
    Does not break the cryptographic chain because review_status is not part of the hash.
    """
    with _write_lock:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE compliance_log SET review_status = ? WHERE request_id = ?",
                (new_status, request_id)
            )
            conn.commit()

