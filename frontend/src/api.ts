import { API_BASE } from "./config";

export type BoardStatus = "open" | "running" | "awaiting approval" | "resolved";

export interface RunInfo {
  run_id: string;
  ticket_id: number;
  status: "running" | "completed" | "stopped_by_limit" | "error";
  started_at: string;
  finished_at: string | null;
  result: { resolution: string; total_tokens: number; requests: number; tool_calls: number } | null;
}

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  notes: string | null;
  created_at: string;
  db_status: string;
  status: BoardStatus;
  pending_approvals: number;
  pending_amount: number;
  latest_run: RunInfo | null;
}

export type StepType =
  | "thinking" | "tool_call" | "tool_result" | "delegation" | "final" | "error" | "human_decision" | "status_sync";

export interface AgentEvent {
  id: number;
  timestamp: string;
  run_id: string;
  ticket_id: number | null;
  agent: string;
  depth: number;
  step_type: StepType;
  tool_name: string | null;
  arguments: Record<string, unknown> | null;
  result: string | null;
  tokens: number;
}

export interface Approval {
  id: number;
  kind: "invoice" | "rent" | "purchase_order";
  ref_id: number | null;
  ticket_id: number | null;
  payee: string;
  amount: number;
  account: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  reason: string;
  requested_by: string;
  status: string;
  created_at: string;
}

export interface Cash {
  checking: number | null;
  as_of: string | null;
  shop_today: string;
  pending_approvals_total: number;
  cash_after_pending: number;
}

/** Error carrying the backend's plain-English `detail` message. */
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${API_BASE}. Is it running?`);
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${res.status}).`;
    throw new ApiError(res.status, detail);
  }
  return body as T;
}

export const api = {
  health: () => request<{ status: string; shop_today: string }>("/health"),
  tickets: () => request<{ tickets: Ticket[] }>("/tickets").then((r) => r.tickets),
  runTicket: (id: number) =>
    request<{ run_id: string }>(`/tickets/${id}/run`, { method: "POST" }),
  events: (ticketId: number, since: number) =>
    request<{ events: AgentEvent[]; last_id: number; running: boolean }>(
      `/events?ticket_id=${ticketId}&since=${since}&limit=1000`,
    ),
  approvals: () => request<{ approvals: Approval[]; total: number }>("/approvals"),
  approve: (id: number, by: string) =>
    request<{ paid: boolean; new_balance: number }>(`/approvals/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: by }),
    }),
  reject: (id: number, by: string, note: string) =>
    request<{ rejected: boolean }>(`/approvals/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ decided_by: by, note }),
    }),
  cash: () => request<Cash>("/cash"),
  reset: () => request<{ message: string }>("/reset", { method: "POST" }),
};
