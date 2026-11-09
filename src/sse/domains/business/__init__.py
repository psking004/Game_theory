"""Business strategy domain extension package."""

from sse.domains.business.scenarios import (
    market_entry_deterrence,
    price_war,
    rd_investment_race,
)
from sse.models import FiniteNormalFormGame


class BusinessDomain:
    name = "business"
    description = "Strategic pricing wars, market entry deterrence, and R&D investment competition."

    def list_scenarios(self) -> list[str]:
        return [
            "price_war",
            "market_entry_deterrence",
            "rd_investment_race",
        ]

    def get_scenario(self, name: str) -> FiniteNormalFormGame:
        factories = {
            "price_war": price_war,
            "market_entry_deterrence": market_entry_deterrence,
            "rd_investment_race": rd_investment_race,
        }
        if name not in factories:
            raise KeyError(f"Scenario '{name}' not found in business domain.")
        return factories[name]()

