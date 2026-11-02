"""Seed / reset: fresh demo state in one action.
Run directly:  python seed.py     (or POST /api/demo/reset)
Restores the default policy that makes all 3 demo scenes fire:
budget $60, ask above $25, hard cap $100, blocked [subscription], min rating 4.0.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def reset_demo(db):
    import models
    from policy_engine import DEFAULT_POLICY
    for model in (models.Approval, models.Order, models.Candidate, models.Task,
                  models.AuditEvent, models.WebhookEvent, models.Policy, models.User):
        db.query(model).delete()
    db.commit()
    db.add(models.User(id=1, name="Demo User", email="demo@vaultpay.local"))
    db.add(models.Policy(user_id=1, policy_json=json.dumps(DEFAULT_POLICY), version=1, active=True))
    db.commit()
    from models import write_audit
    write_audit(db, "INFO", "Demo reset: default policy active "
                "($60 budget, ask above $25, hard cap $100, subscriptions blocked, min seller rating 4.0).")
    return True


if __name__ == "__main__":
    from db import SessionLocal, init_db
    init_db()
    session = SessionLocal()
    try:
        reset_demo(session)
        print("Demo state reset OK - default policy active, audit cleared.")
    finally:
        session.close()
