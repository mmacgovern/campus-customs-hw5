# Campus Customs Multi-Agent Operations (HW5)

An AI operations desk for **Campus Customs**, a small campus apparel shop. A team of five AI agents (Boss, Inventory, Accounting, Facilities, Customer Service) works the shop's open tickets: a customer's tee order (101), a rent notice (102), and a bulk hoodie discount request (103).

The agents only *prepare* payments and purchase orders. **A human approves every dollar** on a React dashboard, and only then does money move.

- **MCP server** (`mcp_server/`, FastMCP): the *only* way the agents read or change shop data. It has 18 tools, and the pay tool is hidden from every agent.
- **Backend** (`backend/`, FastAPI + Pydantic AI): the five-agent team with delegation guardrails, an append-only audit trail, and the approval routes.
- **Dashboard** (`frontend/`, React + Vite + TypeScript): a live "control room" board with agent avatars, a delegation map, approval cards, an animated cash balance and a RESOLVED stamp.
- **Write-ups** (`output/`): the harness, design notes, the plan vs. actual results for each ticket, cash reconciliation, screenshots, and the reflection.

All AI calls go through **Portkey** (`https://api.portkey.ai/v1`) using the model set in `backend/config.py` (the only place it's written).

---

## 1. Setup (once)

You need **Python 3.12** and **Node.js 18+**. Run these from the project folder (`hw5/`). The commands are for Windows (cmd); on Mac/Linux use `.venv/bin/python` and `cp`.

```bat
:: Python virtual environment + packages
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

:: (optional) browser for the screenshot tool
.venv\Scripts\python -m playwright install chromium

:: Dashboard packages
cd frontend
npm install
cd ..

:: Your Portkey key
copy .env.example .env
```

Open `.env` in Notepad and put your key after the `=`:

```
PORTKEY_API_KEY=your-portkey-key-here
```

`.env` is in `.gitignore` and is never committed. The code loads the key at run time with python-dotenv.

## 2. Make a clean working database

`data/campus_customs.db` is the **original** and is never modified. Everything reads and writes `data/campus_customs_new.db`, the working copy. To make (or reset) the working copy, copy the original over it:

```bat
.venv\Scripts\python -m backend.db_reset
```

This is the same as `copy data\campus_customs.db data\campus_customs_new.db`. When the backend is running, you can also click **↺ Reset database** on the board or call `POST /reset`.

## 3. The MCP server

The backend **starts the MCP server automatically** (over stdio) whenever the agents or API routes need it, so you normally don't run it yourself. To run it standalone, for example to test it or to connect it to Claude Code through `.mcp.json`:

```bat
.venv\Scripts\python mcp_server\server.py
```

It waits quietly for an MCP client. Press Ctrl+C to stop it. See [mcp_server/README.md](mcp_server/README.md) for all 18 tools.

## 4. Start the backend (window 1)

Run this from **inside** `backend/`:

```bat
cd backend
..\.venv\Scripts\uvicorn main:app --reload --port 8000
```

Wait for "Application startup complete". Check http://localhost:8000/health, or try every route at http://localhost:8000/docs.

## 5. Start the dashboard (window 2)

```bat
cd frontend
npm run dev
```

Open **http://localhost:5173**. The top bar should say **Backend online** and **Checking $3,400.00**.

## 6. A full three-ticket run

1. **Reset the database first** (step 2, or ↺ Reset database on the board), so cash is $3,400.00 and all tickets are open.
2. On the board, pick **ticket 101** → **▶ Start the team** → wait until it finishes, then approve or reject the requests on the right.
3. Repeat for **102** and **103**, one ticket at a time.
4. Watch the checking balance drop after each approval. The pay tool refuses anything that would make it negative.

Each run makes real AI calls (roughly 50,000–75,000 tokens per ticket).

Other useful commands, from `hw5/`:

```bat
:: Boss on ticket 101 with a low usage limit, then reset
.venv\Scripts\python -m backend.smoke_test

:: Screenshot the board for each ticket (backend + dashboard must be running)
.venv\Scripts\python tools\capture_board.py
```

## 7. Safety rules (short version)

- **Human approval for every payment or purchase.** Agents call `create_payment_request` or `create_purchase_order_request` (status `pending`). Only `POST /approvals/{id}/approve` calls the hidden pay tool `execute_approved_payment`.
- **No negative balances.** The pay tool refuses if cash would go below zero, and a vendor with an unpaid invoice won't get paid for a new purchase order.
- **The shop's "today"** comes from the `desk` table (2026-08-31), never the real calendar.
- **Drafts only.** Customer messages are saved with `save_customer_draft` and never sent.
- **One door to the data.** Shop facts come only from the database through the MCP tools.
- **Guardrails:** max delegation depth 3, no self-delegation, a per-run `UsageLimits` shared by the whole team, and an append-only `output/audit_trail.json`.

Full details: [output/harness.md](output/harness.md).

## 8. Project layout

```
hw5/
├── README.md               this file
├── AI_Prompts.md           every prompt I typed, problem by problem
├── CLAUDE.md               project rules for the vibe coder
├── requirements.txt        Python packages
├── .env.example            copy to .env and add PORTKEY_API_KEY (.env is git-ignored)
├── .gitignore
├── .mcp.json               registers the MCP server with Claude Code
├── data/
│   ├── campus_customs.db       ORIGINAL (never modified)
│   └── campus_customs_new.db   working copy (reset = copy the original over it)
├── mcp_server/
│   ├── server.py           FastMCP server, 18 tools (stdio)
│   └── README.md
├── backend/
│   ├── main.py             FastAPI app (routes, approvals, reset)
│   ├── config.py           model name, Portkey URL, paths, limits (the one place for the model)
│   ├── models.py           Pydantic types (Ticket, AuditEvent, Delegation, PendingApproval, ...)
│   ├── agents/             boss.py, inventory.py, accounting.py, facilities.py,
│   │                       customer_service.py, base.py (delegate tool + audited run loop)
│   ├── prompts/            boss.md, inventory.md, accounting.md, facilities.md, customer_service.md
│   ├── mcp_client.py       MCP stdio connection + filtered (agent-safe) toolsets
│   ├── worker.py           background event loop for MCP/agent work (Windows-safe with --reload)
│   ├── runner.py           runs the team on one ticket
│   ├── audit.py            append-only output/audit_trail.json
│   ├── db_reset.py         reset the working database
│   └── smoke_test.py       quick Boss run on ticket 101
├── frontend/               React + Vite + TypeScript dashboard (src/config.ts holds the backend URL)
├── tools/
│   └── capture_board.py    Playwright screenshots of the board
└── output/
    ├── harness.md          tables, MCP tools, agents, safety, API routes, dashboard, run results
    ├── design.md           dashboard design notes
    ├── desk_tickets.html   Expected vs Actual per ticket, Cash, Reflection (open by double-clicking)
    ├── resolved_board.html board screenshots for 101-103 (works offline)
    ├── resolved_tickets.json
    ├── mcp_smoke.json      MCP tool tests checked against SQL
    ├── audit_trail.json    every agent step (append-only)
    ├── starting_balance.txt
    ├── github_url.txt
    └── screenshots/
```
