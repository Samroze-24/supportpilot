# SupportPilot — AI Helpdesk SaaS for Online Stores

An AI helpdesk SaaS for online stores worldwide. One shared inbox for email, chat and WhatsApp, AI triage that sorts every ticket, draft replies a human approves in one click, a knowledge base, per-plan SLAs, mock billing and analytics — built as a real sellable product, not a demo classifier.

> **Demo build:** runs fully offline with sample data. Billing is **MOCK** (no real Stripe, no real money), channels are simulated (no real email or WhatsApp messages are sent), and AI drafts always need human approval.

## What it does

- **Public landing page** (`GET /`) — Linear/Stripe-style light SaaS design: hero, features, pricing (Free $0, Pro $19/mo, Business $49/mo), FAQ.
- **Auth + multi-tenant workspaces** — signup creates a workspace + owner account; roles owner/admin/agent; invite agents into the same workspace. **Strict isolation:** no user can ever see another workspace's tickets, customers, KB articles or billing.
- **Shared inbox** — tickets across email/chat/WhatsApp (mock), status open/pending/resolved, priority low/normal/high/urgent, assignment, SLA first-response targets per plan (Free 24h, Pro 4h, Business 1h), reply threads, internal notes, tags, search/filter/pagination.
- **AI triage (real ML, no API key)** — TF-IDF + LogisticRegression intent classifier trained on 140 sample English messages (7 intents) plus lexicon sentiment. On ticket creation the API auto-suggests intent, sentiment and priority; the agent accepts or overrides.
- **AI draft replies + knowledge base** — template-based drafts from intent + extracted entities (order/tracking numbers). Drafts are draft-first (`drafted → approved → sent`) — nothing is ever auto-sent. KB articles (CRUD) with TF-IDF retrieval suggesting relevant articles per ticket; public help center at `/help`.
- **Billing (MOCK)** — plans enforced server-side: Free 50 tickets/month + 1 agent, Pro 500 tickets/month + 5 agents, Business unlimited. Exceeding a limit returns `402`. Mock checkout upgrades the plan and records a `MOCK-STRIPE-…` reference.
- **Analytics** — tickets by status/intent/channel, average first-response time, resolution rate, CSAT.

## Tech stack

Python 3.14 · FastAPI + SQLAlchemy + SQLite · JWT auth (python-jose) · direct bcrypt passwords (no passlib) · scikit-learn · vanilla HTML/CSS/JS frontend served by FastAPI (no Node/npm, no CDN, works offline).

## Run it (Windows PowerShell + VS Code)

VS Code is only one way to run these commands — the same PowerShell commands work in any terminal.

```powershell
cd supportpilot
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python train_model.py
python -m app.seed
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000 — the landing page. The dashboard is at `/app`, API docs at `/docs`, health at `/health`.

Run the tests:

```powershell
python -m pytest -q
```

Reset the database:

```powershell
Remove-Item supportpilot.db
python -m app.seed
```

## Demo logins (after seeding)

| Role | Email | Password |
|---|---|---|
| Owner (Northwind Store, Free plan) | owner@northwind.store | owner123 |
| Agent | sara@northwind.store | agent123 |
| Agent | omar@northwind.store | agent123 |

The seed creates 24 tickets from international customers (US, UK, UAE, Canada, Australia, Germany, France, …), 8 KB articles, replies, drafts and one mock billing record.

## Demo walkthrough

1. Log in as the owner and open the **Inbox** — 24 seeded tickets with AI intent badges.
2. Open a ticket: see the AI triage (intent, sentiment, suggested priority) and the auto-created AI draft. **Approve** it, then **Send** — it lands on the reply thread.
3. Click **New ticket**, write e.g. *"Where is my order #ORD-4821? It was placed 5 days ago."* — the API triages it as `order_status` and creates a draft automatically.
4. Open **Knowledge base**, add an article, then check **Suggested KB articles** on a matching ticket.
5. Open **Billing**: Free plan shows 24/50 tickets used. Create tickets until 50 — the 51st returns `402`. Click **Upgrade to Pro (mock)** — the cap lifts and a `MOCK-STRIPE-…` payment appears.
6. Open **Analytics** for status/intent/channel breakdowns, first-response time and CSAT.

## API highlights

| Route | Notes |
|---|---|
| `POST /auth/signup` | Creates workspace + owner, returns JWT |
| `POST /auth/login` | JSON login |
| `POST /auth/login-form` | Form login — Swagger Authorize uses this |
| `POST /auth/invite` | Owner/admin invites an agent (plan agent-limit enforced) |
| `GET/POST /tickets` | List (filter/search/paginate) · create runs AI triage |
| `GET /tickets/{id}` | Ticket + replies + notes + drafts |
| `POST /tickets/{id}/drafts` | Generate AI draft · `PATCH /tickets/drafts/{id}` approve/send |
| `GET /tickets/{id}/suggest-kb` | TF-IDF KB suggestions |
| `GET/POST/PATCH/DELETE /kb` | Knowledge base CRUD |
| `GET /billing` · `POST /billing/checkout` | Plan, usage, mock upgrade |
| `GET /analytics/summary` | Dashboard numbers |
| `GET /public/kb?workspace_id=N` | Public help-center articles for one workspace |

## Verified results (2026-11-14)

- **17 tests passed** (fresh venv: install, train, seed, boot, login flows).
- Intent classifier on held-out 20% (28 sample messages): **accuracy 0.9286, macro F1 0.928** — see `metrics.json` after training (regenerate with `python train_model.py`).
- cp314 wheels pre-verified for every dependency (FastAPI 0.121.3, SQLAlchemy 2.1.8, scikit-learn 1.7.2, pandas 2.3.3, bcrypt 4.3.0, pydantic 2.14.3).
- `model.pkl` and `metrics.json` are gitignored and regenerate via `train_model.py`.

## Honest caveats

- Sample/synthetic data only — no real customers, orders or messages.
- Billing is a mock: plans and limits are real server-side logic, but no real payment gateway is connected and no real money moves.
- Channels are simulated: nothing is actually emailed or sent via WhatsApp.
- AI replies are template + ML-suggestion drafts — they need human approval and are not a real LLM.
- Local demo only: change `SECRET_KEY` via environment before any real deployment, and use a production database.
