"""Shared machinery for the agent team.

- build_model(): the one model, via Portkey.
- make_agent(): builds an agent with its prompt file, its filtered MCP tools,
  and the delegate tool.
- delegate(): lets any agent hand a task to any other agent, with guardrails
  (no self-delegation, max depth, shared usage + UsageLimits).
- run_agent(): runs one agent step by step and writes every step to the audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic_ai import Agent, RunContext, UsageLimits
from pydantic_ai.messages import (
    RetryPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RunUsage

from ..audit import append_event, short
from ..config import (
    MAX_DELEGATION_DEPTH,
    MODEL_NAME,
    PORTKEY_BASE_URL,
    PROMPTS_DIR,
    get_portkey_api_key,
)
from ..mcp_client import agent_toolset
from ..models import Delegation

TEAM = ("boss", "inventory", "accounting", "facilities", "customer_service")


@dataclass
class RunState:
    """Shared by every agent in one run."""
    run_id: str
    ticket_id: int | None
    usage_limits: UsageLimits
    team: dict[str, Agent] = field(default_factory=dict)
    delegations: list[Delegation] = field(default_factory=list)


@dataclass
class TeamDeps:
    """Per-agent context: who is running, how deep in the delegation chain."""
    agent_name: str
    depth: int
    chain: tuple[str, ...]
    state: RunState


def build_model() -> OpenAIResponsesModel:
    # The Responses API (/v1/responses) is required for tool calling with this model.
    provider = OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=get_portkey_api_key())
    return OpenAIResponsesModel(MODEL_NAME, provider=provider)


def load_prompt(agent_name: str) -> str:
    return (PROMPTS_DIR / f"{agent_name}.md").read_text(encoding="utf-8")


async def delegate(ctx: RunContext[TeamDeps], to_agent: str, task: str) -> str:
    """Hand a task to a teammate and get their answer back.

    Args:
        to_agent: One of: boss, inventory, accounting, facilities, customer_service.
        task: A clear, self-contained request. Include the ticket number and every
            fact the teammate needs (SKU, size, qty, invoice id, lease id, amounts).
    """
    deps = ctx.deps
    state = deps.state
    to_agent = to_agent.strip().lower().replace(" ", "_")
    new_depth = deps.depth + 1

    refusal = None
    if to_agent not in TEAM:
        refusal = f"Unknown agent '{to_agent}'. Choose one of: {', '.join(TEAM)}."
    elif to_agent == deps.agent_name:
        refusal = "You cannot delegate to yourself. Do the work or pick a different teammate."
    elif new_depth > MAX_DELEGATION_DEPTH:
        refusal = (f"Delegation depth limit ({MAX_DELEGATION_DEPTH}) reached "
                   f"(chain: {' -> '.join(deps.chain)}). Finish with what you have and say what is missing.")

    record = Delegation(from_agent=deps.agent_name, to_agent=to_agent, task=task, depth=new_depth,
                        allowed=refusal is None, refusal_reason=refusal)
    state.delegations.append(record)
    append_event(run_id=state.run_id, ticket_id=state.ticket_id, agent=deps.agent_name,
                 depth=deps.depth, step_type="delegation", tool_name="delegate",
                 arguments={"to_agent": to_agent, "task": task},
                 result=refusal or f"Handing off to {to_agent} (depth {new_depth}).")
    if refusal:
        return f"DELEGATION REFUSED: {refusal}"

    child = TeamDeps(agent_name=to_agent, depth=new_depth,
                     chain=deps.chain + (to_agent,), state=state)
    header = (f"[Delegated by {deps.agent_name} | ticket {state.ticket_id} | "
              f"delegation depth {new_depth} of {MAX_DELEGATION_DEPTH}]\n\n")
    # Same usage object => tokens and requests are counted across the whole run.
    output = await run_agent(to_agent, header + task, child, usage=ctx.usage)
    record.result_summary = short(output, 300)
    return output


def make_agent(name: str, allowed_tools: frozenset[str], model) -> Agent[TeamDeps, str]:
    return Agent(
        model,
        name=name,
        deps_type=TeamDeps,
        instructions=load_prompt(name),
        toolsets=[agent_toolset(allowed_tools)],
        tools=[delegate],
        retries=2,
    )


def _tokens(response) -> int:
    u = getattr(response, "usage", None)
    return (u.input_tokens + u.output_tokens) if u else 0


async def run_agent(name: str, prompt: str, deps: TeamDeps, usage: RunUsage) -> str:
    """Run one agent, logging every loop step (thinking, tool calls, results, final)."""
    state = deps.state
    agent = state.team[name]
    base = dict(run_id=state.run_id, ticket_id=state.ticket_id, agent=name, depth=deps.depth)
    final_tokens = 0

    async with agent.iter(prompt, deps=deps, usage=usage,
                          usage_limits=state.usage_limits) as run:
        async for node in run:
            if Agent.is_call_tools_node(node):
                response = node.model_response
                tokens = _tokens(response)
                has_calls = any(isinstance(p, ToolCallPart) for p in response.parts)
                for part in response.parts:
                    if isinstance(part, ThinkingPart) and part.content:
                        append_event(**base, step_type="thinking", result=part.content, tokens=tokens)
                    elif isinstance(part, TextPart) and has_calls and part.content.strip():
                        append_event(**base, step_type="thinking", result=part.content, tokens=tokens)
                    elif isinstance(part, ToolCallPart):
                        append_event(**base, step_type="tool_call", tool_name=part.tool_name,
                                     arguments=part.args_as_dict(), tokens=tokens)
                    else:
                        continue
                    tokens = 0  # count each model response's tokens once
                if not has_calls:
                    # Final text answer: its tokens are logged with the 'final' event below.
                    final_tokens = tokens
            elif Agent.is_model_request_node(node):
                for part in node.request.parts:
                    if isinstance(part, ToolReturnPart):
                        append_event(**base, step_type="tool_result", tool_name=part.tool_name,
                                     result=part.model_response_str())
                    elif isinstance(part, RetryPromptPart) and part.tool_name:
                        append_event(**base, step_type="tool_result", tool_name=part.tool_name,
                                     result=f"RETRY: {part.model_response()}")
        output = run.result.output

    append_event(**base, step_type="final", result=output,
                 tokens=final_tokens)
    return output
