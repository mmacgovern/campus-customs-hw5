"""Campus Customs MCP server.

The ONLY way agents touch shop data. Run over stdio with:

    python mcp_server/server.py

Only data/campus_customs_new.db (the working copy) is ever opened.
The original data/campus_customs.db is never touched.

Tools come in two groups:
- Agent-visible tools: read shop data, prepare (never execute) payment and
  purchase-order requests, save customer message drafts, update ticket status.
- Backend-only tools (BACKEND_ONLY_TOOLS): execute or reject an approval, and
  recreate the helper tables after a reset.
  The backend hides these from every agent; only the human approval route
  calls them.
"""

import calendar
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path

from fastmcp import FastMCP

# Build the path from this file's location so it works from any folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "campus_customs_new.db"

# Tools that move money or decide approvals. Never shown to agents.
BACKEND_ONLY_TOOLS = {"execute_approved_payment", "reject_approval", "init_helper_tables"}

TICKET_STATUSES = {"open", "in_progress", "waiting_approval", "resolved"}
PAYMENT_KINDS = {"invoice", "rent"}

mcp = FastMCP("Campus Customs")


# ---------------------------------------------------------------- helpers

def _check_db() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Working database not found at {DB_PATH}. "
            "Reset it by copying data/campus_customs.db to data/campus_customs_new.db."
        )


def _connect() -> sqlite3.Connection:
    """Open the working database read-only. Never creates or copies a file."""
    _check_db()
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _connect_rw() -> sqlite3.Connection:
    """Open the working database for writing, creating the extra tables if missing.

    The extra tables (approvals, message_drafts) are not in the original
    database, so they are created on demand. That way everything still works
    right after a reset.
    """
    _check_db()
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=rw", uri=True)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,              -- invoice | rent | purchase_order
            ref_id INTEGER,                  -- invoice id, lease id, or vendor id
            ticket_id INTEGER,
            payee TEXT NOT NULL,
            amount REAL NOT NULL,
            account TEXT NOT NULL,
            sku TEXT,
            size TEXT,
            qty INTEGER,
            reason TEXT NOT NULL,
            requested_by TEXT NOT NULL,
            status TEXT NOT NULL,            -- pending | executed | rejected
            shop_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            decided_by TEXT,
            decided_at TEXT,
            decision_note TEXT,
            payment_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS message_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            author_agent TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            shop_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    return conn


@contextmanager
def _db(write: bool = False):
    """Open the working database, commit on success, and always close it."""
    conn = _connect_rw() if write else _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone() is not None


def _shop_today(conn: sqlite3.Connection) -> str:
    """The shop's 'today' from the desk table (column date_today or data_today)."""
    row = conn.execute("SELECT * FROM desk LIMIT 1").fetchone()
    if row is None:
        raise ValueError("The desk table has no row, so the shop's 'today' is unknown.")
    for col in ("date_today", "data_today"):
        if col in row.keys():
            return row[col]
    raise ValueError("The desk table has no date_today or data_today column.")


