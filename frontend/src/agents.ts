/** Visual identity for every actor on the board. */
export interface AgentMeta {
  key: string;
  name: string;
  role: string;
  icon: string;
  color: string;
}

export const AGENTS: Record<string, AgentMeta> = {
  boss: { key: "boss", name: "Boss", role: "Routes & decides", icon: "🧭", color: "#f5b942" },
  inventory: { key: "inventory", name: "Inventory", role: "Stock & vendors", icon: "📦", color: "#38c6c6" },
  accounting: { key: "accounting", name: "Accounting", role: "Cash & approvals", icon: "🧮", color: "#5fd38d" },
  facilities: { key: "facilities", name: "Facilities", role: "Leases & rent", icon: "🏢", color: "#a78bfa" },
  customer_service: { key: "customer_service", name: "Customer Service", role: "Draft replies", icon: "💬", color: "#f472b6" },
  human: { key: "human", name: "You (human)", role: "Approves money", icon: "✋", color: "#e2e8f0" },
};

export const TEAM_ORDER = ["boss", "inventory", "accounting", "facilities", "customer_service"];

export function agentMeta(key: string): AgentMeta {
  return AGENTS[key] ?? { key, name: key, role: "", icon: "🤖", color: "#94a3b8" };
}

export const money = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD" });

export const TOOL_LABELS: Record<string, string> = {
  get_shop_today: "checked the shop date",
  list_tickets: "listed tickets",
  get_ticket: "read the ticket",
  check_stock_and_pricing: "checked stock & pricing",
  list_vendors: "looked up vendors",
  get_unpaid_invoices: "checked unpaid invoices",
  get_invoice_and_vendor_hold: "checked invoice & vendor hold",
  get_rent_due_and_cash: "checked rent due & cash",
  get_cash_balance: "checked cash",
  calculate_margin: "calculated margin",
  list_approvals: "listed approvals",
  create_payment_request: "prepared a payment request",
  create_purchase_order_request: "prepared a purchase order",
  save_customer_draft: "saved a customer draft",
  update_ticket_status: "updated ticket status",
  execute_approved_payment: "approved a payment",
  reject_approval: "rejected a request",
  delegate: "delegated",
};
