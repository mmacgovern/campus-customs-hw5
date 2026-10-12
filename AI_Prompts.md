# Homework 5 — AI Prompts Log

This file is the log of what I typed to my vibe coder (Claude Code) while building Homework 5, Campus Customs Multi-Agent Operations. Each problem below has its own section with the exact prompt(s) I typed, any follow-up prompt I needed, and one sentence on what the first prompt was missing. Prompts are copied word for word, not reworded. Sections are filled in at the end of each problem.

---

## Problem 1 - Vibe Coder Prompts

### Prompt(s) I typed

**Kickoff prompt:**

```text
▶ PROMPT 0: Project Kickoff   (copy everything in this box)
I'm starting Homework 5 for my AI Tools for Managers class. This folder is
my project (hw5). I'm not very technical, so please explain things simply.
Please set up the project:
 
1. Check that data/campus_customs.db exists. If the unzip created a nested
   folder (like hw5/hw5/data), move things so the database is at
   data/campus_customs.db relative to this folder. Do NOT change the
   database itself. If docs/HW5_instructions.pdf exists, read it; it is my
   full assignment.
 
2. Create a CLAUDE.md file at the project root with these rules, and follow
   them for the whole assignment:
   - The app is "Campus Customs Multi-Agent Operations": an MCP server in
     mcp_server/ (FastMCP), a FastAPI backend with a Pydantic AI
     multi-agent team in backend/ (Boss, Inventory, Accounting, Facilities,
     Customer Service), a React + Vite + TypeScript dashboard in frontend/,
     and graded write-ups in output/.
   - data/campus_customs.db is the ORIGINAL and must never be modified.
     All reads and writes go to data/campus_customs_new.db (the working
     copy). "Reset" means copying the original over the working copy.
   - All AI calls in my app go through Portkey (OpenAI-compatible base URL
     https://api.portkey.ai/v1) using PORTKEY_API_KEY from .env. The ONLY
     model allowed anywhere in my code, configs, or runs is gpt-6-luna.
     Keep the model name in exactly one place (backend/config.py). Never
     write any other model name anywhere in the project.
   - Shop rules:
     - "Today" for the shop is the date stored in the desk table (the field is
       named data_today or date_today). Use it to decide what is overdue. Never
       use the real calendar date.
     - Vendor lead times come from the vendors table.
     - A vendor will not ship new product while it still has an unpaid invoice.
     - Human approval is required for ANY payment or purchase. Agents only
       PREPARE a payment; a human approves it; only then does money move, and
       every related table gets updated.
     - If there is not enough cash, the pay tool must refuse. No negative
       balances, ever.
     - Cash only goes out (no revenue is modeled in this assignment).
     - Reset the working database to the original before a full run.
     - Never email customers or contact real vendors. Drafts stay on the board.
   - Never invent shop data. Shop facts come only from the database
     through the MCP tools.
   - Never print, log, or commit my API key. Never commit .env.
   - After finishing each problem, update AI_Prompts.md: add the problem
     number and title, the prompt(s) I typed for it (exactly as typed), and
     any follow-up prompt plus one sentence on what was missing after the
     first prompt.
   - Work on one problem at a time. When done, tell me in plain English
     what you did, which files changed, and how I can check it.
 
3. Check my Python version, create a virtual environment in .venv, create
   requirements.txt with what this project will need (fastmcp,
   pydantic-ai, fastapi, uvicorn, python-dotenv, httpx, and anything else
   needed), and install it into .venv.
 
4. Create .env.example containing the line PORTKEY_API_KEY= (blank).
   Create an empty .env file. Create a .gitignore that ignores .env,
   .venv/, node_modules/, __pycache__/, frontend/dist/, and docs/, but does
   NOT ignore the .db files in data/.
 
5. Create the empty folders from the expected layout: mcp_server/,
   backend/prompts/, frontend/, output/.
 
When done, give me simple step-by-step instructions for opening .env on my
computer and pasting my Portkey key into it. Do not ask me to paste the key
into this chat.
```

**Problem 1 prompt:**

