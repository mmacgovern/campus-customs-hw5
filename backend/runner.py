"""Run the agent team on one ticket, starting with the Boss."""

import uuid

from pydantic_ai import UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import RunUsage

from .agents import build_team
from .agents.base import RunState, TeamDeps, run_agent
from .audit import append_event
from .config import default_usage_limits
from .mcp_client import get_mcp_toolset
from .models import TicketResult


def new_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:10]}"


async def run_ticket(ticket_id: int, usage_limits: UsageLimits | None = None,
                     run_id: str | None = None) -> TicketResult:
    """Have the Boss work one ticket. Every agent shares one usage object and one limit."""
    run_id = run_id or new_run_id()
    state = RunState(run_id=run_id, ticket_id=ticket_id,
                     usage_limits=usage_limits or default_usage_limits(),
                     team=build_team())
    usage = RunUsage()
    deps = TeamDeps(agent_name="boss", depth=0, chain=("boss",), state=state)
    prompt = (f"Work ticket {ticket_id}. Read it with get_ticket, delegate to the right teammates, "
              "and finish with the final resolution as described in your instructions.")

    status, resolution = "completed", ""
    try:
        async with get_mcp_toolset():  # one MCP server process for the whole run
            resolution = await run_agent("boss", prompt, deps, usage=usage)
    except UsageLimitExceeded as exc:
        status, resolution = "stopped_by_limit", f"Run stopped by the usage limit: {exc}"
        append_event(run_id=run_id, ticket_id=ticket_id, agent="boss", step_type="error", result=resolution)
    except Exception as exc:  # record, then surface a readable result
        status, resolution = "error", f"{type(exc).__name__}: {exc}"
        append_event(run_id=run_id, ticket_id=ticket_id, agent="boss", step_type="error", result=resolution)

    return TicketResult(
        run_id=run_id, ticket_id=ticket_id, status=status, resolution=resolution,
        delegations=state.delegations, requests=usage.requests, tool_calls=usage.tool_calls,
        input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
        total_tokens=usage.input_tokens + usage.output_tokens,
    )