def _days_between(start: str, end: str) -> int:
    """Whole days from start to end (ISO dates). Positive when end is later."""
    return (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days


def _add_one_month(iso_day: str) -> str:
    d = date.fromisoformat(iso_day[:10])
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _open_invoices(conn: sqlite3.Connection, vendor_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM invoices WHERE vendor_id = ? AND status != 'paid' ORDER BY due_date",
        (vendor_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _total_cash(conn: sqlite3.Connection) -> float:
    return conn.execute("SELECT COALESCE(SUM(balance), 0) FROM cash_accounts").fetchone()[0]


def _pending_total(conn: sqlite3.Connection) -> float:
    if not _table_exists(conn, "approvals"):
        return 0.0
    return conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM approvals WHERE status = 'pending'"
    ).fetchone()[0]


def _duplicate_pending(conn, kind: str, ref_id: int, sku=None, size=None) -> dict | None:
    row = conn.execute(
        "SELECT * FROM approvals WHERE status = 'pending' AND kind = ? AND ref_id = ? "
        "AND COALESCE(sku, '') = COALESCE(?, '') AND COALESCE(size, '') = COALESCE(?, '')",
        (kind, ref_id, sku, size),
    ).fetchone()
    return dict(row) if row else None


# ------------------------------------------------- agent-visible: read tools

@mcp.tool
def get_shop_today() -> dict:
    """Return the shop's 'today' date from the desk table.

    Always use this date (never the real calendar date) to decide what is
    overdue or how many days remain until something is due.
    """
    with _db() as conn:
        return {"shop_today": _shop_today(conn)}


@mcp.tool
def list_tickets(status: str | None = None) -> dict:
    """List tickets, optionally filtered by status (open, in_progress, waiting_approval, resolved).

    Args:
        status: Only return tickets with this status. Leave empty for all.
    """
    with _db() as conn:
        if status:
            rows = conn.execute("SELECT * FROM tickets WHERE status = ? ORDER BY id", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    if not rows:
        return {"found": False, "message": f"No tickets{' with status ' + status if status else ''}."}
    return {"found": True, "tickets": [dict(r) for r in rows]}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Get one ticket by id, plus any approvals and message drafts already linked to it.

    Args:
        ticket_id: The ticket id, e.g. 101.
    """
    with _db() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"found": False, "message": f"No ticket with id {ticket_id}."}
        approvals = drafts = []
        if _table_exists(conn, "approvals"):
            approvals = [dict(r) for r in conn.execute(
                "SELECT * FROM approvals WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
        if _table_exists(conn, "message_drafts"):
            drafts = [dict(r) for r in conn.execute(
                "SELECT * FROM message_drafts WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
        today = _shop_today(conn)
    return {"found": True, "shop_today": today, "ticket": dict(row),
            "approvals": approvals, "message_drafts": drafts}


@mcp.tool
def check_stock_and_pricing(sku: str, size: str, qty_requested: int = 1) -> dict:
    """Check stock for one SKU and size, plus its cost and list price.

    Use this for Ticket 103 (CC-HOOD-NAVY size M, 20 requested) and the stock
    side of Ticket 101 (CC-TEE-WHITE size S, 1 requested). Returns the
    inventory row for that size, stock in every size of the SKU, the pricing
    row (unit_cost is the floor for any discount), and how many units are
    short of the request.

    Args:
        sku: Product code, e.g. "CC-HOOD-NAVY".
        size: Size code, e.g. "M", or "OS" for one-size items.
        qty_requested: How many units the customer wants (default 1).
    """
    with _db() as conn:
        item = conn.execute(
            "SELECT * FROM inventory WHERE sku = ? AND size = ?", (sku, size)
        ).fetchone()
        all_sizes = conn.execute(
            "SELECT * FROM inventory WHERE sku = ?", (sku,)
        ).fetchall()
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()

    if not all_sizes:
        return {"found": False, "message": f"No inventory rows for SKU {sku}."}
    if item is None:
        sizes = ", ".join(r["size"] for r in all_sizes)
        return {
            "found": False,
            "message": f"SKU {sku} has no size {size}. Sizes on file: {sizes}.",
        }

    shortfall = max(qty_requested - item["qty"], 0)
    return {
        "found": True,
        "item": dict(item),
        "all_sizes": [dict(r) for r in all_sizes],
        "pricing": dict(price) if price else None,
        "qty_requested": qty_requested,
        "can_fill_from_stock": shortfall == 0,
        "shortfall": shortfall,
        "restock_cost_at_unit_cost": shortfall * price["unit_cost"] if price else None,
    }


@mcp.tool
def list_vendors() -> dict:
    """List every vendor with its specialty, lead time (lead_days), unpaid invoices,
    and whether it can ship right now.

    A vendor will NOT ship new product while it has any unpaid invoice, so
    can_ship_now is false whenever open_invoices is not empty.
    """
    with _db() as conn:
        vendors = conn.execute("SELECT * FROM vendors ORDER BY id").fetchall()
        today = _shop_today(conn)
        out = []
        for v in vendors:
            open_inv = _open_invoices(conn, v["id"])
            out.append({**dict(v), "open_invoices": open_inv,
                        "unpaid_total": sum(i["amount"] for i in open_inv),
                        "can_ship_now": not open_inv})
    if not out:
        return {"found": False, "message": "No vendors on file."}
    return {"found": True, "shop_today": today, "vendors": out}


@mcp.tool
def get_unpaid_invoices(vendor_id: int | None = None) -> dict:
    """List unpaid invoices (status not 'paid'), optionally for one vendor,
    with days overdue measured from the shop's 'today'.

    Args:
        vendor_id: Only this vendor's invoices. Leave empty for all vendors.
    """
    with _db() as conn:
        today = _shop_today(conn)
        sql = ("SELECT i.*, v.name AS vendor_name FROM invoices i "
               "JOIN vendors v ON v.id = i.vendor_id WHERE i.status != 'paid'")
        params: tuple = ()
        if vendor_id is not None:
            sql += " AND i.vendor_id = ?"
            params = (vendor_id,)
        rows = conn.execute(sql + " ORDER BY i.due_date", params).fetchall()
    if not rows:
        return {"found": False, "shop_today": today, "message": "No unpaid invoices."}
    invoices = []
    for r in rows:
        late = _days_between(r["due_date"], today)
        invoices.append({**dict(r), "days_overdue": max(late, 0), "is_overdue": late > 0})
    return {"found": True, "shop_today": today, "invoices": invoices,
            "total_unpaid": sum(i["amount"] for i in invoices)}


@mcp.tool
def get_invoice_and_vendor_hold(invoice_id: int) -> dict:
    """Look up a vendor invoice, its vendor, and whether it blocks new shipments.

    Use this for Ticket 101 (invoice 501): the vendor will not ship new
    product while it has any unpaid invoice. Returns the invoice row, the
    vendor row (including lead_days), the shop's 'today', how many days the
    invoice is overdue, every open invoice for that vendor, and whether the
    vendor is currently on hold.

    Args:
        invoice_id: The invoice id, e.g. 501.
    """
    with _db() as conn:
        invoice = conn.execute(
            "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
        ).fetchone()
        if invoice is None:
            return {"found": False, "message": f"No invoice with id {invoice_id}."}

        vendor = conn.execute(
            "SELECT * FROM vendors WHERE id = ?", (invoice["vendor_id"],)
        ).fetchone()
        open_invoices = _open_invoices(conn, invoice["vendor_id"])
        today = _shop_today(conn)

    days_late = _days_between(invoice["due_date"], today)
    return {
        "found": True,
        "shop_today": today,
        "invoice": dict(invoice),
        "days_overdue": max(days_late, 0),
        "is_overdue": invoice["status"] != "paid" and days_late > 0,
        "vendor": dict(vendor) if vendor else None,
        "vendor_open_invoices": open_invoices,
        "vendor_on_hold": len(open_invoices) > 0,
    }


@mcp.tool
def get_rent_due_and_cash(lease_id: int) -> dict:
    """Look up a lease's rent, when it is due, and whether cash covers it.

    Use this for Ticket 102 (lease 1, Chapel Street shop). Returns the lease
    row, the shop's 'today', days until rent is due (negative means
    overdue), every cash account row, and whether the total cash balance
    covers one month's rent. This tool only reads; it never pays.

    Args:
        lease_id: The lease id, e.g. 1.
    """
    with _db() as conn:
        lease = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
        if lease is None:
            return {"found": False, "message": f"No lease with id {lease_id}."}
        accounts = conn.execute("SELECT * FROM cash_accounts").fetchall()
        today = _shop_today(conn)

    total_cash = sum(a["balance"] for a in accounts)
    days_until_due = _days_between(today, lease["next_due"])
    return {
        "found": True,
        "shop_today": today,
        "lease": dict(lease),
        "days_until_due": days_until_due,
        "is_overdue": days_until_due < 0,
        "cash_accounts": [dict(a) for a in accounts],
        "total_cash": total_cash,
        "cash_covers_rent": total_cash >= lease["monthly_rent"],
        "cash_after_rent": total_cash - lease["monthly_rent"],
    }


@mcp.tool
def get_cash_balance() -> dict:
    """Return every cash account, the total cash, money already promised to
    pending approvals, and cash left after those pending approvals.

    Cash only goes out in this shop (no revenue is modeled).
    """
    with _db() as conn:
        accounts = [dict(a) for a in conn.execute("SELECT * FROM cash_accounts")]
        total = _total_cash(conn)
        pending = _pending_total(conn)
        today = _shop_today(conn)
    return {"shop_today": today, "cash_accounts": accounts, "total_cash": total,
            "pending_approvals_total": pending, "cash_after_pending": total - pending}


@mcp.tool
def calculate_margin(sku: str, unit_price: float, qty: int = 1) -> dict:
    """Check the margin of selling a SKU at a proposed unit price.

    Uses unit_cost and list_price from the pricing table. Selling below
    unit_cost loses money, so below_cost is a hard stop for any discount.

    Args:
        sku: Product code, e.g. "CC-HOOD-NAVY".
        unit_price: Proposed price per unit (e.g. a discounted price).
        qty: Number of units (default 1).
    """
    with _db() as conn:
        p = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if p is None:
        return {"found": False, "message": f"No pricing row for SKU {sku}."}
    cost, lst = p["unit_cost"], p["list_price"]
    margin = unit_price - cost
    return {
        "found": True,
        "pricing": dict(p),
        "unit_price": unit_price,
        "qty": qty,
        "discount_pct_off_list": round((lst - unit_price) / lst * 100, 2) if lst else None,
        "margin_per_unit": round(margin, 2),
        "margin_pct_of_price": round(margin / unit_price * 100, 2) if unit_price else None,
        "total_revenue": round(unit_price * qty, 2),
        "total_cost": round(cost * qty, 2),
        "total_margin": round(margin * qty, 2),
        "below_cost": unit_price < cost,
    }


@mcp.tool
def list_approvals(status: str | None = "pending") -> dict:
    """List payment / purchase-order approval requests (default: pending ones).

    Args:
        status: pending, executed, or rejected. Leave empty for all.
    """
    with _db() as conn:
        if not _table_exists(conn, "approvals"):
            return {"found": False, "message": "No approval requests yet."}
        if status:
            rows = conn.execute("SELECT * FROM approvals WHERE status = ? ORDER BY id", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM approvals ORDER BY id").fetchall()
    if not rows:
        return {"found": False, "message": f"No {status or ''} approval requests.".replace("  ", " ")}
    return {"found": True, "approvals": [dict(r) for r in rows]}


# ------------------------------------- agent-visible: prepare / draft / status

@mcp.tool
def create_payment_request(kind: str, ref_id: int, reason: str, requested_by: str,
                           ticket_id: int | None = None) -> dict:
    """PREPARE a payment for human approval. This does NOT move any money.

    The amount and payee are taken from the database, never from the caller:
    kind="invoice" pays the full unpaid amount of invoice ref_id to its vendor;
    kind="rent" pays one month's rent of lease ref_id to its landlord.
    The request is stored as 'pending' in the approvals table until a human
    approves or rejects it.

    Args:
        kind: "invoice" or "rent".
        ref_id: The invoice id (e.g. 501) or lease id (e.g. 1).
        reason: One or two sentences on why this payment is needed.
        requested_by: Name of the agent preparing it, e.g. "accounting".
        ticket_id: The ticket this payment helps resolve, if any.
    """
    if kind not in PAYMENT_KINDS:
        return {"created": False, "message": f"kind must be one of {sorted(PAYMENT_KINDS)}."}
    with _db(write=True) as conn:
        if kind == "invoice":
            row = conn.execute(
                "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id "
                "WHERE i.id = ?", (ref_id,)).fetchone()
            if row is None:
                return {"created": False, "message": f"No invoice with id {ref_id}."}
            if row["status"] == "paid":
                return {"created": False, "message": f"Invoice {ref_id} is already paid."}
            payee, amount = row["vendor_name"], row["amount"]
        else:
            row = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if row is None:
                return {"created": False, "message": f"No lease with id {ref_id}."}
            payee, amount = row["landlord"], row["monthly_rent"]

        dup = _duplicate_pending(conn, kind, ref_id)
        if dup:
            return {"created": False, "message": "A pending request for this already exists.",
                    "approval": dup}

        account = conn.execute(
            "SELECT name FROM cash_accounts ORDER BY balance DESC LIMIT 1").fetchone()
        if account is None:
            return {"created": False, "message": "No cash account on file."}
        today = _shop_today(conn)
        cur = conn.execute(
            "INSERT INTO approvals (kind, ref_id, ticket_id, payee, amount, account, reason, "
            "requested_by, status, shop_date, created_at) VALUES (?,?,?,?,?,?,?,?, 'pending', ?, ?)",
            (kind, ref_id, ticket_id, payee, amount, account["name"], reason, requested_by, today, _now()))
        approval = dict(conn.execute("SELECT * FROM approvals WHERE id = ?", (cur.lastrowid,)).fetchone())
        total, pending = _total_cash(conn), _pending_total(conn)
    return {"created": True, "approval": approval,
            "note": "Pending human approval. No money has moved.",
            "total_cash": total, "pending_approvals_total": pending,
            "cash_after_all_pending": total - pending,
            "warning": None if total - pending >= 0 else
                       "Pending requests exceed cash. A human must choose which to approve."}


@mcp.tool
def create_purchase_order_request(vendor_id: int, sku: str, size: str, qty: int,
                                  reason: str, requested_by: str,
                                  ticket_id: int | None = None) -> dict:
    """PREPARE a purchase order (restock) for human approval. No money moves.

    The amount is qty x unit_cost from the pricing table. If the vendor still
    has an unpaid invoice it will not ship, so the response flags
    blocked_until_invoices_paid; the PO cannot be executed until those are paid.

    Args:
        vendor_id: Vendor to buy from (see list_vendors), e.g. 1.
        sku: Product code, e.g. "CC-TEE-WHITE".
        size: Size code, e.g. "S".
        qty: Units to order (must be at least 1).
        reason: One or two sentences on why this order is needed.
        requested_by: Name of the agent preparing it, e.g. "inventory".
        ticket_id: The ticket this order helps resolve, if any.
    """
    if qty < 1:
        return {"created": False, "message": "qty must be at least 1."}
    with _db(write=True) as conn:
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return {"created": False, "message": f"No vendor with id {vendor_id}."}
        item = conn.execute("SELECT * FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        if item is None:
            return {"created": False, "message": f"No inventory row for {sku} size {size}."}
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return {"created": False, "message": f"No pricing row for {sku}."}
        dup = _duplicate_pending(conn, "purchase_order", vendor_id, sku, size)
        if dup:
            return {"created": False, "message": "A pending PO for this vendor/SKU/size already exists.",
                    "approval": dup}
        account = conn.execute(
            "SELECT name FROM cash_accounts ORDER BY balance DESC LIMIT 1").fetchone()
        if account is None:
            return {"created": False, "message": "No cash account on file."}
        amount = round(qty * price["unit_cost"], 2)
        today = _shop_today(conn)
        cur = conn.execute(
            "INSERT INTO approvals (kind, ref_id, ticket_id, payee, amount, account, sku, size, qty, "
            "reason, requested_by, status, shop_date, created_at) "
            "VALUES ('purchase_order',?,?,?,?,?,?,?,?,?,?, 'pending', ?, ?)",
            (vendor_id, ticket_id, vendor["name"], amount, account["name"], sku, size, qty,
             reason, requested_by, today, _now()))
        approval = dict(conn.execute("SELECT * FROM approvals WHERE id = ?", (cur.lastrowid,)).fetchone())
        open_inv = _open_invoices(conn, vendor_id)
        total, pending = _total_cash(conn), _pending_total(conn)
    return {"created": True, "approval": approval,
            "note": "Pending human approval. No money has moved.",
            "vendor_lead_days": vendor["lead_days"],
            "blocked_until_invoices_paid": [i["id"] for i in open_inv],
            "total_cash": total, "pending_approvals_total": pending,
            "cash_after_all_pending": total - pending}


@mcp.tool
def save_customer_draft(recipient: str, subject: str, body: str, author_agent: str,
                        ticket_id: int | None = None) -> dict:
    """Save a customer message as a DRAFT on the board. It is never sent.

    Args:
        recipient: Who the message is for (name as on the ticket).
        subject: Short subject line.
        body: The full draft message.
        author_agent: Name of the agent writing it, e.g. "customer_service".
        ticket_id: The ticket this draft belongs to, if any.
    """
    with _db(write=True) as conn:
        today = _shop_today(conn)
        cur = conn.execute(
            "INSERT INTO message_drafts (ticket_id, recipient, subject, body, author_agent, status, "
            "shop_date, created_at) VALUES (?,?,?,?,?, 'draft', ?, ?)",
            (ticket_id, recipient, subject, body, author_agent, today, _now()))
        draft = dict(conn.execute("SELECT * FROM message_drafts WHERE id = ?", (cur.lastrowid,)).fetchone())
    return {"saved": True, "draft": draft, "note": "Saved as a draft only. Nothing was sent."}


@mcp.tool
def update_ticket_status(ticket_id: int, status: str, note: str, updated_by: str) -> dict:
    """Change a ticket's status and append a note to it.

    Args:
        ticket_id: The ticket id, e.g. 101.
        status: open, in_progress, waiting_approval, or resolved.
        note: Short note explaining the change (appended to the ticket notes).
        updated_by: Name of the agent making the change.
    """
    if status not in TICKET_STATUSES:
        return {"updated": False, "message": f"status must be one of {sorted(TICKET_STATUSES)}."}
    with _db(write=True) as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return {"updated": False, "message": f"No ticket with id {ticket_id}."}
        today = _shop_today(conn)
        notes = (row["notes"] or "") + f"\n[{today} {updated_by}] {status}: {note}"
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?",
                     (status, notes.strip(), ticket_id))
        ticket = dict(conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone())
    return {"updated": True, "ticket": ticket}


# -------------------------------------- approval-only (hidden from agents)

@mcp.tool
def execute_approved_payment(approval_id: int, approved_by: str) -> dict:
    """APPROVAL-ONLY. Execute a pending approval after a human approved it.

    Hidden from every agent; only the backend approval route calls this.
    Refuses if cash would go negative, or if a purchase order's vendor still
    has an unpaid invoice. On success it updates every related table in one
    transaction: cash_accounts (balance down), payments (new row),
    invoices (status 'paid') or leases (next_due moves one month), and
    approvals (status 'executed').

    Args:
        approval_id: The approval request id.
        approved_by: Name of the human who approved it.
    """
    if not approved_by or not approved_by.strip():
        return {"paid": False, "message": "A human approver name is required."}
    conn = _connect_rw()
    try:
        conn.execute("BEGIN IMMEDIATE")
        a = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if a is None:
            conn.rollback()
            return {"paid": False, "message": f"No approval with id {approval_id}."}
        if a["status"] != "pending":
            conn.rollback()
            return {"paid": False, "message": f"Approval {approval_id} is {a['status']}, not pending."}

        acct = conn.execute("SELECT * FROM cash_accounts WHERE name = ?", (a["account"],)).fetchone()
        if acct is None:
            conn.rollback()
            return {"paid": False, "message": f"Cash account {a['account']} not found."}
        if acct["balance"] - a["amount"] < 0:
            conn.rollback()
            return {"paid": False, "refused": True,
                    "message": (f"Refused: {a['account']} has {acct['balance']:.2f}, payment is "
                                f"{a['amount']:.2f}. Balances may never go negative.")}

        today = _shop_today(conn)
        changes: dict = {}
        if a["kind"] == "invoice":
            inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (a["ref_id"],)).fetchone()
            if inv is None or inv["status"] == "paid":
                conn.rollback()
                return {"paid": False, "message": f"Invoice {a['ref_id']} is missing or already paid."}
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (a["ref_id"],))
            changes["invoice"] = {"id": a["ref_id"], "status": "paid"}
        elif a["kind"] == "rent":
            lease = conn.execute("SELECT * FROM leases WHERE id = ?", (a["ref_id"],)).fetchone()
            if lease is None:
                conn.rollback()
                return {"paid": False, "message": f"Lease {a['ref_id']} not found."}
            new_due = _add_one_month(lease["next_due"])
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (new_due, a["ref_id"]))
            changes["lease"] = {"id": a["ref_id"], "old_next_due": lease["next_due"], "next_due": new_due}
        elif a["kind"] == "purchase_order":
            blocking = _open_invoices(conn, a["ref_id"])
            if blocking:
                conn.rollback()
                return {"paid": False, "refused": True,
                        "message": "Refused: vendor still has unpaid invoice(s) "
                                   f"{[i['id'] for i in blocking]} and will not ship."}
            vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (a["ref_id"],)).fetchone()
            changes["purchase_order"] = {"vendor_id": a["ref_id"], "sku": a["sku"], "size": a["size"],
                                         "qty": a["qty"], "lead_days": vendor["lead_days"] if vendor else None}
        else:
            conn.rollback()
            return {"paid": False, "message": f"Unknown approval kind {a['kind']}."}

        new_balance = acct["balance"] - a["amount"]
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
                     (new_balance, today, a["account"]))
        cur = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?,?,?,?,?,?)",
            (a["kind"], a["ref_id"], a["amount"], a["account"], today, approved_by))
        conn.execute(
            "UPDATE approvals SET status = 'executed', decided_by = ?, decided_at = ?, payment_id = ? "
            "WHERE id = ?", (approved_by, _now(), cur.lastrowid, approval_id))
        conn.commit()
        payment = dict(conn.execute("SELECT * FROM payments WHERE id = ?", (cur.lastrowid,)).fetchone())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"paid": True, "payment": payment, "new_balance": new_balance,
            "account": a["account"], "updated": changes}


@mcp.tool
def init_helper_tables() -> dict:
    """BACKEND-ONLY. Create the approvals and message_drafts tables if missing.

    Called by the backend right after a reset (the original database does not
    have these tables). Hidden from every agent. Changes no shop data.
    """
    with _db(write=True) as conn:
        present = [n for n in ("approvals", "message_drafts") if _table_exists(conn, n)]
    return {"ready": True, "helper_tables": present}


@mcp.tool
def reject_approval(approval_id: int, decided_by: str, note: str = "") -> dict:
    """APPROVAL-ONLY. Mark a pending approval as rejected by a human. No money moves.

    Args:
        approval_id: The approval request id.
        decided_by: Name of the human rejecting it.
        note: Optional reason.
    """
    with _db(write=True) as conn:
        a = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if a is None:
            return {"rejected": False, "message": f"No approval with id {approval_id}."}
        if a["status"] != "pending":
            return {"rejected": False, "message": f"Approval {approval_id} is {a['status']}, not pending."}
        conn.execute(
            "UPDATE approvals SET status = 'rejected', decided_by = ?, decided_at = ?, decision_note = ? "
            "WHERE id = ?", (decided_by, _now(), note, approval_id))
        row = dict(conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone())
    return {"rejected": True, "approval": row}


if __name__ == "__main__":
    mcp.run(show_banner=False)  # stdio transport by default
