# HW5 — Campus Customs Multi-Agent Operations

The user is not very technical: explain things simply.

## The app
- `mcp_server/` — MCP server (FastMCP). The only way agents touch shop data.
- `backend/` — FastAPI backend with a Pydantic AI multi-agent team:
  Boss, Inventory, Accounting, Facilities, Customer Service. Agent prompts in `backend/prompts/`.
- `frontend/` — React + Vite + TypeScript dashboard.
- `output/` — graded write-ups.

## Databases
- `data/campus_customs.db` is the ORIGINAL. Never modify it.
- All reads and writes go to `data/campus_customs_new.db` (the working copy).
- "Reset" = copy the original over the working copy.
- Reset the working database to the original before a full run.

## AI / model
- All AI calls go through Portkey (OpenAI-compatible base URL `https://api.portkey.ai/v1`)
  using `PORTKEY_API_KEY` loaded from `.env` at run time.
- The ONLY model allowed anywhere in code, configs, or runs is `gpt-6-luna`.
- The model name lives in exactly one place: `backend/config.py`. Everything else imports it.
- Never write any other model name anywhere in the project.

## Shop rules
- "Today" for the shop is the date in the `desk` table (field `data_today` or `date_today`).
  Use it to decide what is overdue. Never use the real calendar date.
- Vendor lead times come from the `vendors` table.
- A vendor will not ship new product while it still has an unpaid invoice.
- Human approval is required for ANY payment or purchase. Agents only PREPARE a payment;
  a human approves it; only then does money move, and every related table gets updated.
- If there is not enough cash, the pay tool must refuse. No negative balances, ever.
- Cash only goes out (no revenue is modeled).
- Never email customers or contact real vendors. Drafts stay on the board.
- Never invent shop data. Shop facts come only from the database through the MCP tools.

## Secrets
- Never print, log, or commit the API key. Never commit `.env`.
- Never open or read `.env`. `.env.example` is fine to read and edit.

## Workflow
- Work on one problem at a time.
- After finishing each problem, update `AI_Prompts.md`: problem number and title, the prompt(s)
  the user typed for it (exactly as typed), and any follow-up prompt plus one sentence on what
  was missing after the first prompt.
- When done with a problem, explain in plain English what was done, which files changed,
  and how the user can check it.

## Environment
- Python 3.12, virtual environment in `.venv` (`.venv\Scripts\python`).
- Dependencies in `requirements.txt`.
