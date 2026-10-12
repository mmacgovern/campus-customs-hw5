"""The Campus Customs agent team. build_team() returns every agent by name."""

from pydantic_ai import Agent

from . import accounting, boss, customer_service, facilities, inventory
from .base import TEAM, build_model

MODULES = {m.NAME: m for m in (boss, inventory, accounting, facilities, customer_service)}
assert tuple(MODULES) == TEAM


def build_team() -> dict[str, Agent]:
    model = build_model()
    return {name: module.build(model) for name, module in MODULES.items()}
