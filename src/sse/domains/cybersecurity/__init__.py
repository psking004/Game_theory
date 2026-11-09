"""Cybersecurity domain extension package."""

from sse.domains.cybersecurity.scenarios import (
    apt_defense_scenario,
    security_investment_2firm,
    simple_network_defense,
)
from sse.models import FiniteNormalFormGame


class CybersecurityDomain:
    name = "cybersecurity"
    description = "Attacker-defender resource allocation, APT mitigation, and investment games."

    def list_scenarios(self) -> list[str]:
        return [
            "simple_network_defense",
            "apt_defense_scenario",
            "security_investment_2firm",
        ]

    def get_scenario(self, name: str) -> FiniteNormalFormGame:
        factories = {
            "simple_network_defense": simple_network_defense,
            "apt_defense_scenario": apt_defense_scenario,
            "security_investment_2firm": security_investment_2firm,
        }
        if name not in factories:
            raise KeyError(f"Scenario '{name}' not found in cybersecurity domain.")
        return factories[name]()
