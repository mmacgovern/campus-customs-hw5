"""Campus Customs API (FastAPI).

Start it from INSIDE the backend/ folder:
    uvicorn main:app --reload --port 8000

All shop data flows through the MCP server. This file never opens the
database itself (the only file work is the reset copy and reading the
audit trail).
"""

import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make `backend.*` importable when uvicorn is started from inside backend/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from backend.audit import append_event, read_events  # noqa: E402
from backend.config import MODEL_NAME, WORKING_DB  # noqa: E402
from backend.db_reset import reset_working_db  # noqa: E402
from backend.runner import new_run_id, run_ticket  # noqa: E402
from backend.worker import worker  # noqa: E402


# ------------------------------------------------------------- run state
# In memory only. Cleared by POST /reset and when the server restarts.
RUNS: dict[str, dict[str, Any]] = {}          # run_id -> info
LATEST_RUN: dict[int, str] = {}               # ticket_id -> latest run_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_running(ticket_id: int | None = None) -> bool:
    return any(r["status"] == "running" and (ticket_id is None or r["ticket_id"] == ticket_id)
               for r in RUNS.values())


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker.start()
    yield
    worker.stop()


app = FastAPI(title="Campus Customs Multi-Agent Operations", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------- helpers

async def _pending_approvals() -> list[dict]:
    data = await worker.call_tool("list_approvals", status="pending")
    return data.get("approvals", []) if data.get("found") else []


async def _maybe_resolve(ticket_id: int | None, reason: str = "All approvals decided by a human.") -> None:
    """Keep the database in step with the board's rule: once a ticket's run has finished and
    nothing is pending for it, its status becomes 'resolved'.

    Called after every human approve/reject, and again when a run ends (the Boss may have
    written a status before a human decided mid-run, which left it stale).
    """
    if ticket_id is None or _is_running(ticket_id):
        return
    if any(a["ticket_id"] == ticket_id for a in await _pending_approvals()):
        return
    ticket = await worker.call_tool("get_ticket", ticket_id=ticket_id)
    if not ticket.get("found") or ticket["ticket"]["status"] not in ("in_progress", "waiting_approval"):
        return
    before = ticket["ticket"]["status"]
    result = await worker.call_tool("update_ticket_status", ticket_id=ticket_id, status="resolved",
                                    note=reason, updated_by="backend status sync")
    append_event(run_id=LATEST_RUN.get(ticket_id, "status-sync"), ticket_id=ticket_id, agent="backend",
                 step_type="status_sync", tool_name="update_ticket_status",
                 arguments={"ticket_id": ticket_id, "from": before, "to": "resolved"},
                 result=f"{reason} ({'ok' if result.get('updated') else result})")


def _log_decision(approval: dict | None, approval_id: int, tool: str, args: dict, result: Any) -> None:
    ticket_id = approval.get("ticket_id") if approval else None
    append_event(run_id=LATEST_RUN.get(ticket_id, "human-decision"), ticket_id=ticket_id,
                 agent="human", step_type="human_decision", tool_name=tool,
                 arguments={"approval_id": approval_id, **args}, result=result)


async def _get_approval(approval_id: int) -> dict:
    data = await worker.call_tool("list_approvals", status=None)
    for a in data.get("approvals", []) if data.get("found") else []:
        if a["id"] == approval_id:
            return a
    raise HTTPException(404, f"No approval with id {approval_id}.")


# ------------------------------------------------------------- routes

@app.get("/health")
async def health():
    shop = await worker.call_tool("get_shop_today")
    return {"status": "ok", "mcp_server": "connected", "shop_today": shop.get("shop_today"),
            "working_db": WORKING_DB.exists(), "model": MODEL_NAME}


@app.get("/tickets")
async def list_tickets():
    data = await worker.call_tool("list_tickets")
    pending = await _pending_approvals()
    out = []
    for t in data.get("tickets", []):
        tid = t["id"]
        run = RUNS.get(LATEST_RUN.get(tid, ""))
        ticket_pending = [a for a in pending if a["ticket_id"] == tid]
        run_finished = (run is not None and run["status"] != "running") or \
            t["status"] in ("waiting_approval", "resolved")
        if run and run["status"] == "running":
            status = "running"
        elif ticket_pending:
            status = "awaiting approval"
        elif run_finished:
            status = "resolved"
        else:
            status = "open"
        out.append({
            **t,
            "db_status": t["status"],
            "status": status,
            "pending_approvals": len(ticket_pending),
            "pending_amount": round(sum(a["amount"] for a in ticket_pending), 2),
            "latest_run": run,
        })
    return {"tickets": out}


@app.post("/tickets/{ticket_id}/run", status_code=202)
async def run_ticket_route(ticket_id: int):
    found = await worker.call_tool("get_ticket", ticket_id=ticket_id)
    if not found.get("found"):
        raise HTTPException(404, f"No ticket with id {ticket_id}.")
    if _is_running(ticket_id):
        raise HTTPException(409, f"Ticket {ticket_id} is already running ({LATEST_RUN[ticket_id]}).")

    run_id = new_run_id()
    RUNS[run_id] = {"run_id": run_id, "ticket_id": ticket_id, "status": "running",
                    "started_at": _now(), "finished_at": None, "result": None}
    LATEST_RUN[ticket_id] = run_id

    def _done(future):
        info = RUNS.get(run_id)
        if info is None:  # cleared by /reset
            return
        try:
            result = future.result()
            info.update(status=result.status, result=result.model_dump())
        except Exception as exc:  # pragma: no cover - safety net
            info.update(status="error", result={"resolution": f"{type(exc).__name__}: {exc}"})
        info["finished_at"] = _now()
        if info["status"] == "completed":
            # Re-check approvals now that the run is over, so the database matches the board.
            worker.submit(_maybe_resolve(ticket_id, "Run finished with no pending approvals."))

    worker.submit(run_ticket(ticket_id, run_id=run_id)).add_done_callback(_done)
    return {"run_id": run_id, "ticket_id": ticket_id, "status": "running",
            "poll": f"/events?ticket_id={ticket_id}&since=-1"}


@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(404, f"No run {run_id} (runs are kept in memory until reset/restart).")
    return RUNS[run_id]


@app.get("/events")
async def events(ticket_id: int | None = None,
                 since: int = Query(-1, description="Return events with id greater than this."),
                 limit: int = Query(200, ge=1, le=1000)):
    """Agent events, oldest first. Each has an id; pass the last id you saw as `since`."""
    all_events = read_events()
    picked = [{"id": i, **e} for i, e in enumerate(all_events)
              if i > since and (ticket_id is None or e.get("ticket_id") == ticket_id)]
    picked = picked[-limit:]  # most recent `limit`, still oldest first
    return {"events": picked, "last_id": picked[-1]["id"] if picked else since,
            "running": _is_running(ticket_id)}


@app.get("/approvals")
async def approvals():
    pending = await _pending_approvals()
    return {"approvals": pending, "count": len(pending),
            "total": round(sum(a["amount"] for a in pending), 2)}


class ApproveBody(BaseModel):
    approved_by: str = "Dashboard user"


class RejectBody(BaseModel):
    decided_by: str = "Dashboard user"
    note: str = ""


@app.post("/approvals/{approval_id}/approve")
async def approve(approval_id: int, body: ApproveBody | None = None):
    """The ONLY place money moves: calls the MCP pay tool after a human clicks Approve."""
    body = body or ApproveBody()
    approval = await _get_approval(approval_id)
    result = await worker.call_tool("execute_approved_payment", approval_id=approval_id,
                                    approved_by=body.approved_by)
    _log_decision(approval, approval_id, "execute_approved_payment",
                  {"approved_by": body.approved_by}, result)
    if not result.get("paid"):
        raise HTTPException(409, result.get("message", "Payment refused."))
    await _maybe_resolve(approval.get("ticket_id"))
    return result


@app.post("/approvals/{approval_id}/reject")
async def reject(approval_id: int, body: RejectBody | None = None):
    body = body or RejectBody()
    approval = await _get_approval(approval_id)
    result = await worker.call_tool("reject_approval", approval_id=approval_id,
                                    decided_by=body.decided_by, note=body.note)
    _log_decision(approval, approval_id, "reject_approval",
                  {"decided_by": body.decided_by, "note": body.note}, result)
    if not result.get("rejected"):
        raise HTTPException(409, result.get("message", "Could not reject."))
    await _maybe_resolve(approval.get("ticket_id"))
    return result


@app.get("/cash")
async def cash():
    data = await worker.call_tool("get_cash_balance")
    checking = next((a for a in data["cash_accounts"] if a["name"] == "checking"), None)
    return {"checking": checking["balance"] if checking else None,
            "as_of": checking["date"] if checking else None,
            "shop_today": data["shop_today"],
            "pending_approvals_total": data["pending_approvals_total"],
            "cash_after_pending": data["cash_after_pending"]}


@app.post("/reset")
async def reset():
    """Copy the original DB over the working copy, recreate helper tables, clear run state.

    The original is only read. output/audit_trail.json is NOT wiped.
    """
    if _is_running():
        raise HTTPException(409, "A run is in progress. Wait for it to finish before resetting.")
    reset_working_db()
    tables = await worker.call_tool("init_helper_tables")
    RUNS.clear()
    LATEST_RUN.clear()
    append_event(run_id="reset", agent="human", step_type="human_decision", tool_name="reset",
                 result="Working database reset from the original; run state cleared.")
    return {"reset": True, "helper_tables": tables.get("helper_tables", []),
            "message": "Working database reset from the original. Audit trail kept."}
