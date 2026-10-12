import { useEffect, useRef, useState } from "react";
import type { Cash } from "../api";
import { money } from "../agents";

/** Smoothly counts from the old balance to the new one. */
function useTween(target: number, ms = 1200): number {
  const [value, setValue] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    const start = performance.now();
    const begin = from.current;
    let frame = 0;
    const step = (now: number) => {
      const p = Math.min((now - start) / ms, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      const v = begin + (target - begin) * eased;
      setValue(v);
      from.current = v;
      if (p < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, ms]);
  return value;
}

export function CashMeter({ cash }: { cash: Cash | null }) {
  const balance = cash?.checking ?? 0;
  const shown = useTween(balance);
  const prev = useRef<number | null>(null);
  const [delta, setDelta] = useState<{ amount: number; key: number } | null>(null);

  useEffect(() => {
    if (cash?.checking == null) return;
    if (prev.current !== null && cash.checking !== prev.current) {
      setDelta({ amount: cash.checking - prev.current, key: Date.now() });
    }
    prev.current = cash.checking;
  }, [cash?.checking]);

  const pending = cash?.pending_approvals_total ?? 0;
  const after = cash?.cash_after_pending ?? balance;
  const pendingPct = balance > 0 ? Math.min((pending / balance) * 100, 100) : 0;
  const over = after < 0;

  return (
    <section className="panel cash-panel">
      <div className="panel-title">
        <span>🏦 Checking balance</span>
        <span className="muted mono">{cash?.as_of ?? ""}</span>
      </div>
      <div className={`cash-big mono ${delta && delta.amount < 0 ? "dropping" : ""}`} key={delta?.key}>
        {cash ? money(shown) : "—"}
        {delta && (
          <span className={`cash-delta ${delta.amount < 0 ? "down" : "up"}`} key={delta.key}>
            {delta.amount < 0 ? "−" : "+"}
            {money(Math.abs(delta.amount))}
          </span>
        )}
      </div>
      <div className="cash-bar" title="Share of cash already promised to pending requests">
        <div className={`cash-bar-fill ${over ? "over" : ""}`} style={{ width: `${pendingPct}%` }} />
      </div>
      <div className="cash-rows">
        <div>
          <span className="muted">Promised to pending requests</span>
          <span className="mono">{money(pending)}</span>
        </div>
        <div>
          <span className="muted">Left if all are approved</span>
          <span className={`mono ${over ? "bad" : "good"}`}>{money(after)}</span>
        </div>
      </div>
      {over && (
        <div className="cash-warning">
          ⚠️ Pending requests are more than the cash on hand. The pay tool will refuse whatever
          doesn't fit. Choose what to approve first.
        </div>
      )}
      <div className="cash-foot muted">Cash only goes out in this shop. No sales are counted.</div>
    </section>
  );
}