```text
Problem 1: Create AI_Prompts.md at the project root. This is the log of
what I typed to my vibe coder (Claude Code) for Homework 5.
 
- Start with a title and a one-paragraph intro explaining that.
- Add one section per problem, with these headings:
  Problem 1 - Vibe Coder Prompts
  Problem 2 - Study the Campus Customs Database
  Problem 3 - Build the MCP Server
  Problem 4 - Add the MCP Server to Vibe Coder and Test Each Tool
  Problem 5 - Build the Agent Team and Grow the MCP Tools
  Problem 6 - Plan the Three Tickets
  Problem 7 - Backend Routes
  Problem 8 - Agent Dashboard
  Problem 9 - Resolve the Tickets
  Problem 10 - Reflection
  Problem 11 - Submit to GitHub
- Under each heading add three parts: "Prompt(s) I typed",
  "Follow-up prompt (if needed)", and "What was lacking after the first
  prompt (one sentence)".
- Fill in Problem 1 now with my kickoff prompt and this prompt, exactly as
  I typed them. Leave the other sections as clearly marked placeholders.
- Remember: at the end of every future problem, fill in that problem's
  section with the prompts I actually typed.
```

### Follow-up prompt (if needed)

None needed.

### What was lacking after the first prompt (one sentence)

N/A — no follow-up was needed.

---

## Problem 2 - Study the Campus Customs Database

### Prompt(s) I typed

```text
Problem 2 - Study the Campus Customs Database.
 
1. Make the working copy: copy data/campus_customs.db to
   data/campus_customs_new.db (overwrite if it already exists). Do not
   modify the original.
2. Open the database read-only. For every table, list every column (name
   and type), the row count, and 2-3 sample rows.
3. Find the three open tickets (101, 102, 103). For each, explain in plain
   English what it's asking for, and trace exactly how it links to other
   tables (for example: which SKU and size in inventories, which vendor,
   which invoice, which lease, which cash account). Show me the actual
   rows that matter.
4. Find the shop's "today" date in the desk table and tell me what is
   overdue as of that date.
5. Create output/harness.md titled "Campus Customs Agent Harness" with a
   section "1. Database Tables". For each table: the table name, a list of
   its fields, and one short line on why that table matters to the agents
   (name the ticket it relates to when possible). Add a short subsection
   "Open Tickets at a Glance" summarizing tickets 101, 102 and 103 and the
   tables each one touches.
 
Use only what is actually in the database. Finish with a plain-English
summary of the three tickets for me, and update AI_Prompts.md.
```

### Follow-up prompt (if needed)

None needed.

### What was lacking after the first prompt (one sentence)

N/A — no follow-up was needed.

---

## Problem 3 - Build the MCP Server

### Prompt(s) I typed

```text
Problem 3 - Build the MCP Server.
 
Using what you learned about tickets 101, 102 and 103, build an MCP server
in mcp_server/server.py using FastMCP.
- It must use data/campus_customs_new.db. Build the file path from the
  location of server.py so it works no matter which folder I run it from.
  Never touch data/campus_customs.db.
- Write exactly three tools for now: the three most useful ones for
  unlocking the open tickets (ideally one per ticket). Give them clear,
  descriptive names. Each tool needs a clear docstring, simple inputs,
  returns real rows from the database as structured data, and returns a
  clear message if nothing is found. Never make up data.
- The server should run over stdio with: python mcp_server/server.py
- Test each tool by calling its Python function directly against the
  working database and show me the results. (No need to connect it to
  Claude Code yet.)
 
Then:
- Add a section "2. MCP Tools" to output/harness.md. For each tool list:
  its name, which table(s) it reads, which ticket it helps unlock (101,
  102, or 103), and one specific sentence on why it's the right tool for
  that ticket. Mention the actual SKU, vendor, invoice, or lease involved.
  No vague lines like "reads inventories".
- Create mcp_server/README.md explaining what the MCP server is for, that
  it uses data/campus_customs_new.db, how to run it, and its three tools.
- Update AI_Prompts.md.
```

### Follow-up prompt (if needed)

```text
Follow-Up Prompt for Problem 3. The harness lines for the tools are too vague. Tie each tool to the exact ticket number and the specific SKU/vendor/lease/invoice it helps with. also Show me the output of each tool side by side with a direct SQL query of the same rows so I can see they match.
```

### What was lacking after the first prompt (one sentence)

The first prompt didn't ask for proof that the tools return the same rows as the database, and the harness descriptions weren't tied tightly enough to the exact ticket and its specific SKU, vendor, lease or invoice.

