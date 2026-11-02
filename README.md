# VaultPay Agent

> "AI agents can shop. VaultPay is the agent you can actually trust with money — it spends only inside rules *you* wrote, asks when it's unsure, refuses when a rule breaks, and shows you exactly why, every time."

**PayPal AI Hackathon · Deadline: Fri 13 Nov 2026, 1:30 AM IST**

## The problem
Autonomous shopping agents are arriving with real wallets attached. The failure mode is trust: an LLM that can spend can also hallucinate, overspend, buy the wrong category, or be prompt-injected into draining a budget — and a pure-LLM decision is not reproducible or auditable.

## The trust idea
**The LLM never decides whether money moves.** The LLM *parses* plain-language rules into a strict JSON policy and *explains* decisions afterwards. Deterministic code — `policy_engine.evaluate()` — decides **ALLOW / ASK / DENY**, in a fixed order, with a human-readable reason for every verdict. Same input, same verdict, every time. Every verdict lands in an append-only audit timeline.

### The 3 demo scenes
1. **ALLOW** — agent buys fest supplies (e.g. the $42 Fest Decoration Kit) inside a $60 budget → pays via PayPal on its own → audit shows the rule that permitted it.
2. **ASK** — agent finds a $31 item, above the $25 ask-threshold → payment pauses → approval card → human approves → PayPal capture completes.
3. **DENY** — agent tries a blocked category (subscription) → refused → **no PayPal order is ever created** → audit shows the rule that blocked it.

## Architecture
```
Next.js + Tailwind ( /rules /tasks /approvals /audit )
        | REST API
FastAPI: Policy Engine (deterministic) · Agent Orchestrator (LLM: parse + explain only)
         PayPal Service (Orders v2 create -> capture, webhooks) · Audit Ledger (append-only)
        |                    |                     |
  PayPal Sandbox        LLM API (optional)     catalogue.json (~30 items)
  api-m.sandbox.paypal.com                     Postgres on Render / SQLite locally
```
Repo: `backend/` (main.py, policy_engine.py, agent.py, paypal_service.py, models.py, db.py, seed.py, tests/) · `frontend/` (App Router, components: ApprovalCard, AuditTimeline, PolicyPreview, TaskTracker) · `catalogue.json` · `render.yaml`

## Setup (under 10 steps)
1. Clone this repo.
2. `cp .env.example .env` — it defaults to `PAYPAL_MOCK=true`, so everything runs with **no PayPal account needed**.
3. Backend: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
4. Run backend: `.venv/bin/uvicorn main:app --port 8000` — check `http://localhost:8000/health` → `{"ok": true, "paypal_mock": true}`
5. Seed/reset demo state any time: `POST /api/demo/reset` (or `.venv/bin/python seed.py`).
6. Frontend: `cd ../frontend && npm install && npm run dev` → http://localhost:3000
7. Try the 3 scenes on `/tasks`: Fest Decoration Kit (ALLOW), Premium Gift Hamper (ASK → approve on `/approvals`), streaming subscription (DENY).
8. **Go real (sandbox):** create a Sandbox app at developer.paypal.com (owner does this), put `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` in `.env`, set `PAYPAL_MOCK=false`, restart. Same code now creates/captures real sandbox orders.
9. Tests: `cd backend && PAYPAL_MOCK=true .venv/bin/python -m pytest tests/ -v`
10. Deploy: import `render.yaml` on Render (backend + frontend), set the env vars marked `sync: false`, register the webhook URL `https://<backend>/api/paypal/webhook` in the PayPal app and set `PAYPAL_WEBHOOK_ID`.

## Judges' testing instructions
- Hosted demo: *(add Render URL after deploy)*
- No login needed — a seeded demo user is built in. Start on `/rules` (default policy: $60 budget, ask above $25, hard cap $100, subscriptions blocked, min seller rating 4.0), then run the 3 tasks listed in step 7 above, and read the verdicts on `/audit`.
- PayPal sandbox buyer login (for the real-sandbox approve step): **email: _[PLACEHOLDER — add sandbox Personal account email after the owner creates the sandbox app]_ · password: _[PLACEHOLDER]_** — sandbox money is fake.
- In mock mode (default `.env.example`), PayPal create/approve/capture is simulated end-to-end returning COMPLETED, so all 3 scenes can be verified without any account.

## AI-tools disclosure (draft)
This project was built with AI assistance (Muse / Muse Spark) for code generation, test generation and documentation. The submitted product itself uses an LLM (when `LLM_API_KEY` is configured) only to parse natural-language spending rules into a validated JSON policy and to explain completed decisions in plain language. All spending verdicts (ALLOW / ASK / DENY) are made by deterministic, unit-tested code — never by the LLM. The app also runs fully without an LLM key via a deterministic local fallback parser.

## Out of scope (by design)
Real e-commerce scraping, other PayPal products, multi-currency, full auth (seeded demo user), mobile app, refunds flow.
