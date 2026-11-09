"""Social systems domain extension package."""

from sse.domains.social.scenarios import (
    condorcet_voting,
    hawk_dove,
    stag_hunt,
)
from sse.models import FiniteNormalFormGame


class SocialSystemsDomain:
    name = "social"
    description = "Strategic voting, Hawk-Dove conflict, and Stag Hunt social coordination dilemmas."

    def list_scenarios(self) -> list[str]:
        return [
            "hawk_dove",
            "stag_hunt",
            "condorcet_voting",
        ]

    def get_scenario(self, name: str) -> FiniteNormalFormGame:
        factories = {
            "hawk_dove": hawk_dove,
            "stag_hunt": stag_hunt,
            "condorcet_voting": condorcet_voting,
        }
        if name not in factories:
            raise KeyError(f"Scenario '{name}' not found in social systems domain.")
        return factories[name]()