---

## Problem 4 - Add the MCP Server to Vibe Coder and Test Each Tool

### Prompt(s) I typed

**Part 1:**

```text
Problem 4 (part 1) - Connect my MCP server to Claude Code.
 
Create .mcp.json at the project root that registers our server as a stdio
MCP server named "campus-customs". It should run mcp_server/server.py with
the Python inside .venv, using paths that work on my computer (check
whether I'm on Windows or Mac). Make sure the server starts cleanly when
launched that way.
 
Then tell me exactly what to do to load it (I'll need to exit and restart
Claude Code and approve the server). Stop and wait for me after that.
```

### Follow-up prompt (if needed)

**Part 2 (typed after restarting and connecting the server):**

```text
Problem 4 (part 2) - The campus-customs MCP server is now connected.
 
Test each of our three MCP tools by actually calling them through the MCP
connection (not by running Python directly). For each tool, use a realistic
question tied to the ticket it helps with.
 
Then verify each output against data/campus_customs_new.db with a direct
SQL query and confirm the values match.
 
Save the evidence in output/mcp_smoke.json as a list with one entry per
tool containing:
  "prompt"              - the question asked of you
  "tool"                - the MCP tool name
  "arguments"           - the inputs used
  "output"              - the exact tool output
  "verified_against_db" - true/false
  "verification_query"  - the SQL used to check it
 
Also confirm .mcp.json is saved at the project root. Update AI_Prompts.md
for Problem 4 (my prompts were the ".mcp.json" prompt before the restart
and this one).
```

### What was lacking after the first prompt (one sentence)

The first prompt only registered and started the server, so it didn't test the tools through the live MCP connection, check them against the database, or save any evidence file.

---

## Problem 5 - Build the Agent Team and Grow the MCP Tools

### Prompt(s) I typed

```text
Problem 5 - Build the agent team and grow the MCP tools.
 
Build the Campus Customs agent team with Pydantic AI in backend/.
Check the installed Pydantic AI version and use its current API
(don't guess).
 
MODEL AND KEYS
- Every agent uses gpt-6-luna through Portkey only: OpenAI-compatible base
  URL https://api.portkey.ai/v1, key from PORTKEY_API_KEY in .env (load it
  with python-dotenv). The model name lives only in backend/config.py.
  No other model name may appear anywhere in the project.
 
THE FIVE AGENTS (one Python file each, e.g. backend/agents/)
- Boss: reads each ticket, decides who should work on it, makes final
  calls, and writes the final resolution.
- Inventory: checks stock by SKU and size, spots shortfalls, and figures
  out which vendor can restock (using vendor lead times and the unpaid-
  invoice rule).
- Accounting: watches cash and invoices, checks margins, and PREPARES
  payments or purchase orders for human approval. It can never execute a
  payment.
- Facilities: handles the shop space (leases, rent, due dates).
- Customer Service: drafts messages for customers. Drafts stay on the
  board; it never sends anything.
 
FULL CONNECTIVITY
- Any agent can delegate to any other agent through a delegate tool
  (to_agent, task). Pass the shared usage object so token use is counted
  across the whole run.
- Guardrails: max delegation depth of 3, no delegating to yourself, and a
  per-run request/token limit using Pydantic AI UsageLimits.
 
AGENT PROMPTS
- Write detailed system prompts, one file each in backend/prompts/:
  boss.md, inventory.md, accounting.md, facilities.md,
  customer_service.md. Each must cover: role and scope; what is NOT its
  job; which teammates to delegate to and when; which MCP tools to use;
  every shop rule that applies to it; a step-by-step working method; what
  its final answer should contain; and what to do when information is
  missing (say so, never invent). Shop rules:
- "Today" for the shop is the date stored in the desk table (the field is
  named data_today or date_today). Use it to decide what is overdue. Never
  use the real calendar date.
- Vendor lead times come from the vendors table.
- A vendor will not ship new product while it still has an unpaid invoice.
- Human approval is required for ANY payment or purchase. Agents only
  PREPARE a payment; a human approves it; only then does money move, and
  every related table gets updated.
- If there is not enough cash, the pay tool must refuse. No negative
  balances, ever.
- Cash only goes out (no revenue is modeled in this assignment).
- Reset the working database to the original before a full run.
- Never email customers or contact real vendors. Drafts stay on the board.
 
DATA TYPES
- Put Pydantic models in backend/models.py (for example: Ticket,
  AuditEvent, Delegation, PendingApproval, TicketResult, CashBalance).
 
MCP TOOLS (the only way to touch shop data)
- Agents get shop data ONLY through our MCP server (use Pydantic AI's MCP
  stdio client to launch mcp_server/server.py). Do not build a second data
  layer in the backend that queries the database directly.
- Add the tools needed to fully resolve tickets 101, 102 and 103, based on
  what those tickets actually need. For example: get shop "today" date,
  list/get tickets, check stock, vendors and lead times, unpaid invoices
  by vendor, lease/rent due, cash balance, margins from pricing, create a
  pending payment or purchase order request, save a customer message
  draft, update ticket status, and a pay tool.
- Payment safety: agents can only create PENDING approval requests (stored
  in a new approvals table in the working database; create it if missing
  so it still works after a reset). The pay/execute tool must be hidden
  from every agent (use a filtered toolset); only the backend approval
  route will call it later. The pay tool must refuse if cash would go
  negative, and when it pays it must update every related table
  (cash_accounts, payments, and invoice or lease status).
 
AUDIT TRAIL
- Every agent-loop step appends an entry to output/audit_trail.json:
  timestamp, run_id, ticket_id, agent, step type (thinking / tool_call /
  tool_result / delegation / final), tool name and arguments, a short
  result, and tokens used. Append only; never wipe the file. Keep it
  valid JSON.
 
DOCS
- Update output/harness.md: add "3. Agents" (each agent, its job, who it
  usually delegates to); update "2. MCP Tools" to list EVERY tool and the
  table(s) it uses, marking which are agent-visible vs. approval-only; add
  "4. Safety and Guardrails" covering the guardrails a real business
  would want when agents touch real customers and real money, plus the
  limits that keep token use in check.
- Update mcp_server/README.md so the tool list matches.
 
TEST
- Write backend/smoke_test.py that runs the Boss on ticket 101 with a low
  usage limit, prints what happened, and then resets the working database
  (copy the original over it). Run it once and show me the result in plain
  English.
- Update AI_Prompts.md.
```

