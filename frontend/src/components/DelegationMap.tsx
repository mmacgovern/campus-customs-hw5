import type { AgentEvent } from "../api";
import { TEAM_ORDER, agentMeta } from "../agents";

const W = 340;
const H = 250;
const CX = W / 2;
const CY = H / 2 + 6;
const R = 92;

// Boss at the top, the four specialists around the circle.
const POS: Record<string, { x: number; y: number }> = Object.fromEntries(
  TEAM_ORDER.map((key, i) => {
    const angle = -Math.PI / 2 + (i * 2 * Math.PI) / TEAM_ORDER.length;
    return [key, { x: CX + R * Math.cos(angle), y: CY + R * Math.sin(angle) }];
  }),
);

interface Props {
  events: AgentEvent[];
  running: boolean;
}

export function DelegationMap({ events, running }: Props) {
  const edges = new Map<string, { from: string; to: string; count: number; refused: boolean }>();
  for (const e of events) {
    if (e.step_type !== "delegation") continue;
    const to = String(e.arguments?.to_agent ?? "");
    if (!POS[to] || !POS[e.agent]) continue;
    const refused = !(e.result ?? "").startsWith("Handing off");
    const k = `${e.agent}>${to}`;
    const prev = edges.get(k);
    edges.set(k, { from: e.agent, to, count: (prev?.count ?? 0) + 1, refused: refused && (prev?.refused ?? true) });
  }
  const involved = new Set(events.filter((e) => POS[e.agent]).map((e) => e.agent));
  const lastAgent = [...events].reverse().find((e) => POS[e.agent])?.agent;

  return (
    <section className="panel">
      <div className="panel-title">
        <span>🕸️ Who called whom</span>
        <span className="muted small">{edges.size ? `${edges.size} hand-off route${edges.size > 1 ? "s" : ""}` : "no hand-offs yet"}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="map" role="img" aria-label="Delegation map">
        <defs>
          {TEAM_ORDER.map((k) => (
            <marker key={k} id={`arrow-${k}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" fill={agentMeta(k).color} />
            </marker>
          ))}
        </defs>
        {[...edges.values()].map(({ from, to, count, refused }) => {
          const a = POS[from];
          const b = POS[to];
          // Shorten so the arrow stops at the node's edge, and bend slightly so A→B and B→A don't overlap.
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const len = Math.hypot(dx, dy) || 1;
          const ux = dx / len;
          const uy = dy / len;
          const sx = a.x + ux * 24;
          const sy = a.y + uy * 24;
          const ex = b.x - ux * 26;
          const ey = b.y - uy * 26;
          const mx = (sx + ex) / 2 - uy * 16;
          const my = (sy + ey) / 2 + ux * 16;
          const color = agentMeta(from).color;
          return (
            <g key={`${from}-${to}`}>
              <path
                d={`M${sx},${sy} Q${mx},${my} ${ex},${ey}`}
                fill="none"
                stroke={refused ? "#ef4444" : color}
                strokeWidth={1.5 + Math.min(count, 3)}
                strokeDasharray={refused ? "4 4" : running ? "6 5" : undefined}
                className={running ? "flow" : ""}
                markerEnd={`url(#arrow-${from})`}
                opacity={0.9}
              />
              {count > 1 && (
                <text x={mx} y={my} className="edge-count" textAnchor="middle">×{count}</text>
              )}
            </g>
          );
        })}
        {TEAM_ORDER.map((k) => {
          const m = agentMeta(k);
          const p = POS[k];
          const on = involved.has(k);
          return (
            <g key={k} opacity={on ? 1 : 0.28} className={running && lastAgent === k ? "node-active" : ""}>
              <circle cx={p.x} cy={p.y} r={21} fill="#0d1424" stroke={m.color} strokeWidth={on ? 2.5 : 1.5} />
              <text x={p.x} y={p.y + 6} textAnchor="middle" fontSize="18">{m.icon}</text>
              <text x={p.x} y={p.y + 36} textAnchor="middle" className="node-label" fill={m.color}>
                {m.name}
              </text>
            </g>
          );
        })}
      </svg>
    </section>
  );
}
