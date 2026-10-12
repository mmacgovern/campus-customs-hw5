import { useEffect, useRef, type ReactNode } from "react";
import type { AgentEvent } from "../api";
import { TOOL_LABELS, agentMeta } from "../agents";

/** Older audit entries squashed answers onto one line; put the line breaks back. */
function restoreLines(text: string): string {
  if (text.includes("\n")) return text;
  return text
    .replace(/\s*(#{1,4}\s)/g, "\n$1")
    .replace(/(#{1,4}\s[^*\n]*?\*\*[^*]+\*\*)\s+/g, "$1\n")
    .replace(/\s+-\s(?=\S)/g, "\n- ");
}

/** Plain-English line for a human approve / reject event. */
export function humanText(e: AgentEvent): string {
  const r = e.result ?? "";
  const amount = r.match(/"amount":\s*([\d.]+)/)?.[1];
  const payee = r.match(/"payee":\s*"([^"]+)"/)?.[1];
  const id = e.arguments?.approval_id;
  const amt = amount ? ` $${Number(amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "";
  if (e.tool_name === "reset") return "Reset the working database.";
  if (e.tool_name === "reject_approval") {
    const note = e.arguments?.note ? ` Reason: "${String(e.arguments.note)}"` : "";
    return /"rejected":\s*true/.test(r) ? `Rejected request #${id}${amt}${payee ? ` to ${payee}` : ""}.${note}` : `Could not reject #${id}.`;
  }
  if (/"paid":\s*true/.test(r)) {
    const bal = r.match(/"new_balance":\s*([\d.]+)/)?.[1];
    return `Approved request #${id}: paid${amt}${payee ? ` to ${payee}` : ""}.${bal ? ` Checking is now $${Number(bal).toLocaleString("en-US", { minimumFractionDigits: 2 })}.` : ""}`;
  }
  const msg = r.match(/"message":\s*"([^"]+)"/)?.[1];
  return `Approval #${id} refused${msg ? `: ${msg}` : "."}`;
}

/** Tiny renderer for the agents' markdown-ish answers (headings, bold, bullets). */
function renderText(raw: string): ReactNode {
  const text = restoreLines(raw);
  const inline = (line: string, key: number) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    return (
      <span key={key}>
        {parts.map((p, i) => (p.startsWith("**") && p.endsWith("**") ? <b key={i}>{p.slice(2, -2)}</b> : p))}
      </span>
    );
  };
  return text.split("\n").map((raw, i) => {
    const line = raw.trimEnd();
    if (!line.trim()) return <div key={i} className="md-gap" />;
    if (/^#{1,4}\s/.test(line)) return <div key={i} className="md-h">{line.replace(/^#{1,4}\s/, "")}</div>;
    if (/^\s*[-*]\s/.test(line)) return <div key={i} className="md-li">• {inline(line.replace(/^\s*[-*]\s/, ""), i)}</div>;
    return <div key={i}>{inline(line, i)}</div>;
  });
}

function Args({ args }: { args: Record<string, unknown> | null }) {
  if (!args) return null;
  const entries = Object.entries(args).filter(([k]) => k !== "task" && k !== "reason" && k !== "body");
  if (!entries.length) return null;
  return (
    <span className="args">
      {entries.map(([k, v]) => (
        <span key={k} className="arg-chip mono">
          {k}={typeof v === "string" ? v : JSON.stringify(v)}
        </span>
      ))}
    </span>
  );
}

function EventBody({ e }: { e: AgentEvent }) {
  switch (e.step_type) {
    case "tool_call":
      return (
        <div className="ev-line">
          <span className="ev-kind tool">🔧 {TOOL_LABELS[e.tool_name ?? ""] ?? e.tool_name}</span>
          <code className="tool-name">{e.tool_name}</code>
          <Args args={e.arguments} />
        </div>
      );
    case "tool_result":
      return (
        <div className="ev-line">
          <span className="ev-kind result">↩ {e.tool_name}</span>
          <span className="ev-result mono">{e.result}</span>
        </div>
      );
    case "delegation": {
      const to = agentMeta(String(e.arguments?.to_agent ?? ""));
      const refused = (e.result ?? "").startsWith("Handing off") === false;
      return (
        <div className={`handoff ${refused ? "refused" : ""}`}>
          <div className="handoff-head">
            <span>{refused ? "⛔ Tried to hand off to" : "➜ Hands off to"}</span>
            <span className="mini-avatar" style={{ background: to.color }}>{to.icon}</span>
            <b style={{ color: to.color }}>{to.name}</b>
          </div>
          <div className="handoff-task">{String(e.arguments?.task ?? "")}</div>
          {refused && <div className="bad small">{e.result}</div>}
        </div>
      );
    }
    case "final":
      return <div className="bubble">{renderText(e.result ?? "")}</div>;
    case "thinking":
      return <div className="thinking">💭 {e.result}</div>;
    case "human_decision":
      return (
        <div className="ev-line">
          <span className="ev-kind human">🖐 {humanText(e)}</span>
        </div>
      );
    case "error":
      return <div className="bad">⚠️ {e.result}</div>;
    default:
      return <div>{e.result}</div>;
  }
}

interface Props {
  events: AgentEvent[];
  running: boolean;
  hideResults: boolean;
}

export function ActivityFeed({ events, running, hideResults }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const stick = useRef(true);

  useEffect(() => {
    const el = box.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [events.length]);

  const shown = hideResults ? events.filter((e) => e.step_type !== "tool_result") : events;

  return (
    <div
      className="feed"
      ref={box}
      onScroll={(ev) => {
        const el = ev.currentTarget;
        stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      }}
    >
      {shown.length === 0 && (
        <div className="feed-empty">
          {running ? "Waking up the team…" : "No activity yet. Pick a ticket and press Start the team."}
        </div>
      )}
      {shown.map((e) => {
        const a = agentMeta(e.agent);
        return (
          <div
            key={e.id}
            className={`event ev-${e.step_type}`}
            style={{ ["--agent" as string]: a.color, marginLeft: `${Math.min(e.depth, 3) * 18}px` }}
          >
            <div className="avatar" style={{ background: a.color }} title={a.name}>
              {a.icon}
            </div>
            <div className="ev-main">
              <div className="ev-head">
                <span className="ev-agent" style={{ color: a.color }}>{a.name}</span>
                {e.depth > 0 && <span className="depth-tag">depth {e.depth}</span>}
                <span className="ev-time mono">{new Date(e.timestamp).toLocaleTimeString()}</span>
                {e.tokens > 0 && <span className="ev-tokens mono">{e.tokens.toLocaleString()} tok</span>}
              </div>
              <EventBody e={e} />
            </div>
          </div>
        );
      })}
      {running && (
        <div className="typing">
          <span />
          <span />
          <span />
          <em>agents working</em>
        </div>
      )}
    </div>
  );
}
