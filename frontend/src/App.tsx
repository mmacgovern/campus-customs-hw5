import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api, type AgentEvent, type Approval, type Cash, type Ticket } from "./api";
import { BOARD_POLL_MS, EVENTS_POLL_MS } from "./config";
import { money } from "./agents";
import { TicketList } from "./components/TicketList";
import { ActivityFeed } from "./components/ActivityFeed";
import { DelegationMap } from "./components/DelegationMap";
import { AgentSummary } from "./components/AgentSummary";
import { ApprovalsPanel } from "./components/ApprovalsPanel";
import { CashMeter } from "./components/CashMeter";
import { ResetButton } from "./components/ResetButton";

type Tone = "good" | "bad" | "info";
interface Toast { id: number; text: string; tone: Tone }

const NON_RUNS = new Set(["reset", "human-decision"]);

function loadApprover(): string {
  try {
    return localStorage.getItem("approver") || "Shop manager";
  } catch {
    return "Shop manager";
  }
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [cash, setCash] = useState<Cash | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [viewRun, setViewRun] = useState<string | null>(null);
  const [hideResults, setHideResults] = useState(true);
  const [starting, setStarting] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [approver, setApprover] = useState(loadApprover);
  const lastId = useRef(-1);
  const prevStatus = useRef<Record<number, string>>({});

  const toast = useCallback((text: string, tone: Tone = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000);
  }, []);

  // ---- board: tickets, cash, approvals ----
  const refreshBoard = useCallback(async () => {
    try {
      const [t, c, a] = await Promise.all([api.tickets(), api.cash(), api.approvals()]);
      setTickets(t);
      setCash(c);
      setApprovals(a.approvals);
      setBackendUp(true);
    } catch {
      setBackendUp(false);
    }
  }, []);

  useEffect(() => {
    refreshBoard();
    const h = setInterval(refreshBoard, BOARD_POLL_MS);
    return () => clearInterval(h);
  }, [refreshBoard]);

  useEffect(() => {
    if (selectedId === null && tickets.length) setSelectedId(tickets[0].id);
  }, [tickets, selectedId]);

  // Announce when a run finishes, and how the ticket ended up.
  useEffect(() => {
    for (const t of tickets) {
      const before = prevStatus.current[t.id];
      if (before === "running" && t.status !== "running") {
        if (t.status === "resolved") toast(`Ticket ${t.id} is resolved. 🎉`, "good");
        else if (t.status === "awaiting approval")
          toast(`Ticket ${t.id}: the team is done. ${t.pending_approvals} request(s) need your approval.`, "info");
        else toast(`Ticket ${t.id}: run ended (${t.latest_run?.status ?? t.status}).`, "info");
      }
      if (before && before !== "resolved" && before !== "running" && t.status === "resolved") {
        toast(`Ticket ${t.id} is resolved. 🎉`, "good");
      }
      prevStatus.current[t.id] = t.status;
    }
  }, [tickets, toast]);

  // ---- events for the selected ticket ----
  useEffect(() => {
    if (selectedId === null) return;
    let cancelled = false;
    lastId.current = -1;
    setEvents([]);
    setViewRun(null);
    const poll = async () => {
      try {
        const r = await api.events(selectedId, lastId.current);
        if (cancelled) return;
        if (r.events.length) {
          lastId.current = r.last_id;
          setEvents((prev) => [...prev, ...r.events]);
        }
      } catch {
        /* the board poll reports the backend as down */
      }
    };
    poll();
    const h = setInterval(poll, EVENTS_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(h);
    };
  }, [selectedId]);

  const selected = tickets.find((t) => t.id === selectedId) ?? null;
  const running = selected?.status === "running";
  const anyRunning = tickets.some((t) => t.status === "running");

  // Runs seen for this ticket, newest last.
  const runIds = useMemo(() => {
    const ids: string[] = [];
    for (const e of events) if (!NON_RUNS.has(e.run_id) && !ids.includes(e.run_id)) ids.push(e.run_id);
    const live = selected?.latest_run?.run_id;
    if (live && !ids.includes(live)) ids.push(live);
    return ids;
  }, [events, selected?.latest_run?.run_id]);

  const activeRun = viewRun ?? selected?.latest_run?.run_id ?? runIds[runIds.length - 1] ?? null;
  const runEvents = useMemo(() => events.filter((e) => e.run_id === activeRun), [events, activeRun]);

  async function startRun() {
    if (!selected) return;
    setStarting(true);
    try {
      const r = await api.runTicket(selected.id);
      setViewRun(r.run_id);
      toast(`Team started on ticket ${selected.id}.`, "info");
      await refreshBoard();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : String(err), "bad");
    } finally {
      setStarting(false);
    }
  }

  async function doReset() {
    try {
      const r = await api.reset();
      toast(r.message, "good");
      prevStatus.current = {};
      lastId.current = -1;
      setEvents([]);
      setViewRun(null);
      await refreshBoard();
    } catch (err) {
      toast(err instanceof ApiError ? err.message : String(err), "bad");
    }
  }

  const runTokens = runEvents.reduce((n, e) => n + e.tokens, 0);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">CC</span>
          <div>
            <div className="brand-name">Campus Customs · Ops Desk</div>
            <div className="brand-sub">Multi-agent operations control room</div>
          </div>
        </div>
        <div className="topbar-mid">
          <div className="chip">
            📅 Shop today <b className="mono">{cash?.shop_today ?? "…"}</b>
          </div>
          <div className="chip">
            🏦 Checking <b className="mono">{money(cash?.checking)}</b>
          </div>
          <div className={`chip status-light ${backendUp ? "up" : backendUp === false ? "down" : ""}`}>
            <span className="light" /> {backendUp ? "Backend online" : backendUp === false ? "Backend offline" : "Connecting…"}
          </div>
        </div>
        <div className="topbar-right">
          <label className="signer small">
            Signing as
            <input
              value={approver}
              onChange={(e) => {
                setApprover(e.target.value);
                try {
                  localStorage.setItem("approver", e.target.value);
                } catch {
                  /* storage blocked: keep in memory only */
                }
              }}
            />
          </label>
          <ResetButton disabled={anyRunning || !backendUp} onConfirm={doReset} />
        </div>
      </header>

      {backendUp === false && (
        <div className="offline-banner">
          Can't reach the backend at http://localhost:8000. Start it from the backend folder with{" "}
          <code>uvicorn main:app --reload --port 8000</code>.
        </div>
      )}

      <main className="grid">
        <aside className="col-left">
          <div className="col-title">Ticket queue</div>
          <TicketList tickets={tickets} selectedId={selectedId} onSelect={setSelectedId} />
          <div className="legend small muted">
            <div><span className="dot open" /> open</div>
            <div><span className="dot running" /> running</div>
            <div><span className="dot awaiting" /> awaiting approval</div>
            <div><span className="dot resolved" /> resolved</div>
          </div>
        </aside>

        <section className="col-center">
          {selected ? (
            <div className="panel ticket-head">
              <div>
                <div className="muted small">Ticket #{selected.id} · {selected.type.replace(/_/g, " ")}</div>
                <h1>{selected.subject}</h1>
                <div className="muted">
                  {selected.requester}
                  {selected.notes ? ` · "${selected.notes.split("\n")[0]}"` : ""}
                </div>
              </div>
              <div className="ticket-actions">
                <button className="btn start" onClick={startRun} disabled={running || starting || !backendUp}>
                  {running ? (
                    <>
                      <span className="spinner" /> Team working…
                    </>
                  ) : starting ? (
                    "Starting…"
                  ) : selected.latest_run || runIds.length ? (
                    "▶ Run the team again"
                  ) : (
                    "▶ Start the team"
                  )}
                </button>
                {selected.status === "resolved" && <div className="stamp stamp-lg">RESOLVED</div>}
              </div>
            </div>
          ) : (
            <div className="panel">Loading tickets…</div>
          )}

          <div className="panel feed-panel">
            <div className="panel-title">
              <span>📡 Live activity {running && <span className="live-tag">LIVE</span>}</span>
              <span className="feed-tools small">
                {runIds.length > 1 && (
                  <select value={activeRun ?? ""} onChange={(e) => setViewRun(e.target.value)}>
                    {runIds.map((id, i) => (
                      <option key={id} value={id}>
                        {id}
                        {i === runIds.length - 1 ? " (latest)" : ""}
                      </option>
                    ))}
                  </select>
                )}
                {runTokens > 0 && <span className="muted mono">{runTokens.toLocaleString()} tokens</span>}
                <label>
                  <input type="checkbox" checked={!hideResults} onChange={(e) => setHideResults(!e.target.checked)} />
                  show raw tool results
                </label>
              </span>
            </div>
            <ActivityFeed events={runEvents} running={running} hideResults={hideResults} />
          </div>

          <div className="center-bottom">
            <DelegationMap events={runEvents} running={running} />
            <AgentSummary events={runEvents} />
          </div>
        </section>

        <aside className="col-right">
          <CashMeter cash={cash} />
          <ApprovalsPanel
            approvals={approvals}
            cashOnHand={cash?.checking ?? null}
            approver={approver || "Shop manager"}
            onDecided={(msg, tone) => {
              toast(msg, tone);
              refreshBoard();
            }}
          />
        </aside>
      </main>

      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.tone}`}>{t.text}</div>
        ))}
      </div>
    </div>
  );
}