### Follow-up prompt (if needed)

None needed.

### What was lacking after the first prompt (one sentence)

N/A — no follow-up was needed.

---

## Problem 6 - Plan the Three Tickets

### Prompt(s) I typed

```text
Problem 6 - Plan the three tickets (Expected only).
 
Before we wire the backend, write what I expect the team to do. Base it on
the actual ticket rows and related data, our MCP tool list, and the agent
prompts in backend/prompts/.
 
Create output/desk_tickets.html: one self-contained page (all CSS and JS
inside the file, no internet needed) that opens by double-clicking. It has
five tabs: Ticket 101, Ticket 102, Ticket 103, Cash, Reflection. Make it
clean and easy to read.
 
On each ticket tab show a short ticket summary, then an "Expected" section
with:
- Who the Boss should call first, and why (tie it to the ticket's data).
- The specific delegations expected, in order, e.g.
  "Boss -> Inventory: check SKU X size M stock" then
  "Inventory -> Accounting: does vendor Y have an unpaid invoice?".
  Only include the specialists the ticket really needs. Do NOT send every
  specialist on every ticket. Also list which agents should NOT be
  involved and why.
- The exact MCP tool names the run should use.
- Any human approvals expected, with dollar amounts if the data shows them.
 
Below that, add an empty "Actual" section on each ticket tab with the note
"To be filled after the run (Problem 9)". On the Cash and Reflection tabs,
just put a short "Coming later" note.
 
Update AI_Prompts.md.
```

### Follow-up prompt (if needed)

```text
Follow up Prompt Claude - The plan for ticket N involves too many agents. Trim it to only the specialists that ticket truly needs and explain why each one is there. Add the specific SKU, vendor, invoice or lease and dollar amounts to each Expected section so it's concrete.
```

### What was lacking after the first prompt (one sentence)

The first prompt didn't require a stated reason for each specialist or the exact SKU, vendor, invoice, lease and dollar figures in each Expected section, so the plan carried extra hand-offs and read less concretely than it should.

---

## Problem 7 - Backend Routes

### Prompt(s) I typed

```text
Problem 7 - Backend routes.
 
In backend/main.py create a FastAPI app that uses our agent team. It must
start with "uvicorn main:app --reload --port 8000" run from INSIDE the
backend/ folder, so make imports and file paths work from there.
 
Add these routes:
- GET  /tickets - the three tickets and whether each is open or resolved
  (also show "running" or "awaiting approval" when that applies).
- POST /tickets/{ticket_id}/run - run the agent team on that ticket. Run it
  in the background and return a run_id right away, so the dashboard can
  poll events while it works.
- GET  /events?ticket_id=&since= - recent agent events: which agent, what
  it said, which tools it used, and delegations, oldest first.
- GET  /approvals - pending payment/purchase requests prepared by agents.
- POST /approvals/{approval_id}/approve - a human clicked Approve. This is
  the ONLY place money moves: call the MCP pay tool, which refuses if
  there isn't enough cash, and updates the related tables. Return a clear
  error message if refused.
- POST /approvals/{approval_id}/reject - mark it rejected.
- GET  /cash - the current checking balance from cash_accounts.
- POST /reset - copy data/campus_customs.db over data/campus_customs_new.db
  (never touch the original), recreate helper tables, and clear in-memory
  run state. Do not wipe output/audit_trail.json.
- GET  /health - simple check.
 
A ticket is "resolved" when its run has finished and it has no pending
approvals. All shop data still flows through the MCP server.
Allow CORS from http://localhost:5173 and http://127.0.0.1:5173.
 
Then start the server yourself, test every route with real requests, show
me the results in plain English, call /reset at the end, and stop the
server.
 
Add section "5. API Routes" to output/harness.md with one line per route:
URL - what it does. Update AI_Prompts.md, then tell me in simple steps how
to start the backend myself.
```

### Follow-up prompt (if needed)

None needed.

### What was lacking after the first prompt (one sentence)

N/A — no follow-up was needed.

---

## Problem 8 - Agent Dashboard

### Prompt(s) I typed

```text
Problem 8 - Agent dashboard.
 
Build the dashboard in frontend/ with React + Vite + TypeScript. It talks
to our backend at http://localhost:8000 (put that address in one config
constant). Make sure the backend allows the Vite origin
http://localhost:5173 (CORS).
 
The board must:
- List all three tickets with a status (open / running / awaiting
  approval / resolved).
- Let me pick a ticket and click a button to start the agent team on it.
- Show live activity while it runs (poll /events every 1-2 seconds): each
  agent's messages, tool calls, and delegations, with each agent visually
  distinct (its own color, icon/avatar, and name).
- Mark the ticket resolved when the run finishes.
- Show a short summary card of what each agent did on that ticket.
- Show pending pay/purchase requests (vendor, amount, reason) with Approve
  and Reject buttons that call the backend. Show a clear message if the
  pay tool refuses (not enough cash).
- Always show the checking balance and refresh it after approvals (it
  should visibly drop after an approved payment).
- Include a "Reset database" button with a confirmation step.
 
Design: make it look great and feel like a real operations desk people
would enjoy using. Be creative: for example a "shop floor" or "control
room" theme, agent avatars, a visual of who delegated to whom, an animated
balance change, and a satisfying "resolved" stamp. Keep it readable and
make it work on a laptop screen.
 
Install the packages, run a build to catch TypeScript errors, and fix them.
 
Write output/design.md describing the layout, how the agents read
differently, how resolved tickets and cash show up, and why, including
the creative choices that make it special and enjoyable to use.
 
Update AI_Prompts.md, then give me simple step-by-step instructions to
start the backend and the dashboard in two separate terminal windows.
```

### Follow-up prompt (if needed)

None needed.

### What was lacking after the first prompt (one sentence)

N/A — no follow-up was needed.

---

## Problem 9 - Resolve the Tickets

### Prompt(s) I typed

**Part 1:**

```text
Problem 9 (part 1) - Prepare for the full run.
 
1. Reset the working database: copy data/campus_customs.db over
   data/campus_customs_new.db (or call POST /reset if the backend is
   running). Confirm all three tickets show as open.
2. Read the starting checking balance from cash_accounts in the working
   database, tell me, and save it with a timestamp to
   output/starting_balance.txt.
3. Check that the backend (http://localhost:8000/health) and dashboard
   (http://localhost:5173) are running. If not, tell me exactly how to
   start them.
Then wait while I run tickets 101, 102 and 103 on the board.
```

