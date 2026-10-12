# Campus Customs Ops Desk: Dashboard Design

The dashboard (`frontend/`, React + Vite + TypeScript) is a **dark "control room" for the shop**: the place a manager sits to watch the AI team work, step in only when money is involved, and see each ticket get stamped closed. It talks to the backend at one address, `API_BASE` in `frontend/src/config.ts` (`http://localhost:8000`). The backend allows the Vite origin `http://localhost:5173` through CORS.

## Layout (three columns, sized for a laptop)

```
┌──────────────────────────── top bar ────────────────────────────┐
│ CC Ops Desk │ Shop today · Checking $ · ● Backend online │ Signing as · ↺ Reset │
├──────────┬──────────────────────────────────────┬───────────────┤
│ TICKET   │ Ticket header + ▶ Start the team     │ 🏦 Checking   │
│ QUEUE    │──────────────────────────────────────│   balance     │
│ #101     │ 📡 Live activity (agent feed)        │───────────────│
│ #102     │                                      │ ✍️ Waiting for│
│ #103     │                                      │  your approval│
│ legend   │──────────────────┬───────────────────│  (cards with  │
│          │ 🕸️ Who called    │ 🪪 What each agent│  Approve /    │
│          │    whom (map)    │    did (cards)    │  Reject)      │
└──────────┴──────────────────┴───────────────────┴───────────────┘
```

- **Left: the ticket queue.** Each ticket is a card with its number, type icon (🛍️ order, 🏠 rent, 🏷️ price override), requester, the exact SKU/size/qty or lease, and a status pill. The colored left edge repeats the status so you can scan the queue at a glance.
- **Center: the work.** The selected ticket's header holds the big **▶ Start the team** button. Below it is the live feed, then two panels: a delegation map and per-agent summary cards.
- **Right: the money.** The checking balance always sits at the top right, with the approval cards under it. Money decisions stay in one fixed place, apart from the busy feed, so they never scroll away.
- The left and right columns stay put while the center scrolls. Below about 1,240 px wide the columns narrow; below about 980 px everything stacks into one column.

## How the agents read differently

Each agent has its own **color, emoji avatar and name**, used the same way everywhere: in the feed, the map and the summary cards.

| Agent | Avatar | Color | Why |
|---|---|---|---|
| Boss | 🧭 | amber | The compass that sets direction |
| Inventory | 📦 | teal | Boxes on shelves |
| Accounting | 🧮 | green | The money color |
| Facilities | 🏢 | violet | The building |
| Customer Service | 💬 | pink | Warm, conversational |
| You (human) | ✋ | white | The hand that approves |

In the **live feed**, each step is a row with the agent's avatar, a colored left rule and a faint tint of its color. Each step type has its own look:
- **Tool calls** show a plain-English label ("checked stock & pricing"), the exact MCP tool name in a code chip, and the arguments as small chips.
- **Hand-offs** are dashed "➜ Hands off to [avatar] Accounting" boxes that include the task text. Refused hand-offs (to itself, or too deep) turn red with ⛔.
- **Final answers** appear as a speech bubble, with the agent's headings in its own color.
- **Depth** is shown by indenting rows, so a Boss → Inventory → Accounting chain looks like a conversation thread. A small "depth 2" tag backs this up.
- Raw tool results are hidden by default to keep the feed readable. A "show raw tool results" checkbox brings them back for auditing.

The board polls `/events` every 1.5 seconds, using the `since` cursor so only new events come back. New rows slide in, and the feed follows the newest step unless you've scrolled up to read. While a run is going, a red **LIVE** tag blinks and three "agents working" dots bounce.

## Who called whom (delegation map)

This is an SVG with the Boss at the top and the four specialists around a circle. Every hand-off in the run draws a curved arrow in the **sender's color**. A thicker arrow with a "×2" label means repeated hand-offs, and a red dashed arrow means a refused one. Agents that weren't involved fade to 28% opacity. During a run, the arrows' dashes flow and the agent who acted last glows.

**Why:** Problem 6 asked us to send only the specialists a ticket needs. This map makes that visible in one second: on ticket 102 you should see only Boss → Facilities → Accounting light up.

## What each agent did (summary cards)

There is one card per agent that worked on the ticket. Each shows the number of tool calls, who it handed off to, chips for each distinct tool it used, its token count, and the first meaningful line of its final answer as a quote. The human gets a card too once you approve or reject something.

## How resolved tickets show up

