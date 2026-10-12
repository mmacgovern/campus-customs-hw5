"""Inventory agent: checks stock by SKU and size, spots shortfalls, and finds
which vendor can restock (lead times + the unpaid-invoice rule)."""

from .base import make_agent

NAME = "inventory"
DELEGATES_TO = ("accounting", "customer_service", "boss")

# Read-only: stock, vendors, lead times, vendor holds.
TOOLS = frozenset({
    "get_shop_today", "get_ticket", "check_stock_and_pricing", "list_vendors",
    "get_unpaid_invoices", "get_invoice_and_vendor_hold",
})


def build(model):
    return make_agent(NAME, TOOLS, model)