**Part 2:**

```text
Problem 9 (part 2) - I've run all three tickets on the board and they show
resolved. Now document the run:
 
1. Read output/audit_trail.json (only the runs since the reset), the
   approvals, and the working database.
2. In output/desk_tickets.html, fill the "Actual" section on each ticket
   tab: which agents worked, what they delegated to whom (in order), which
   MCP tools were used, and the approvals I gave. Keep the Expected
   section unchanged and add a short "Expected vs Actual" note.
3. Fill the Cash tab:
   - Starting checking balance after the reset
     (from output/starting_balance.txt).
   - For each ticket: how cash changed when it resolved and why (which
     payment or purchase, vendor, invoice or lease, dollar amount).
   - Ending checking balance.
   Check the math: starting balance minus all approved payments must equal
   the ending balance, and the ending balance must equal cash_accounts in
   data/campus_customs_new.db. Show me the check.
4. Create output/resolved_tickets.json: for each ticket: id, final status,
   short outcome, what each agent contributed, and any human approvals
   (approval id, amount, vendor, time approved).
5. Create output/resolved_board.html: a double-clickable page showing a
   screenshot of the React board for each resolved ticket (101, 102, 103).
   Take the screenshots yourself with Playwright from
   http://localhost:5173 (select each ticket so its resolved view shows)
   and embed them in the page so it works offline. If you can't take them,
   tell me and I'll save screenshots into output/screenshots/ myself.
6. Confirm output/audit_trail.json contains these real runs (appended, not
   overwritten).
7. Finish output/harness.md so it covers tables, MCP tools, the five
   agents, API routes, the dashboard (summarize and link design.md), and
   safety rules.
8. Update AI_Prompts.md.
```

### Follow-up prompt (if needed)

None needed.

### What was lacking after the first prompt (one sentence)

N/A — no follow-up was needed.

---

## Problem 10 - Reflection

### Prompt(s) I typed

```text
Problem 10 - Reflection.
 
Help me write the Reflection tab in output/desk_tickets.html. Before you
write anything, ask me 4 quick questions about my own impressions (what
surprised me, what frustrated me, which agent impressed or disappointed
me, and what I'd change). Wait for my answers and work them in.
 
Use as evidence: the ticket tabs (Expected vs Actual), the Cash tab,
output/resolved_tickets.json, and output/audit_trail.json. Every answer
must cite specific Campus Customs details: ticket numbers, agent names,
MCP tool names, SKUs, vendors, leases, and dollar amounts.
 
Answer these, each under its own heading, in detail:
1. How would I evaluate the agents' performance on each ticket, and why?
   (One part per ticket: accuracy, efficiency/token use, rule-following,
   approvals.)
2. For each ticket, how did Actual compare to my Expected plan?
3. What would have been simpler as one agent with tools, and why?
4. Three new problems Campus Customs might face that this team COULD solve
   with the tools we built (say which agents and tools would handle each).
5. Three new problems this team could NOT solve with our tools, and the
   new tools and agents I'd need to solve them.
 
Write in a first-person, conversational student voice. Keep the page's
style consistent. Update AI_Prompts.md.
```

**My answers to Claude's 4 questions (part of the same problem):**

```text
1.) What Surprised Me. I was impressed with how fast the runs were executed and how well the agents worked with eachother for the outcomes. 2.) What frustrated me - the board saying “resolved” while the database said something else, or token costs (about 48,000–75,000 per ticket 3.) Which agent impressed you - The Boss,  which disappointed you - The Boss missed that you had rejected the hoodie order. 4.) What's one thing you'd change - I would have reduced the redundancies to make the overal process for efficient (if possible).
```

### Follow-up prompt (if needed)

None needed.

### What was lacking after the first prompt (one sentence)

N/A — no follow-up was needed.

---

## Problem 11 - Submit to GitHub

### Prompt(s) I typed

_[PLACEHOLDER — to be filled in at the end of Problem 11]_

### Follow-up prompt (if needed)

_[PLACEHOLDER — to be filled in at the end of Problem 11]_

### What was lacking after the first prompt (one sentence)

_[PLACEHOLDER — to be filled in at the end of Problem 11]_
