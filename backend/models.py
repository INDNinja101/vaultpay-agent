import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean
from db import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, default="Demo User")
    email = Column(String, default="demo@vaultpay.local")


class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, default=1)
    policy_json = Column(Text, nullable=False)
    version = Column(Integer, default=1)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)

    def to_dict(self):
        return {"id": self.id, "policy_json": json.loads(self.policy_json),
                "version": self.version, "active": self.active}


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    prompt = Column(Text, nullable=False)
    status = Column(String, default="PENDING")  # COMPLETED|WAITING_APPROVAL|BLOCKED|FAILED
    spent_total = Column(Float, default=0.0)
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=_now)


class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=False)
    item_id = Column(Integer)
    item_snapshot = Column(Text, nullable=False)  # JSON snapshot of catalogue item
    verdict = Column(String)  # ALLOW|ASK|DENY
    reason = Column(Text)
    status = Column(String, default="EVALUATED")  # PAID|PENDING_APPROVAL|DENIED|REJECTED|EVALUATED
    justification = Column(Text, default="")

    def item(self):
        return json.loads(self.item_snapshot)


class Approval(Base):
    __tablename__ = "approvals"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=False)
    candidate_id = Column(Integer, nullable=False)
    status = Column(String, default="PENDING")  # PENDING|APPROVED|REJECTED
    created_at = Column(DateTime, default=_now)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer)
    candidate_id = Column(Integer)
    paypal_order_id = Column(String, unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, default="CREATED")  # CREATED|PAID|FAILED
    created_at = Column(DateTime, default=_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, nullable=True)
    type = Column(String, nullable=False)  # ALLOW|ASK|DENY|PAID|INFO|WEBHOOK|REJECTED|FAILED
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_now)

    def to_dict(self):
        return {"id": self.id, "task_id": self.task_id, "type": self.type,
                "message": self.message,
                "created_at": self.created_at.isoformat() if self.created_at else None}


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, nullable=False)
    event_type = Column(String)
    created_at = Column(DateTime, default=_now)


def write_audit(db, type: str, message: str, task_id=None) -> AuditEvent:
    """Append-only: the ONLY way audit events are created. Never update/delete them."""
    ev = AuditEvent(task_id=task_id, type=type, message=message)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev
