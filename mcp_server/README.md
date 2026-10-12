# Campus Customs MCP Server

## What it is for
This is an MCP (Model Context Protocol) server. It is the **only** way the AI agents get facts about the Campus Customs shop, or change anything in it. Agents call its tools to look up real rows from the database instead of guessing.

## Which database it uses
It uses **`data/campus_customs_new.db`**, the working copy. The path is built from the location of `server.py`, so the server works no matter which folder you run it from.

- It never opens the original `data/campus_customs.db`.
- Read tools open the working copy **read-only**. Only the write tools listed below change it.
- If the working copy is missing, the tools report an error instead of creating one. To reset, copy `data/campus_customs.db` over `data/campus_customs_new.db` (or run `.venv\Scripts\python -m backend.db_reset`).
- Two extra tables, `approvals` and `message_drafts`, are created automatically the first time they're needed, so everything still works after a reset.

## How to run it
From the `hw5` folder:

```
.venv\Scripts\python mcp_server/server.py
```

It talks over **stdio** (standard input/output), so it sits quietly waiting for an MCP client such as Claude Code or the agent backend. Press **Ctrl+C** to stop it. The backend starts it automatically, so you rarely need to run it yourself.

## The tools (18)

"Overdue" and "days until due" are always measured against the shop's "today" in the `desk` table, never the real calendar date. When nothing matches, a tool returns `{"found": false, "message": "..."}`.

### Agent-visible: read
| Tool | Inputs | Tables | Helps with |
|---|---|---|---|
| `get_shop_today` | none | desk | The shop's "today" (2026-08-31) |
| `list_tickets` | `status` (optional) | tickets | The ticket queue |
| `get_ticket` | `ticket_id` | tickets, approvals, message_drafts | One ticket plus its approvals and drafts |
| `check_stock_and_pricing` | `sku`, `size`, `qty_requested` | inventory, pricing | **103**: CC-HOOD-NAVY M has 8 of 20. **101**: CC-TEE-WHITE S has 0. |
| `list_vendors` | none | vendors, invoices | Lead times, and which vendors can ship now |
| `get_unpaid_invoices` | `vendor_id` (optional) | invoices, vendors | **101**: invoice 501 is 3 days overdue |
| `get_invoice_and_vendor_hold` | `invoice_id` | invoices, vendors | **101**: Bulldog Print Co is on hold until 501 is paid |
| `get_rent_due_and_cash` | `lease_id` | leases, cash_accounts | **102**: $2,400 rent due 2026-09-02 vs. $3,400 cash |
| `get_cash_balance` | none | cash_accounts, approvals | Cash, pending total, cash after pending |
| `calculate_margin` | `sku`, `unit_price`, `qty` | pricing | **103**: discount floor (unit cost $22.00) |
| `list_approvals` | `status` (default pending) | approvals | What's already waiting for a human |

### Agent-visible: prepare, draft, update (no money moves)
| Tool | Inputs | Writes to | What it does |
|---|---|---|---|
| `create_payment_request` | `kind` (invoice/rent), `ref_id`, `reason`, `requested_by`, `ticket_id` | approvals | PREPARES a payment as `pending`. Amount and payee come from the database. |
| `create_purchase_order_request` | `vendor_id`, `sku`, `size`, `qty`, `reason`, `requested_by`, `ticket_id` | approvals | PREPARES a restock PO (qty × unit_cost). Flags any unpaid invoice that blocks the vendor. |
| `save_customer_draft` | `recipient`, `subject`, `body`, `author_agent`, `ticket_id` | message_drafts | Saves a draft. **Never sent.** |
| `update_ticket_status` | `ticket_id`, `status`, `note`, `updated_by` | tickets | Status: open / in_progress / waiting_approval / resolved |

### Approval-only and backend-only (hidden from every agent)
These are removed from every agent's tool list by a filtered toolset in `backend/mcp_client.py` (the `BACKEND_ONLY_TOOLS` list). Only the backend routes call them.

| Tool | Inputs | Writes to | What it does |
|---|---|---|---|
| `execute_approved_payment` | `approval_id`, `approved_by` | cash_accounts, payments, invoices or leases, approvals | **The pay tool.** Refuses if cash would go negative, or if a PO's vendor still has an unpaid invoice. Otherwise, in one transaction, it lowers the cash balance, adds a payments row, marks the invoice `paid` (or moves the lease's `next_due` forward one month), and marks the approval `executed`. |
| `reject_approval` | `approval_id`, `decided_by`, `note` | approvals | Marks a pending request `rejected`. No money moves. |
| `init_helper_tables` | none | approvals, message_drafts | Recreates the two helper tables after a reset (`POST /reset`). No shop data changes. |
