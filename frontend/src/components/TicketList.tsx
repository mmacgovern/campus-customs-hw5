import type { BoardStatus, Ticket } from "../api";
import { money } from "../agents";

const TYPE_ICON: Record<string, string> = {
  customer_order: "🛍️",
  rent_notice: "🏠",
  price_override: "🏷️",
};

const STATUS_LABEL: Record<BoardStatus, string> = {
  open: "Open",
  running: "Running",
  "awaiting approval": "Awaiting approval",
  resolved: "Resolved",
};

function detail(t: Ticket): string {
  if (t.sku) return `${t.qty ?? 1} × ${t.sku} · size ${t.size}`;
  if (t.lease_id) return `Lease ${t.lease_id}`;
  return t.type.replace(/_/g, " ");
}

interface Props {
  tickets: Ticket[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

export function TicketList({ tickets, selectedId, onSelect }: Props) {
  return (
    <div className="ticket-list">
      {tickets.map((t) => (
        <button
          key={t.id}
          className={`ticket-card status-${t.status.replace(" ", "-")} ${t.id === selectedId ? "selected" : ""}`}
          onClick={() => onSelect(t.id)}
          aria-pressed={t.id === selectedId}
        >
          <div className="ticket-top">
            <span className="ticket-id">#{t.id}</span>
            <span className={`status-pill ${t.status.replace(" ", "-")}`}>
              {t.status === "running" && <span className="pulse-dot" />}
              {STATUS_LABEL[t.status]}
            </span>
          </div>
          <div className="ticket-subject">
            <span className="ticket-icon">{TYPE_ICON[t.type] ?? "🎫"}</span>
            {t.subject}
          </div>
          <div className="ticket-meta">{t.requester}</div>
          <div className="ticket-meta mono">{detail(t)}</div>
          {t.pending_approvals > 0 && (
            <div className="ticket-pending">
              ⏳ {t.pending_approvals} awaiting you · {money(t.pending_amount)}
            </div>
          )}
          {t.status === "resolved" && (
            <div className="stamp" aria-label="Resolved">
              RESOLVED
            </div>
          )}
        </button>
      ))}
    </div>
  );
}
