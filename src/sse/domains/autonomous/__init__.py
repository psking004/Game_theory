"""Autonomous systems domain extension package."""

from sse.domains.autonomous.scenarios import (
    autonomous_intersection,
    cooperative_perimeter_patrol,
    dynamic_spectrum_access,
)
from sse.models import FiniteNormalFormGame


class AutonomousSystemsDomain:
    name = "autonomous"
    description = "Decentralized intersection crossing, cognitive radio spectrum access, and multi-robot patrolling."

    def list_scenarios(self) -> list[str]:
        return [
            "autonomous_intersection",
            "dynamic_spectrum_access",
            "cooperative_perimeter_patrol",
        ]

    def get_scenario(self, name: str) -> FiniteNormalFormGame:
        factories = {
            "autonomous_intersection": autonomous_intersection,
            "dynamic_spectrum_access": dynamic_spectrum_access,
            "cooperative_perimeter_patrol": cooperative_perimeter_patrol,
        }
        if name not in factories:
            raise KeyError(f"Scenario '{name}' not found in autonomous systems domain.")
        return factories[name]()

