# Campus Customs Agent Harness

This document describes how the Campus Customs Multi-Agent Operations app is put together: the data, the tools, the agent team, the API, the dashboard, and the safety rules around them. Sections:

1. [Database Tables](#1-database-tables): the 9 shop tables plus 2 helper tables
2. [MCP Tools](#2-mcp-tools): the 18 tools in `mcp_server/server.py`, agent-visible vs. backend-only
3. [Agents](#3-agents): Boss, Inventory, Accounting, Facilities, Customer Service
4. [Safety and Guardrails](#4-safety-and-guardrails): money, customers, data, audit, token limits
5. [API Routes](#5-api-routes): `backend/main.py`
6. [Dashboard](#6-dashboard): the React board in `frontend/` (details in [design.md](design.md))
7. [Full Run Results](#7-full-run-results): what happened on tickets 101-103 (details in [desk_tickets.html](desk_tickets.html))

## 1. Database Tables

Source: `data/campus_customs.db` (original, read-only). Agents work against the copy `data/campus_customs_new.db`. The shop's "today" is **2026-08-31** (from `desk.date_today`).

### desk
- **Fields:** `date_today` (TEXT), `notes` (TEXT)
- **Why it matters:** Holds the shop's "today" (2026-08-31), which every agent uses to decide what is overdue. It applies to all three tickets.

### inventory
- **Fields:** `sku` (TEXT), `name` (TEXT), `size` (TEXT), `qty` (INTEGER), `location` (TEXT). Primary key is (`sku`, `size`).
- **Why it matters:** Stock on hand by SKU and size. The Inventory agent checks it for **Ticket 101** (CC-TEE-WHITE size S has 0) and **Ticket 103** (CC-HOOD-NAVY size M has 8 against 20 requested).

### pricing
- **Fields:** `sku` (TEXT), `unit_cost` (REAL), `list_price` (REAL)
- **Why it matters:** Cost and list price per SKU. It sets the floor for the bulk discount in **Ticket 103** (hoodie costs $22.00 and lists at $58.00) and the cost of any reorder for **Ticket 101** and **Ticket 103**.

### vendors
- **Fields:** `id` (INTEGER), `name` (TEXT), `specialty` (TEXT), `lead_days` (INTEGER)
- **Why it matters:** Who can restock and how many days it takes. Bulldog Print Co (apparel reprint, 5 days) matters for **Ticket 101** and **Ticket 103**.

### leases
- **Fields:** `id` (INTEGER), `space_name` (TEXT), `landlord` (TEXT), `monthly_rent` (REAL), `next_due` (TEXT), `notes` (TEXT)
- **Why it matters:** The shop's rent obligation. Lease 1 ($2,400.00 due 2026-09-02) is the subject of **Ticket 102**.

### cash_accounts
- **Fields:** `name` (TEXT), `balance` (REAL), `date` (TEXT)
- **Why it matters:** The only source of cash ("checking", $3,400.00). The pay tool must refuse any payment larger than this balance. It limits **Tickets 101, 102 and 103**.

### payments
- **Fields:** `id` (INTEGER), `kind` (TEXT), `ref_id` (INTEGER), `amount` (REAL), `account` (TEXT), `paid_at` (TEXT), `approved_by` (TEXT)
- **Why it matters:** The record of money that has gone out. It is empty now, and a row is written only after a human approves a payment. Paying invoice 501 (**Ticket 101**) or the rent (**Ticket 102**) will add rows here.

### invoices
- **Fields:** `id` (INTEGER), `vendor_id` (INTEGER → vendors.id), `amount` (REAL), `due_date` (TEXT), `status` (TEXT), `description` (TEXT)
- **Why it matters:** Unpaid vendor bills. Invoice 501 ($840.00 to Bulldog Print Co, due 2026-08-28, open) is overdue and blocks new shipments from that vendor. It is linked to **Ticket 101**.

### tickets
- **Fields:** `id` (INTEGER), `type` (TEXT), `requester` (TEXT), `subject` (TEXT), `sku` (TEXT), `size` (TEXT), `qty` (INTEGER), `lease_id` (INTEGER → leases.id), `invoice_id` (INTEGER → invoices.id), `status` (TEXT), `notes` (TEXT), `created_at` (TEXT)
- **Why it matters:** The work queue the Boss agent routes to the specialist agents. It holds **Tickets 101, 102 and 103**, all `open`.

### Helper tables (added by the app, not in the original)

The MCP server creates these in the working copy when they're first needed (and `POST /reset` recreates them), so the original database is never changed.

### approvals
- **Fields:** `id`, `kind` (invoice / rent / purchase_order), `ref_id` (invoice, lease, or vendor id), `ticket_id`, `payee`, `amount`, `account`, `sku`, `size`, `qty`, `reason`, `requested_by` (agent), `status` (pending / executed / rejected), `shop_date`, `created_at`, `decided_by`, `decided_at`, `decision_note`, `payment_id`
- **Why it matters:** Every payment or purchase an agent *prepares* waits here as `pending` until a human approves or rejects it. In the full run: #1 invoice 501 and #2 tee PO (**Ticket 101**), #3 rent (**Ticket 102**), and #4 hoodie PO (**Ticket 103**, rejected).

### message_drafts
- **Fields:** `id`, `ticket_id`, `recipient`, `subject`, `body`, `author_agent`, `status` (always `draft`), `shop_date`, `created_at`
- **Why it matters:** Customer Service's replies stay here as drafts on the board. Nothing is ever sent.

### Open Tickets at a Glance

| Ticket | Type | Requester | Ask | Tables it touches |
|---|---|---|---|---|
| **101** | customer_order | Tauhid Zaman | 1 × Classic Bulldog Tee (CC-TEE-WHITE), size S. Stock is 0, and the linked invoice 501 (Bulldog Print Co, $840.00) is open and overdue, so the vendor won't ship until it is paid. | tickets, inventory, pricing, invoices, vendors, cash_accounts, payments, desk |
| **102** | rent_notice | Elm City Properties | Rent of $2,400.00 for lease 1 (Chapel Street shop) is due 2026-09-02, which is 2 days after shop "today". | tickets, leases, cash_accounts, payments, desk |
| **103** | price_override | Yale AI Club | 20 × Basic Hoodie Big Yale (CC-HOOD-NAVY), size M, at a bulk discount. Only 8 are in stock, so the shop is 12 short. Cost is $22.00 and list price is $58.00. | tickets, inventory, pricing, vendors, cash_accounts, desk |

**Cash constraint across tickets:** checking holds $3,400.00. Paying invoice 501 ($840.00) and the rent ($2,400.00) totals $3,240.00 and would leave $160.00, which is less than restocking 12 hoodies at cost (12 × $22.00 = $264.00).

## 2. MCP Tools

The server is `mcp_server/server.py` (FastMCP, stdio). It is the **only** way agents touch shop data, and it only ever opens `data/campus_customs_new.db` (never the original). Read tools open the database read-only. When nothing matches, a tool returns `{"found": false, "message": ...}`. Every "overdue" or "days until due" figure is measured from the desk table's `date_today`, never the real calendar.

### The three core ticket tools (built in Problem 3)

| Tool | Ticket | Exact rows it pulls | Tables read |
|---|---|---|---|
| `get_invoice_and_vendor_hold(501)` | **101** (Tauhid Zaman, 1 × CC-TEE-WHITE size S) | invoice **501** · vendor **1, Bulldog Print Co** · desk date 2026-08-31 | invoices, vendors, desk |
| `get_rent_due_and_cash(1)` | **102** (Elm City Properties rent notice) | lease **1, Chapel Street shop** · cash account **checking** · desk date 2026-08-31 | leases, cash_accounts, desk |
| `check_stock_and_pricing("CC-HOOD-NAVY", "M", 20)` | **103** (Yale AI Club, 20 × CC-HOOD-NAVY size M) | inventory **CC-HOOD-NAVY / M** (and its S, L, XL rows) · pricing **CC-HOOD-NAVY** | inventory, pricing |

### get_invoice_and_vendor_hold → Ticket 101
Ticket 101 links to invoice 501: **$840.00 owed to Bulldog Print Co (vendor 1), due 2026-08-28 and 3 days overdue**. Until it is paid, Bulldog Print Co (5-day lead time) won't reprint the CC-TEE-WHITE size S the customer wants.

### get_rent_due_and_cash → Ticket 102
Ticket 102 links to lease 1: **Chapel Street shop rent of $2,400.00 owed to Elm City Properties, due 2026-09-02 (2 days away)**. The tool puts that next to the **$3,400.00 checking** balance so Accounting can prepare the payment for human approval before it goes overdue.

### check_stock_and_pricing → Ticket 103
Ticket 103 asks for 20 × CC-HOOD-NAVY size M, but **inventory holds 8, so the shop is 12 short**. The tool also returns the **$22.00 unit cost** (the floor for any bulk discount) and the **$58.00 list price**. Called as `check_stock_and_pricing("CC-TEE-WHITE", "S", 1)`, it also confirms that Ticket 101's tee has 0 in stock.

### Every MCP tool (18 total)

**Who can see it.** *Agent-visible* tools can be offered to agents, and each agent gets only the subset on its own allow-list (see section 3). *Approval-only* and *backend-only* tools (the `BACKEND_ONLY_TOOLS` list) are removed for every agent by a filtered toolset in `backend/mcp_client.py`. Only the backend routes call them: the approval routes and `/reset`.

| # | Tool | What it does | Table(s) it uses | Visibility | Main ticket(s) |
|---|---|---|---|---|---|
| 1 | `get_shop_today` | The shop's "today" | desk | Agent-visible | 101, 102, 103 |
| 2 | `list_tickets` | Ticket queue, optional status filter | tickets | Agent-visible | all |
| 3 | `get_ticket` | One ticket plus its approvals and drafts | tickets, approvals, message_drafts, desk | Agent-visible | all |
| 4 | `check_stock_and_pricing` | Stock for a SKU/size, all sizes, cost/list price, shortfall | inventory, pricing | Agent-visible | 101 (tee S = 0), 103 (hoodie M = 8 of 20) |
| 5 | `list_vendors` | Vendors, lead_days, unpaid invoices, `can_ship_now` | vendors, invoices, desk | Agent-visible | 101, 103 |
| 6 | `get_unpaid_invoices` | Unpaid invoices with days overdue | invoices, vendors, desk | Agent-visible | 101 (invoice 501) |
| 7 | `get_invoice_and_vendor_hold` | One invoice, its vendor, whether the vendor is on hold | invoices, vendors, desk | Agent-visible | 101 |
| 8 | `get_rent_due_and_cash` | Lease rent, days until due, cash cover | leases, cash_accounts, desk | Agent-visible | 102 (lease 1) |
| 9 | `get_cash_balance` | Cash, pending approvals total, cash after pending | cash_accounts, approvals, desk | Agent-visible | 101, 102, 103 |
| 10 | `calculate_margin` | Margin at a proposed price; `below_cost` flag | pricing | Agent-visible | 103 (discount floor $22.00) |
| 11 | `list_approvals` | Pending, executed, or rejected requests | approvals | Agent-visible | all money tickets |
| 12 | `create_payment_request` | PREPARES an invoice or rent payment (status `pending`, no money moves). Amount and payee come from the DB. | approvals (writes); reads invoices, vendors, leases, cash_accounts, desk | Agent-visible | 101 (invoice 501), 102 (rent) |
| 13 | `create_purchase_order_request` | PREPARES a restock PO (qty × unit_cost) and flags vendor holds | approvals (writes); reads vendors, inventory, pricing, invoices, cash_accounts, desk | Agent-visible | 101 (tee), 103 (hoodies) |
| 14 | `save_customer_draft` | Saves a customer message as a draft. It is never sent. | message_drafts (writes), desk | Agent-visible | 101, 102, 103 |
| 15 | `update_ticket_status` | Sets the status (open / in_progress / waiting_approval / resolved) and appends a note | tickets (writes), desk | Agent-visible (Boss only) | all |
| 16 | `execute_approved_payment` | **The pay tool.** Runs a human-approved request in one transaction. Refuses if cash would go negative, or if a PO's vendor still has an unpaid invoice. Updates cash_accounts, payments, the invoice (`paid`) or the lease (`next_due` +1 month), and approvals. | approvals, cash_accounts, payments, invoices, leases, vendors, desk | **Approval-only (hidden)** | 101, 102, 103 |
| 17 | `reject_approval` | Marks a pending request rejected. No money moves. | approvals | **Approval-only (hidden)** | all |
| 18 | `init_helper_tables` | Recreates the approvals and message_drafts tables after a reset. No shop data changes. | approvals, message_drafts | **Backend-only (hidden)** (used by `POST /reset`) | all |

The `approvals` and `message_drafts` tables are new. They are not in the original database, so the server creates them automatically the first time a write tool runs. That keeps everything working right after a reset.

## 3. Agents

The team lives in `backend/agents/`, with one file per agent and one system prompt per agent in `backend/prompts/`. All agents use the one model set in `backend/config.py` through Portkey. Each agent sees only the MCP tools on its allow-list, plus a `delegate(to_agent, task)` tool that can reach any teammate.

| Agent | Job | MCP tools it can see | Usually delegates to |
|---|---|---|---|
| **Boss** (`boss.py`) | Reads each ticket, decides who works on it, makes the final call, sets the ticket status, and writes the final resolution | get_shop_today, list_tickets, get_ticket, update_ticket_status, get_cash_balance, list_approvals | Inventory (stock), Facilities (rent), Accounting (money), then Customer Service (draft reply) |
| **Inventory** (`inventory.py`) | Checks stock by SKU and size, spots shortfalls, picks a vendor that can restock (lead_days plus the unpaid-invoice rule), and estimates restock cost | get_shop_today, get_ticket, check_stock_and_pricing, list_vendors, get_unpaid_invoices, get_invoice_and_vendor_hold | Accounting (to prepare a PO or the invoice payment that unblocks a vendor) |
| **Accounting** (`accounting.py`) | Watches cash and invoices, checks margins, and **PREPARES** payment and purchase-order requests. It can never execute a payment. | get_shop_today, get_ticket, get_cash_balance, get_unpaid_invoices, get_invoice_and_vendor_hold, get_rent_due_and_cash, calculate_margin, check_stock_and_pricing, list_vendors, list_approvals, create_payment_request, create_purchase_order_request | Inventory (vendor/stock facts), Facilities (lease facts), Boss (cash conflicts) |
| **Facilities** (`facilities.py`) | Handles the shop space: leases, rent amounts, due dates, and days until due | get_shop_today, get_ticket, get_rent_due_and_cash, get_cash_balance, list_approvals | Accounting (to prepare the rent payment) |
| **Customer Service** (`customer_service.py`) | Drafts honest messages to requesters. Drafts stay on the board and are never sent. | get_shop_today, get_ticket, check_stock_and_pricing, save_customer_draft | Inventory or Accounting (only to confirm a fact before writing) |

**How a run works.** `backend/runner.py` starts one MCP server process, then runs the Boss on a ticket. Every agent in that run shares one usage counter and one set of `UsageLimits`, so tokens are counted across the whole team. Every loop step is appended to `output/audit_trail.json`.

## 4. Safety and Guardrails

### Money (a real business needs these the most)
- **Human in the loop for every dollar.** Agents can only *prepare* requests (`status = pending`). No agent can see the pay tool: it is removed by a filtered toolset, and each agent also has its own allow-list, so the pay tool is blocked twice. Only the human approval route will call it.
- **Amounts come from the database, not the AI.** `create_payment_request` reads the invoice or lease amount itself, and a PO is priced at qty × unit_cost from pricing. An agent can't inflate or invent an amount.
- **No negative balances, ever.** The pay tool checks the balance inside a locked transaction and refuses if cash would drop below zero. `get_cash_balance` and every create-request result also show cash after *all* pending requests, so over-commitment is visible before anyone approves.
- **The vendor-hold rule is enforced in code.** A purchase order can't be executed while that vendor has an unpaid invoice.
- **All-or-nothing updates.** A payment updates cash_accounts, payments, the invoice or lease, and approvals together, or not at all.
- **No duplicates.** A second pending request for the same invoice, lease, or vendor/SKU/size is refused.
- **Named approver.** Every executed payment records `approved_by` (a human name), and every approval records `decided_by` and `decided_at`.

### Customers and vendors
- **Drafts only.** Customer Service saves drafts (`status = draft`). There is no send tool anywhere, and no agent can contact a vendor or landlord.
- **No internal details or promises in drafts.** The prompts forbid mentioning invoice disputes, cash, or approval ids to customers, promising dates that depend on a pending approval as certain, or offering a price below unit cost (`calculate_margin` flags `below_cost`).

### Data integrity
- **One door to the data.** Agents reach shop data only through MCP tools. The backend has no SQL of its own.
- **The original database is never modified.** Everything uses `campus_customs_new.db`. "Reset" copies the original over it before a full run.
- **Shop calendar, not the real one.** All overdue and due-date math uses the desk table's `date_today`.
- **No invented facts.** Every prompt says to report missing information plainly instead of guessing.
- **Least privilege.** Each agent sees only the tools its job needs. For example, Customer Service has no money tools and Inventory can't create requests.

### Audit and secrets
- **Full audit trail.** Every thinking, tool_call, tool_result, delegation, final, and error step is appended to `output/audit_trail.json` with timestamp, run_id, ticket_id, agent, depth, tool name and arguments, a short result, and tokens. The file is append-only and always valid JSON (it is written to a temp file first, then swapped in).
- **Key safety.** The Portkey key is read from `.env` at run time, never printed or logged, and scrubbed from audit entries if it ever appeared. `.env` is git-ignored.

### Token and runaway-loop limits
- **Delegation depth limit of 3.** Delegations deeper than that are refused with a message telling the agent to finish with what it has.
- **No self-delegation**, and unknown agent names are refused.
- **Per-run `UsageLimits` shared by the whole team.** By default: 60 model requests, 80 tool calls, and 400,000 total tokens (`backend/config.py`). The smoke test uses lower limits: 30 requests, 40 tool calls, 150,000 tokens. Hitting a limit stops the run cleanly and records `stopped_by_limit`.
- **Tool retries capped** at 2 per agent. Tool errors are shown to the model instead of crashing the run.
- **One redaction (Problem 11):** before publishing to GitHub, a single word was replaced in one audit event: the error from the first failed smoke test (run `run-b66053ae0a`). It quoted the AI provider's internal deployment name for our model, which broke the "only one model name in the project" rule, so it now reads `[provider deployment name]`. No events were removed, reordered or otherwise changed.
- **Short audit results** (max 400 characters each for tool results and other steps) keep the log readable and small. Agents' *final* answers are stored in full so a human can read the whole resolution later (changed during Problem 9; earlier entries stay as written because the log is append-only).

## 5. API Routes

`backend/main.py` (FastAPI). Start it from inside `backend/` with `uvicorn main:app --reload --port 8000`. Every route gets shop data through the MCP server. CORS allows `http://localhost:5173` and `http://127.0.0.1:5173`.

- `GET /health` - Simple check: MCP server connected, shop "today", working database present, model in use.
- `GET /tickets` - The three tickets, each with a status: `open`, `running`, `awaiting approval`, or `resolved` (resolved = run finished and no pending approvals). Also shows pending approval count and amount, and the latest run.
- `POST /tickets/{ticket_id}/run` - Starts the agent team (the Boss first) on that ticket in the background and returns a `run_id` right away (HTTP 202). Refuses a second run of the same ticket while one is going (409).
- `GET /runs/{run_id}` - Status of one run (running, completed, stopped_by_limit, or error) and the Boss's final result when done.
- `GET /events?ticket_id=&since=` - Agent events from `output/audit_trail.json`, oldest first: which agent, what it said, the tools and arguments it used, tool results, delegations, and human decisions. Each event has an `id`; pass the last one you saw as `since` to get only new events.
- `GET /approvals` - Pending payment and purchase-order requests prepared by agents, with the total.
- `POST /approvals/{approval_id}/approve` - A human clicked Approve. This is the **only place money moves**: it calls the MCP pay tool, which refuses (HTTP 409 with a clear message) if cash would go negative or a vendor is still on hold, and otherwise updates cash_accounts, payments, the invoice or lease, and approvals. Optional body: `{"approved_by": "name"}`.
- `POST /approvals/{approval_id}/reject` - Marks the request rejected. No money moves. Optional body: `{"decided_by": "name", "note": "why"}`.
- `GET /cash` - Current checking balance from cash_accounts, plus the pending total and cash left after pending.
- `POST /reset` - Copies `data/campus_customs.db` over `data/campus_customs_new.db` (the original is only read), recreates the helper tables, and clears in-memory run state. It keeps `output/audit_trail.json`, and refuses while a run is in progress (409).

After every approve or reject, the backend writes a `human_decision` event to the audit trail. **Status sync:** after every approve or reject, and again whenever a run finishes, the backend checks that ticket. If its run is done and nothing is still pending, a ticket that is `in_progress` or `waiting_approval` is set to `resolved` through the MCP `update_ticket_status` tool, and a `status_sync` event is logged. This keeps the database in step with the board's "resolved" stamp. It was added after the full run, when tickets 101 and 103 were left stale.

## 6. Dashboard

The **Campus Customs Ops Desk** is a React + Vite + TypeScript board in `frontend/` (run with `npm run dev`, open http://localhost:5173). It talks to the backend through one constant, `API_BASE` in `frontend/src/config.ts`. Full design notes are in **[design.md](design.md)**.

- **Layout:** a dark "control room" in three columns.
  - **Left:** the ticket queue, with status pills (open / running / awaiting approval / resolved).
  - **Center:** the selected ticket, a ▶ Start button, the live activity feed, a "who called whom" delegation map, and a summary card per agent.
  - **Right:** the checking balance and the approval cards.
- **Live activity:** the board polls `GET /events` every 1.5 seconds with a `since` cursor. Each agent has its own color, emoji avatar and name (Boss 🧭 amber, Inventory 📦 teal, Accounting 🧮 green, Facilities 🏢 violet, Customer Service 💬 pink, You ✋ white). Rows show tool calls with their arguments, hand-offs (indented by depth), and final answers as speech bubbles.
- **Money:**
  - Each approval card shows the vendor, amount, reason and the agent that prepared it.
  - **Approve** names the exact amount on the button. **Reject** asks for a reason.
  - A refusal from the pay tool shows as "💸 Not enough cash: payment refused".
  - The checking balance is always visible. It counts down and flashes red with a floating "−$840.00" when a payment goes through.
  - A bar shows how much cash is already promised to pending requests.
- **Resolved tickets** get a red rubber **RESOLVED** stamp that drops onto the ticket card and header, plus a toast message.
- **Reset database** has a confirmation dialog and is disabled while a run is going.
- **Screenshots** of the board for each resolved ticket are in [resolved_board.html](resolved_board.html). They're taken with Playwright by `tools/capture_board.py`.

## 7. Full Run Results

On 2026-10-12, after a reset (starting checking **$3,400.00**, see [starting_balance.txt](starting_balance.txt)), all three tickets were run on the board, and a human approved or rejected each request. Expected vs. actual for each ticket, and the cash walk-through, are in [desk_tickets.html](desk_tickets.html). Structured results are in [resolved_tickets.json](resolved_tickets.json).

| Ticket | Specialists used | Hand-offs | Tokens | Human decisions | Cash change |
|---|---|---|---|---|---|
| 101 Bulldog tee | Inventory, Accounting, Customer Service | 5 | 75,419 | #1 invoice 501 approved; #2 tee PO approved | −$840.00 − $8.00 |
| 102 Rent due | Facilities, Accounting, Customer Service | 4 | 48,040 | #3 rent approved | −$2,400.00 |
| 103 Bulk hoodies | Inventory, Accounting, Customer Service | 4 | 63,434 | #4 hoodie PO **rejected** (not enough cash) | $0.00 |

**Cash check:** $3,400.00 − $3,248.00 = **$152.00**, which equals `cash_accounts.balance` for checking in the working database.

**Lessons for the harness:**
1. The Boss tends to call Accounting more than once, and brings in Customer Service even for a landlord notice. The prompts could be tighter about "one hand-off per specialist" and "no reply needed for rent notices".
2. Nobody noticed that invoice 501 was already the rush reprint of the size-S tee, so a possible double order was approved.
3. When a human approves or rejects *during* a run, the Boss can finish with stale facts. On ticket 103, the database status stayed `waiting_approval` even though the PO had been rejected, and the Boss left 101 `in_progress`. **Fixed:** the Shop manager formally closed both as `resolved` with `update_ticket_status` (logged as `human_decision` events), and the backend now re-syncs a ticket's status whenever a run ends (see section 5). All three tickets are now `resolved` in `data/campus_customs_new.db`.
