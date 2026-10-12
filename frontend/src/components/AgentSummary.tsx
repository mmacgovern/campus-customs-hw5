import type { AgentEvent } from "../api";
import { TOOL_LABELS, agentMeta } from "../agents";
import { humanText } from "./ActivityFeed";

interface Summary {
  agent: string;
  toolCalls: number;
  tools: string[];
  delegatedTo: string[];
  tokens: number;
  lastWord: string | null;
  decisions: number;
}

function summarize(events: AgentEvent[]): Summary[] {
  const by = new Map<string, Summary>();
  for (const e of events) {
    if (e.agent === "human" && e.step_type !== "human_decision") continue;
    const s =
      by.get(e.agent) ??
      { agent: e.agent, toolCalls: 0, tools: [], delegatedTo: [], tokens: 0, lastWord: null, decisions: 0 };
    s.tokens += e.tokens;
    if (e.step_type === "tool_call" && e.tool_name && e.tool_name !== "delegate") {
      s.toolCalls += 1;
      if (!s.tools.includes(e.tool_name)) s.tools.push(e.tool_name);
    }
    if (e.step_type === "delegation" && (e.result ?? "").startsWith("Handing off")) {
      const to = String(e.arguments?.to_agent ?? "");
      if (!s.delegatedTo.includes(to)) s.delegatedTo.push(to);
    }
    if (e.step_type === "final") s.lastWord = e.result;
    if (e.step_type === "human_decision") {
      s.decisions += 1;
      s.lastWord = s.lastWord && s.decisions > 1 ? `${s.lastWord} ${humanText(e)}` : humanText(e);
    }
    by.set(e.agent, s);
  }
  return [...by.values()];
}

function firstLine(text: string | null): string {
  if (!text) return "Still working…";
  const clean = text.replace(/[#*`]/g, "").split("\n").map((l) => l.trim()).filter(Boolean);
  const pick = clean.find((l) => l.length > 30) ?? clean[0] ?? "";
  return pick.length > 170 ? pick.slice(0, 167) + "…" : pick;
}

export function AgentSummary({ events }: { events: AgentEvent[] }) {
  const summaries = summarize(events);
  return (
    <section className="panel">
      <div className="panel-title">
        <span>🪪 What each agent did</span>
        <span className="muted small">{summaries.length ? `${summaries.length} on this ticket` : ""}</span>
      </div>
      {summaries.length === 0 && <div className="muted small">Summaries appear once the team starts.</div>}
      <div className="summary-grid">
        {summaries.map((s) => {
          const m = agentMeta(s.agent);
          return (
            <div key={s.agent} className="summary-card" style={{ ["--agent" as string]: m.color }}>
              <div className="summary-head">
                <span className="avatar sm" style={{ background: m.color }}>{m.icon}</span>
                <div>
                  <div className="summary-name" style={{ color: m.color }}>{m.name}</div>
                  <div className="muted small">{m.role}</div>
                </div>
                {s.tokens > 0 && <span className="summary-tokens mono">{s.tokens.toLocaleString()} tok</span>}
              </div>
              <div className="summary-stats small">
                {s.agent === "human" ? (
                  <span>{s.decisions} decision{s.decisions === 1 ? "" : "s"}</span>
                ) : (
                  <span>{s.toolCalls} tool call{s.toolCalls === 1 ? "" : "s"}</span>
                )}
                {s.delegatedTo.length > 0 && (
                  <span>
                    → {s.delegatedTo.map((d) => agentMeta(d).name).join(", ")}
                  </span>
                )}
              </div>
              {s.tools.length > 0 && (
                <div className="summary-tools">
                  {s.tools.map((t) => (
                    <span key={t} className="tool-chip" title={t}>{TOOL_LABELS[t] ?? t}</span>
                  ))}
                </div>
              )}
              <div className="summary-word">“{firstLine(s.lastWord)}”</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
