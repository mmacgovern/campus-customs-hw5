"""Accounting agent: watches cash and invoices, checks margins, and PREPARES
payments or purchase orders for human approval. It can never execute a payment."""

from .base import make_agent

NAME = "accounting"
DELEGATES_TO = ("inventory", "facilities", "boss")

# Can prepare (not execute) payments and purchase orders.
# The pay tool is approval-only and is filtered out for every agent.
TOOLS = frozenset({
    "get_shop_today", "get_ticket", "get_cash_balance", "get_unpaid_invoices",
    "get_invoice_and_vendor_hold", "get_rent_due_and_cash", "calculate_margin",
    "check_stock_and_pricing", "list_vendors", "list_approvals",
    "create_payment_request", "create_purchase_order_request",
})


def build(model):
    return make_agent(NAME, TOOLS, model)
