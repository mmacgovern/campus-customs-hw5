"""Facilities agent: handles the shop space (leases, rent, due dates)."""

from .base import make_agent

NAME = "facilities"
DELEGATES_TO = ("accounting", "boss")

# Reads leases and cash; asks Accounting to prepare any rent payment.
TOOLS = frozenset({
    "get_shop_today", "get_ticket", "get_rent_due_and_cash", "get_cash_balance",
    "list_approvals",
})


def build(model):
    return make_agent(NAME, TOOLS, model)
