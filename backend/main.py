"""VaultPay Agent - FastAPI backend.

API contract (blueprint):
  POST /api/policies/parse   {text} -> {policy_json}
  POST /api/policies         {policy_json} -> saved policy
  POST /api/tasks            {prompt} -> {task_id}
  GET  /api/tasks/{id}       -> task + candidates + verdicts
  GET  /api/approvals        -> pending approval cards
  POST /api/approvals/{id}   {decision} -> approve triggers PayPal flow
  POST /api/paypal/webhook   PayPal -> backend (verified, idempotent)
  GET  /api/audit?task_id=   -> money timeline
  GET  /health
  POST /api/demo/reset       -> seed/reset demo state
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from db import get_db, init_db
import models
from models import write_audit
from policy_engine import DEFAULT_POLICY, validate_policy, evaluate
import agent as agent_mod
from paypal_service import paypal
from seed import reset_demo

app = FastAPI(title="VaultPay Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _startup():
    init_db()
    db = next(get_db())
    try:
        if not db.query(models.Policy).filter_by(active=True).first():
            reset_demo(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"ok": True, "service": "vaultpay-agent", "paypal_mock": paypal.mock}


# ------------------------------------------------------------- policies --
@app.post("/api/policies/parse")
def parse_policy(body: dict):
    text = (body or {}).get("text", "")
    if not text.strip():
        raise HTTPException(400, "text is required")
    try:
        return {"policy_json": agent_mod.parse_policy_text(text)}
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/policies")
def save_policy(body: dict, db: Session = Depends(get_db)):
    raw = (body or {}).get("policy_json", body)
    try:
        policy = validate_policy(raw)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.query(models.Policy).update({models.Policy.active: False})
    last = db.query(models.Policy).order_by(models.Policy.version.desc()).first()
    row = models.Policy(policy_json=json.dumps(policy),
                        version=(last.version + 1 if last else 1), active=True)
    db.add(row); db.commit(); db.refresh(row)
    write_audit(db, "INFO", f"Policy v{row.version} saved and activated: {json.dumps(policy)}")
    return row.to_dict()


@app.get("/api/policies/active")
def active_policy(db: Session = Depends(get_db)):
    row = db.query(models.Policy).filter_by(active=True).first()
    return row.to_dict() if row else {"policy_json": DEFAULT_POLICY, "version": 0, "active": True}


def _active_policy(db) -> dict:
    row = db.query(models.Policy).filter_by(active=True).first()
    return json.loads(row.policy_json) if row else dict(DEFAULT_POLICY)


# ---------------------------------------------------------------- tasks --
def _pay_for_candidate(db, task, cand, item) -> models.Order:
    created = paypal.create_order(float(item["price"]), item["name"], custom_id=str(task.id))
    order = models.Order(task_id=task.id, candidate_id=cand.id,
                         paypal_order_id=created["id"], amount=float(item["price"]),
                         status="CREATED")
    db.add(order); db.commit(); db.refresh(order)
    result = paypal.capture_order(created["id"], expected_amount=float(item["price"]))
    if result["status"] == "COMPLETED":
        order.status = "PAID"
        cand.status = "PAID"
        task.spent_total = round(task.spent_total + float(item["price"]), 2)
        write_audit(db, "PAID",
                    f"PAID: {item['name']} - ${float(item['price']):.2f} captured via PayPal "
                    f"(order {created['id']}, status COMPLETED).", task_id=task.id)
    else:
        order.status = "FAILED"
        cand.status = "FAILED"
        write_audit(db, "FAILED",
                    f"FAILED: capture for {item['name']} returned {result['status']}; not retried silently.",
                    task_id=task.id)
    db.commit()
    return order


@app.post("/api/tasks")
def create_task(body: dict, db: Session = Depends(get_db)):
    prompt = (body or {}).get("prompt", "").strip()
    if not prompt:
        raise HTTPException(400, "prompt is required")
    task = models.Task(prompt=prompt, status="PENDING")
    db.add(task); db.commit(); db.refresh(task)
    policy = _active_policy(db)
    parsed = agent_mod.parse_task(prompt)
    candidates = agent_mod.select_candidates(parsed, agent_mod.load_catalogue())
    write_audit(db, "INFO", f"Task #{task.id} started: '{prompt}' - {len(candidates)} candidate(s) selected.", task_id=task.id)

    if not candidates:
        task.status = "BLOCKED"
        task.summary = "No catalogue items matched this task, so nothing was bought."
        write_audit(db, "DENY", "BLOCKED: no candidates matched the task.", task_id=task.id)
        db.commit()
        return {"task_id": task.id, "status": task.status}

    paused = paid = denied = False
    for item in candidates:
        verdict = evaluate(policy, item, task.spent_total)
        cand = models.Candidate(task_id=task.id, item_id=item["id"],
                                item_snapshot=json.dumps({k: item[k] for k in
                                    ("id", "name", "price", "category", "seller", "seller_rating", "description") if k in item}),
                                verdict=verdict["verdict"], reason=verdict["reason"],
                                justification=item.get("justification", ""))
        db.add(cand); db.commit(); db.refresh(cand)
        write_audit(db, verdict["verdict"], verdict["reason"], task_id=task.id)
        if verdict["verdict"] == "DENY":
            cand.status = "DENIED"; db.commit(); denied = True
            continue
        if verdict["verdict"] == "ASK":
            cand.status = "PENDING_APPROVAL"
            ap = models.Approval(task_id=task.id, candidate_id=cand.id, status="PENDING")
            db.add(ap); db.commit()
            paused = True
            break  # pause the task at the first ASK, per blueprint
        # ALLOW
        _pay_for_candidate(db, task, cand, item)
        paid = cand.status == "PAID"
        break  # one purchase per task run unless quantity handling is added

    task.status = "WAITING_APPROVAL" if paused else ("COMPLETED" if paid else "BLOCKED")
    events = [e.to_dict() for e in db.query(models.AuditEvent).filter_by(task_id=task.id).all()]
    task.summary = agent_mod.explain(prompt, events)
    db.commit()
    return {"task_id": task.id, "status": task.status, "spent_total": task.spent_total,
            "summary": task.summary}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.Task).get(task_id)
    if not task:
        raise HTTPException(404, "task not found")
    cands = db.query(models.Candidate).filter_by(task_id=task_id).all()
    return {"id": task.id, "prompt": task.prompt, "status": task.status,
            "spent_total": task.spent_total, "summary": task.summary,
            "candidates": [{"id": c.id, "item": c.item(), "verdict": c.verdict,
                            "reason": c.reason, "status": c.status,
                            "justification": c.justification} for c in cands]}


# ------------------------------------------------------------ approvals --
@app.get("/api/approvals")
def list_approvals(db: Session = Depends(get_db)):
    rows = db.query(models.Approval).filter_by(status="PENDING").all()
    out = []
    for a in rows:
        cand = db.query(models.Candidate).get(a.candidate_id)
        out.append({"id": a.id, "task_id": a.task_id, "candidate_id": a.candidate_id,
                    "status": a.status, "item": cand.item() if cand else None,
                    "reason": cand.reason if cand else ""})
    return {"approvals": out}


@app.post("/api/approvals/{approval_id}")
def decide_approval(approval_id: int, body: dict, db: Session = Depends(get_db)):
    ap = db.query(models.Approval).get(approval_id)
    if not ap or ap.status != "PENDING":
        raise HTTPException(404, "pending approval not found")
    decision = str((body or {}).get("decision", "")).upper()
    cand = db.query(models.Candidate).get(ap.candidate_id)
    task = db.query(models.Task).get(ap.task_id)
    item = cand.item()
    if decision in ("APPROVE", "APPROVED"):
        ap.status = "APPROVED"; db.commit()
        _pay_for_candidate(db, task, cand, item)
        if task.status == "WAITING_APPROVAL":
            task.status = "COMPLETED" if cand.status == "PAID" else task.status
            db.commit()
        return {"id": ap.id, "status": ap.status, "candidate_status": cand.status,
                "spent_total": task.spent_total}
    if decision in ("REJECT", "REJECTED"):
        ap.status = "REJECTED"; cand.status = "REJECTED"; db.commit()
        write_audit(db, "REJECTED", f"REJECTED by human: {item['name']} was not purchased.", task_id=task.id)
        if task.status == "WAITING_APPROVAL":
            task.status = "BLOCKED"; db.commit()
        return {"id": ap.id, "status": ap.status, "candidate_status": cand.status}
    raise HTTPException(400, "decision must be APPROVE or REJECT")


# -------------------------------------------------------------- webhook --
@app.post("/api/paypal/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    if not paypal.verify_webhook(dict(request.headers), body):
        raise HTTPException(400, "webhook signature verification failed")
    event_id = str(body.get("id", ""))
    if event_id and db.query(models.WebhookEvent).filter_by(event_id=event_id).first():
        return {"ok": True, "duplicate": True}  # idempotent: duplicates are a no-op
    if event_id:
        db.add(models.WebhookEvent(event_id=event_id, event_type=body.get("event_type")))
        db.commit()
    etype = body.get("event_type", "")
    resource = body.get("resource", {}) or {}
    order_id = (resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
                or resource.get("id"))
    order = db.query(models.Order).filter_by(paypal_order_id=order_id).first() if order_id else None
    if etype == "PAYMENT.CAPTURE.COMPLETED" and order:
        order.status = "PAID"; db.commit()
        write_audit(db, "WEBHOOK", f"Webhook {etype}: order {order_id} marked PAID.", task_id=order.task_id)
    elif etype == "PAYMENT.CAPTURE.DENIED" and order:
        order.status = "FAILED"; db.commit()
        write_audit(db, "FAILED", f"Webhook {etype}: order {order_id} marked FAILED.", task_id=order.task_id)
    elif etype == "CHECKOUT.ORDER.APPROVED":
        write_audit(db, "WEBHOOK", f"Webhook {etype}: order {order_id} approved by buyer.",
                    task_id=order.task_id if order else None)
    return {"ok": True}


# ---------------------------------------------------------------- audit --
@app.get("/api/audit")
def audit(task_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(models.AuditEvent)
    if task_id is not None:
        q = q.filter_by(task_id=task_id)
    rows = q.order_by(models.AuditEvent.id.desc()).all()
    return {"events": [e.to_dict() for e in rows]}


# ----------------------------------------------------------------- demo --
@app.post("/api/demo/reset")
def demo_reset(db: Session = Depends(get_db)):
    reset_demo(db)
    return {"ok": True, "message": "Demo state reset: default policy active, audit cleared."}
