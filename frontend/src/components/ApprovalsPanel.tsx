import { useState } from "react";
import { ApiError, api, type Approval } from "../api";
import { agentMeta, money } from "../agents";

const KIND: Record<Approval["kind"], { icon: string; label: string }> = {
  invoice: { icon: "🧾", label: "Vendor invoice" },
  rent: { icon: "🏠", label: "Rent" },
  purchase_order: { icon: "📦", label: "Purchase order" },
};

interface Props {
  approvals: Approval[];
  cashOnHand: number | null;
  approver: string;
  onDecided: (message: string, tone: "good" | "bad" | "info") => void;
}

function describe(a: Approval): string {
  if (a.kind === "invoice") return `Invoice ${a.ref_id}`;
  if (a.kind === "rent") return `Lease ${a.ref_id}`;
  return `${a.qty} × ${a.sku} size ${a.size}`;
}

export function ApprovalsPanel({ approvals, cashOnHand, approver, onDecided }: Props) {
  const [busy, setBusy] = useState<number | null>(null);
  const [errors, setErrors] = useState<Record<number, string>>({});
  const [rejecting, setRejecting] = useState<number | null>(null);
  const [note, setNote] = useState("");

  async function approve(a: Approval) {
    setBusy(a.id);
    setErrors((e) => ({ ...e, [a.id]: "" }));
    try {
      const r = await api.approve(a.id, approver);
      onDecided(`Paid ${money(a.amount)} to ${a.payee}. Checking is now ${money(r.new_balance)}.`, "good");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : String(err);
      setErrors((e) => ({ ...e, [a.id]: msg }));
      onDecided(`Payment refused: ${msg}`, "bad");
    } finally {
      setBusy(null);
    }
  }

  async function reject(a: Approval) {
    setBusy(a.id);
    try {
      await api.reject(a.id, approver, note);
      onDecided(`Rejected ${KIND[a.kind].label.toLowerCase()} to ${a.payee} (${money(a.amount)}). No money moved.`, "info");
      setRejecting(null);
      setNote("");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : String(err);
      setErrors((e) => ({ ...e, [a.id]: msg }));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="panel approvals-panel">
      <div className="panel-title">
        <span>✍️ Waiting for your approval</span>
        <span className="count-badge">{approvals.length}</span>
      </div>
      {approvals.length === 0 && (
        <div className="empty-approvals">
          <div className="big-emoji">🗂️</div>
          Nothing to sign. Agents can only <b>prepare</b> payments, and money moves only when you
          approve.
        </div>
      )}
      {approvals.map((a) => {
        const k = KIND[a.kind];
        const by = agentMeta(a.requested_by);
        const tooBig = cashOnHand != null && a.amount > cashOnHand;
        const error = errors[a.id];
        const cashRefusal = error && /negative|has \d|not enough|insufficient/i.test(error);
        return (
          <div key={a.id} className={`approval-card ${error ? "has-error" : ""}`}>
            <div className="approval-top">
              <span className="approval-kind">{k.icon} {k.label}</span>
              <span className="muted small">#{a.id}{a.ticket_id ? ` · ticket ${a.ticket_id}` : ""}</span>
            </div>
            <div className="approval-payee">{a.payee}</div>
            <div className="approval-amount mono">{money(a.amount)}</div>
            <div className="muted small">{describe(a)} · from {a.account}</div>
            <div className="approval-reason">{a.reason}</div>
            <div className="approval-by small">
              <span className="mini-avatar" style={{ background: by.color }}>{by.icon}</span>
              prepared by <b style={{ color: by.color }}>{by.name}</b>
            </div>
            {tooBig && !error && (
              <div className="approval-warn small">⚠️ This is more than the {money(cashOnHand)} on hand.</div>
            )}
            {error && (
              <div className="approval-error">
                <b>{cashRefusal ? "💸 Not enough cash: payment refused" : "⛔ Refused"}</b>
                <div>{error}</div>
              </div>
            )}
            {rejecting === a.id ? (
              <div className="reject-box">
                <input
                  autoFocus
                  placeholder="Why reject? (optional)"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && reject(a)}
                />
                <div className="btn-row">
                  <button className="btn ghost" onClick={() => setRejecting(null)} disabled={busy === a.id}>
                    Cancel
                  </button>
                  <button className="btn danger" onClick={() => reject(a)} disabled={busy === a.id}>
                    Confirm reject
                  </button>
                </div>
              </div>
            ) : (
              <div className="btn-row">
                <button className="btn ghost" onClick={() => setRejecting(a.id)} disabled={busy !== null}>
                  Reject
                </button>
                <button className="btn approve" onClick={() => approve(a)} disabled={busy !== null}>
                  {busy === a.id ? "Paying…" : `Approve ${money(a.amount)}`}
                </button>
              </div>
            )}
          </div>
        );
      })}
    </section>
  );
}
