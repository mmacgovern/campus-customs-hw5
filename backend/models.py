"""Pydantic data types shared by the backend, the agents, and (later) the API routes."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
StepType = Literal["thinking", "tool_call", "tool_result", "delegation", "final", "error", "status_sync",
                   "human_decision"]
TicketStatus = Literal["open", "in_progress", "waiting_approval", "resolved"]
ApprovalKind = Literal["invoice", "rent", "purchase_order"]
ApprovalStatus = Literal["pending", "executed", "rejected"]


class Ticket(BaseModel):
    """A row from the tickets table."""
    id: int
    type: str
    requester: str
    subject: str
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    lease_id: int | None = None
    invoice_id: int | None = None
    status: TicketStatus | str
    notes: str | None = None
    created_at: str


class CashBalance(BaseModel):
    """Cash on hand, from the get_cash_balance MCP tool."""
    shop_today: str
    total_cash: float
    pending_approvals_total: float = 0.0
    cash_after_pending: float
    cash_accounts: list[dict[str, Any]] = Field(default_factory=list)


class PendingApproval(BaseModel):
    """A payment or purchase order an agent PREPARED. Money moves only after a human approves."""
    id: int
    kind: ApprovalKind
    ref_id: int | None = None
    ticket_id: int | None = None
    payee: str
    amount: float
    account: str
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    reason: str
    requested_by: str
    status: ApprovalStatus
    shop_date: str
    created_at: str
    decided_by: str | None = None
    decided_at: str | None = None
    decision_note: str | None = None
    payment_id: int | None = None


class Delegation(BaseModel):
    """One agent handing a task to a teammate."""
    from_agent: str
    to_agent: str
    task: str
    depth: int
    allowed: bool = True
    refusal_reason: str | None = None
    result_summary: str | None = None


class AuditEvent(BaseModel):
    """One step of an agent loop, appended to output/audit_trail.json."""
    timestamp: datetime
    run_id: str
    ticket_id: int | None = None
    agent: str
    depth: int = 0
    step_type: StepType
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    result: str | None = None
    tokens: int = 0


class TicketResult(BaseModel):
    """What the Boss produced for one ticket run."""
    run_id: str
    ticket_id: int
    status: Literal["completed", "stopped_by_limit", "error"]
    resolution: str
    delegations: list[Delegation] = Field(default_factory=list)
    requests: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
