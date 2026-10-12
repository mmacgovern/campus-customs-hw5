"""Customer Service agent: drafts messages for customers. Drafts stay on the
board; it never sends anything."""

from .base import make_agent

NAME = "customer_service"
DELEGATES_TO = ("inventory", "accounting", "boss")

# Can read the ticket and stock, and save drafts. No money tools.
TOOLS = frozenset({
    "get_shop_today", "get_ticket", "check_stock_and_pricing", "save_customer_draft",
})


def build(model):
    return make_agent(NAME, TOOLS, model)
