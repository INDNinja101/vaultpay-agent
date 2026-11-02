# Demo Video Script — VaultPay Agent (under 3 minutes, Blueprint Step 29)
Public on YouTube. Record against the deployed app (or localhost in mock mode — state which on screen).

| Time | Screen | Say / show |
|---|---|---|
| 0:00–0:15 | Home page | Hook: "Agents that spend are everywhere. This is the one you'd trust with a wallet." |
| 0:15–0:40 | /rules | Type the rules in plain language: "Fest supplies under $60, ask me above $25, never subscriptions, only sellers rated 4+" → Parse → policy preview appears → Save. Point out: "The AI only *parses*. From here, code decides." |
| 0:40–1:15 | /tasks → ALLOW scene | Run "Buy the Complete Fest Decoration Kit" ($42, inside the $60 budget). Show verdict ALLOW, PayPal capture COMPLETED, spent total updates. |
| 1:15–1:50 | /tasks → /approvals → ASK scene | Run "Buy Premium Gift Hamper" ($31 > $25 threshold). Agent pauses — nothing paid. Go to /approvals, show the card with the triggering rule, click Approve → PayPal capture completes → PAID. |
| 1:50–2:20 | /tasks → DENY scene | Run "Buy a streaming subscription". Verdict DENY, blocked category. Emphasise: "No PayPal order was ever created for this." Show the task ending BLOCKED — a correct outcome. |
| 2:20–2:50 | /audit | Close on the money timeline, colour-coded ALLOW / ASK / DENY / PAID: "Every dollar it touched, explained." |
| 2:50–3:00 | Home / end card | "VaultPay Agent — rules you wrote, verdicts you can audit. Repo and live demo in the description." |

Notes: keep it under 3:00 total; reset the demo (`POST /api/demo/reset` or the Reset button on /audit) before recording so the timeline is clean; do not show any real credentials — sandbox/mock only.