- Status pills: **Open** (grey), **Running** (blue, with a pulsing dot), **Awaiting approval** (amber, plus "⏳ 2 awaiting you · $848.00" on the card), and **Resolved** (green).
- When a ticket becomes resolved (its run is finished and no approvals are pending), a red **RESOLVED rubber stamp** slams onto the card. It drops in from 2.6× size, overshoots and settles at a −12° tilt. A larger stamp also appears in the ticket header, and a toast says "Ticket 102 is resolved. 🎉".
- When a run finishes but still needs you, a toast says "the team is done. 2 request(s) need your approval."

**Why a stamp?** Closing a ticket should feel final and a little satisfying, like stamping paperwork at a real desk. It's also impossible to miss when scanning the queue.

## How cash shows up

- The **checking balance** is always visible twice: as a large glowing number in the right column, and as a chip in the top bar. It refreshes every 2 seconds and right after every Approve or Reject.
- When a payment is approved, the number **counts down** to the new balance over about 1.2 seconds (ease-out), flashes red, and a "−$2,400.00" label floats up and fades. You see the money leave.
- A thin bar shows how much of the cash is **already promised** to pending requests. Below it: "Left if all are approved." If pending requests add up to more than the cash on hand, the bar turns red and a warning explains that the pay tool will refuse whatever doesn't fit. This is the 101 + 102 + 103 cash conflict from Problem 6.
- A footnote says "Cash only goes out in this shop. No sales are counted," matching the shop rule.

## Approvals: the only place money moves

Each pending request is a card with a faint amber hazard-stripe background, meaning "needs a human." It shows:
- the kind (🧾 invoice, 🏠 rent, 📦 purchase order), request number and ticket
- the **vendor or payee**, a large **amount**, and what it's for (e.g. "1 × CC-TEE-WHITE size S")
- the agent's **reason**, and which agent prepared it (with its avatar)

The buttons:
- **Approve** names the amount on the button ("Approve $840.00"), so you always know what you're signing. It calls `POST /approvals/{id}/approve`.
- **Reject** asks for an optional reason inline, then calls `POST /approvals/{id}/reject`.

**If the pay tool refuses**, the card shakes, turns red and shows **"💸 Not enough cash: payment refused"** (or "⛔ Refused" for other reasons, such as the vendor still being on hold), with the backend's exact message. A red toast repeats it. A card also warns in advance when its amount is more than the cash on hand.

Approvals are signed with the name in the top bar's **"Signing as"** box. That name is recorded as `approved_by` in the payments table and in the audit trail.

## Reset database

The **↺ Reset database** button in the top bar opens a confirmation dialog. It explains what happens: cash back to $3,400, invoice 501 unpaid, all tickets reopened, requests and drafts cleared, the original database untouched and the audit trail kept. Only "Yes, reset" calls `POST /reset`. The button is disabled while any ticket is running, which matches the backend's own guard.

## Creative choices, and why they make it enjoyable

1. **A control-room look.** A deep navy background with a faint blueprint grid, glowing status lights and monospace numbers. It feels like an operations desk rather than a form, which suits a team of agents you're supervising.
2. **Agents as characters.** Avatars and colors turn a log into a conversation you can follow: you watch the Boss hand work to Inventory, and Inventory pass it to Accounting.
3. **The delegation map** answers "who did what" at a glance and rewards a lean plan.
4. **Money you can feel.** The balance counts down and flashes when you approve, so a payment never happens silently.
5. **The RESOLVED stamp** gives each finished ticket a satisfying moment.
6. **Calm by default.** Raw tool output is hidden, animations are short, and `prefers-reduced-motion` turns all motion off for people who prefer that.
7. **Honest about safety.** The approvals panel says agents can only *prepare* payments, Approve buttons name the exact amount, and refusals are loud and specific. The design reinforces the shop rules instead of hiding them.
8. **Laptop-first.** Three columns fit a 1,366–1,440 px screen, and the money column stays visible while you scroll through a long run.

## Files

- `frontend/src/config.ts`: the backend address and polling speeds (one place)
- `frontend/src/api.ts`: typed calls to every backend route
- `frontend/src/agents.ts`: agent colors, avatars, names, and friendly tool labels
- `frontend/src/App.tsx`: layout, polling, run start/finish detection, toasts
- `frontend/src/components/`: `TicketList`, `ActivityFeed`, `DelegationMap`, `AgentSummary`, `ApprovalsPanel`, `CashMeter`, `ResetButton`
- `frontend/src/styles.css`: the control-room theme and animations
