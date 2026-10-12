"""Smoke test: run the Boss on ticket 101 with a low usage limit, print what
happened, then reset the working database.

Run from the project folder:
    .venv\\Scripts\\python -m backend.smoke_test
"""

import asyncio
import sys
from pathlib import Path

if __package__ in (None, ""):  # allow `python backend/smoke_test.py` too
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "backend"

from pydantic_ai import UsageLimits

from backend.config import AUDIT_TRAIL
from backend.db_reset import reset_working_db
from backend.runner import run_ticket

LOW_LIMITS = UsageLimits(request_limit=30, tool_calls_limit=40, total_tokens_limit=150_000)


async def main() -> None:
    reset_working_db()  # always start from the original data
    print("Running the Boss on ticket 101 (low usage limit)...\n")
    try:
        report(await run_ticket(101, usage_limits=LOW_LIMITS))
    finally:
        reset_working_db()
        print("\nWorking database reset (original copied over campus_customs_new.db).")


def report(result) -> None:
    print(f"Run id:  {result.run_id}")
    print(f"Status:  {result.status}")
    print(f"Usage:   {result.requests} model requests, {result.tool_calls} tool calls, "
          f"{result.total_tokens:,} tokens (in {result.input_tokens:,} / out {result.output_tokens:,})")
    print("\nDelegations:")
    for d in result.delegations or []:
        flag = "ok" if d.allowed else f"REFUSED ({d.refusal_reason})"
        print(f"  depth {d.depth}: {d.from_agent} -> {d.to_agent} [{flag}]")
    if not result.delegations:
        print("  (none)")
    print("\nBoss's final resolution:\n")
    print(result.resolution)
    print(f"\nEvery step is in output/{AUDIT_TRAIL.name} (run id {result.run_id}).")


if __name__ == "__main__":
    asyncio.run(main())
