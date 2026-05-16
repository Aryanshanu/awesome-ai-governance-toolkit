import sqlite3
import pandas as pd

DB_PATH = "ledger.db"

def generate_health_report() -> dict:
    """
    Generates a transparency and health report from the immutable ledger.
    Provides metrics for RAI observability.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query("SELECT * FROM compliance_log", conn)
    except Exception:
        return {"total": 0, "blocked": 0, "hitl": 0, "fairness_issues": 0, "fairness_score": 100.0}
        
    if df.empty:
        return {"total": 0, "blocked": 0, "hitl": 0, "fairness_issues": 0, "fairness_score": 100.0}
        
    total = len(df)
    blocked = len(df[df["action_taken"] == "BLOCKED"])
    hitl = len(df[df["action_taken"] == "PENDING_HITL"])
    
    # Fairness issues are ones where the rule violated mentions bias/fairness
    fairness_issues = len(df[df["rule_violated"].str.contains("bias|fairness", case=False, na=False)])
    
    fairness_score = 100.0
    if total > 0:
        fairness_score = round(((total - fairness_issues) / total) * 100.0, 1)
        
    return {
        "total": total,
        "blocked": blocked,
        "hitl": hitl,
        "fairness_issues": fairness_issues,
        "fairness_score": fairness_score
    }
