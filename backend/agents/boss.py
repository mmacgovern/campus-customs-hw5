"""Boss agent: reads each ticket, routes work to specialists, makes final calls,
and writes the final resolution."""

from .base import make_agent

NAME = "boss"
DELEGATES_TO = ("inventory", "accounting", "facilities", "customer_service")

# Boss reads and updates tickets; specialists do the detailed work.
TOOLS = frozenset({
    "get_shop_today", "list_tickets", "get_ticket", "update_ticket_status",
    "get_cash_balance", "list_approvals",
})


def build(model):
    return make_agent(NAME, TOOLS, model)
