"""Validated model contracts for finite normal-form games."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import product
from math import isfinite


class GameValidationError(ValueError):
    """Raised when a game definition violates its mathematical contract."""


@dataclass(frozen=True, slots=True)
class Player:
    """A strategic participant with a stable identifier."""

    id: str
    name: str

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise GameValidationError("Player id must not be empty.")
        if not self.name.strip():
            raise GameValidationError("Player name must not be empty.")


@dataclass(frozen=True, slots=True)
class FiniteNormalFormGame:
    """A finite normal-form game with a payoff tensor.

    `payoffs[profile][player_index]` is the utility received by that player.
    Profiles follow the Cartesian-product order of each player's action list.
    """

    id: str
    name: str
    players: tuple[Player, ...]
    actions: tuple[tuple[str, ...], ...]
    payoffs: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise GameValidationError("Game id must not be empty.")
        if not self.name.strip():
            raise GameValidationError("Game name must not be empty.")
        if len(self.players) < 2:
            raise GameValidationError("A normal-form game requires at least two players.")
        player_ids = [p.id for p in self.players]
        if len(set(player_ids)) != len(player_ids):
            raise GameValidationError("Player ids must be unique.")
        if len(self.actions) != len(self.players):
            raise GameValidationError("Each player must have exactly one action set.")
        for index, action_set in enumerate(self.actions):
            if not action_set:
                raise GameValidationError(f"Player {index} must have at least one action.")
            if any(not action.strip() for action in action_set):
                raise GameValidationError("Action names must not be empty.")
            if len(set(action_set)) != len(action_set):
                raise GameValidationError(f"Actions for player {index} must be unique.")

        expected_profiles = 1
        for action_set in self.actions:
            expected_profiles *= len(action_set)
        if len(self.payoffs) != expected_profiles:
            raise GameValidationError(
                f"Expected {expected_profiles} payoff profiles; received {len(self.payoffs)}."
            )
        for profile_index, payoff_vector in enumerate(self.payoffs):
            if len(payoff_vector) != len(self.players):
                raise GameValidationError(
                    f"Payoff profile {profile_index} must contain one value per player."
                )
            if any(not isfinite(value) for value in payoff_vector):
                raise GameValidationError("All payoffs must be finite real numbers.")

    @property
    def action_counts(self) -> tuple[int, ...]:
        return tuple(len(action_set) for action_set in self.actions)

    @property
    def profile_count(self) -> int:
        count = 1
        for size in self.action_counts:
            count *= size
        return count

    def profiles(self) -> Iterator[tuple[int, ...]]:
        """Yield action-index profiles in canonical Cartesian-product order."""
        return product(*(range(size) for size in self.action_counts))

    def profile_index(self, profile: Sequence[int]) -> int:
        """Map an action-index profile to its flattened payoff row."""
        if len(profile) != len(self.players):
            raise GameValidationError("Profile length must equal player count.")
        index = 0
        for action_index, action_count in zip(profile, self.action_counts, strict=True):
            if not isinstance(action_index, int) or isinstance(action_index, bool):
                raise GameValidationError("Action indices must be integers.")
            if action_index < 0 or action_index >= action_count:
                raise GameValidationError("Action index is outside the player's action set.")
            index = index * action_count + action_index
        return index

    def payoff(self, profile: Sequence[int]) -> tuple[float, ...]:
        return self.payoffs[self.profile_index(profile)]

    def action_names(self, profile: Sequence[int]) -> tuple[str, ...]:
        if len(profile) != len(self.players):
            raise GameValidationError("Profile length must equal player count.")
        return tuple(
            self.actions[player_index][action_index]
            for player_index, action_index in enumerate(profile)
        )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> FiniteNormalFormGame:
        """Build a game from the documented JSON-compatible schema."""
        try:
            raw_players = data["players"]
            raw_actions = data["actions"]
            raw_payoffs = data["payoffs"]
            if not isinstance(raw_players, list) or not isinstance(raw_actions, dict):
                raise TypeError("players must be a list and actions must be an object")
            players = tuple(
                Player(id=str(item), name=str(item))
                for item in raw_players
            )
            actions = tuple(
                tuple(str(action) for action in raw_actions[player.id])
                for player in players
            )
            payoffs = tuple(
                tuple(float(value) for value in vector)
                for vector in raw_payoffs
            )
            return cls(
                id=str(data["id"]),
                name=str(data["name"]),
                players=players,
                actions=actions,
                payoffs=payoffs,
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, GameValidationError):
                raise
            raise GameValidationError(f"Invalid game document: {exc}") from exc

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "players": [player.id for player in self.players],
            "actions": {
                player.id: list(self.actions[index])
                for index, player in enumerate(self.players)
            },
            "payoffs": [list(vector) for vector in self.payoffs],
        }
