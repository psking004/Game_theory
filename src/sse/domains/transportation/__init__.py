"""Transportation domain extension package."""

from sse.domains.transportation.scenarios import (
    braess_paradox,
    corridor_peak_spreading,
    two_route_commute,
)
from sse.models import FiniteNormalFormGame


class TransportationDomain:
    name = "transportation"
    description = "Traffic route choice, Braess's paradox network equilibria, and departure time peak spreading."

    def list_scenarios(self) -> list[str]:
        return [
            "braess_paradox",
            "two_route_commute",
            "corridor_peak_spreading",
        ]

    def get_scenario(self, name: str) -> FiniteNormalFormGame:
        factories = {
            "braess_paradox": braess_paradox,
            "two_route_commute": two_route_commute,
            "corridor_peak_spreading": corridor_peak_spreading,
        }
        if name not in factories:
            raise KeyError(f"Scenario '{name}' not found in transportation domain.")
        return factories[name]()
