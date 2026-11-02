# Devpost Submission Draft — VaultPay Agent
*(Copy into Devpost on submission day. Fill the bracketed placeholders after deploy.)*

**Project name:** VaultPay Agent
**Tagline:** The AI shopping agent you can actually trust with money.

## Problem
AI agents are starting to shop with real wallets. But an LLM deciding on its own whether to spend is untrustworthy: it can hallucinate, overspend, buy blocked categories, or be manipulated — and its decisions aren't reproducible or auditable. Users need an agent that spends only inside rules they set, asks before anything unusual, and proves afterwards exactly what it did and why.

## What it does
You write spending rules in plain language ("Fest supplies under $60, ask me above $25, never subscriptions, only sellers rated 4+"). VaultPay turns them into a strict policy, then shops a catalogue against it:
- **ALLOW** — inside all rules → pays via PayPal automatically
- **ASK** — above your ask-threshold → pauses, shows an approval card, pays only after you approve
- **DENY** — breaks a hard rule → refused, and no PayPal order is ever created
Every verdict, with its reason, is written to an append-only money timeline.

## How PayPal is used
PayPal **Orders v2** (sandbox) is the payment rail: server-side OAuth token, `POST /v2/checkout/orders` with `intent: CAPTURE` and the task id as `custom_id`, buyer approval, then server-side capture with amount verification before anything is marked PAID. **Webhooks** (`CHECKOUT.ORDER.APPROVED`, `PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.CAPTURE.DENIED`) are signature-verified and processed idempotently (stored event ids + unique order ids), so the webhook — not the browser — is the source of truth for payment state on the deployed app.

## How AI is used
An LLM parses natural-language rules into a validated JSON policy schema, ranks/explains catalogue picks, and turns the audit log into a plain-language summary. **Critically, the LLM never decides a spending verdict** — a deterministic, unit-tested policy engine does (blocked category → hard cap → seller rating → budget → ask-threshold → allow). Invalid or ambiguous LLM output falls back to ASK, never ALLOW. The app also runs with no LLM key via a deterministic local fallback parser.

## Tech
Next.js + Tailwind · FastAPI · SQLAlchemy (SQLite locally, Postgres on Render) · PayPal Orders v2 + Webhooks · httpx · Pytest (policy-engine rules/boundaries + mock-mode end-to-end gate tests, 18 passing).

## Links (fill in)
- Live demo: [PLACEHOLDER — Render frontend URL]
- Repo: [PLACEHOLDER — public GitHub URL]
- Demo video (<3 min, public YouTube): [PLACEHOLDER]
- Testing instructions: see README — seeded demo user, no login; sandbox buyer login [PLACEHOLDER after sandbox app creation].

## AI-tools disclosure (mandatory field)
Built with AI assistance (Muse / Muse Spark) for coding, tests and docs. Product AI use: an LLM (when configured) parses rules and explains decisions only; all ALLOW/ASK/DENY verdicts are deterministic code. Full disclosure draft in README.md.

## Team
[PLACEHOLDER — list everyone who built it on the Devpost project, incl. teammate invite acceptance.]
