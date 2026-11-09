"""Strategic Systems Engine - Bayesian Game Models and Harsanyi Transformation.

Provides formal representations for games of incomplete information with private types,
prior beliefs, and the Harsanyi transformation into strategic-form games for
computing Bayesian Nash Equilibria (BNE).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import product
from typing import Any

from sse.models import FiniteNormalFormGame, GameValidationError, Player


@dataclass(frozen=True, slots=True)
class BayesianType:
    """A private information type for a player."""

    type_id: str
    name: str = ""
    description: str = ""


@dataclass(frozen=True, slots=True)
class BayesianNashEquilibrium:
    """Computed Bayesian Nash Equilibrium with type-contingent strategies."""

    player_type_strategies: dict[str, dict[str, dict[str, float]]]  # player_id -> type_id -> {action_id: prob}
    ex_ante_expected_payoffs: dict[str, float]
    expanded_equilibrium: Any


@dataclass
class BayesianGame:
    """Formal representation of a finite Bayesian game with incomplete information."""

    id: str
    name: str
    players: tuple[Player, ...]
    actions: tuple[tuple[str, ...], ...]
    types: tuple[tuple[str, ...], ...]  # types per player
    prior_distribution: dict[tuple[str, ...], float]  # joint type tuple -> probability
    payoff_functions: dict[str, Callable[[tuple[str, ...], tuple[str, ...]], float]] | None = None
    payoff_tables: dict[tuple[str, ...], tuple[tuple[float, ...], ...]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.players) != 2:
            raise GameValidationError("Currently, 2-player Bayesian games are supported for Harsanyi transformation.")
        if len(self.actions) != len(self.players) or len(self.types) != len(self.players):
            raise GameValidationError("Action and type dimensions must match player count.")

        # Verify prior probabilities sum to 1.0
        total_p = sum(self.prior_distribution.values())
        if abs(total_p - 1.0) > 1e-4:
            raise GameValidationError(f"Prior probability distribution must sum to 1.0, got {total_p:.6f}")

    def get_type_combinations(self) -> list[tuple[str, ...]]:
        """Returns all possible joint type profiles (theta_1, ..., theta_n)."""
        return list(product(*self.types))

    def to_harsanyi_normal_form(self) -> tuple[FiniteNormalFormGame, dict[int, list[dict[str, str]]]]:
        """Executes the Harsanyi transformation to produce an equivalent expanded strategic-form game.

        Returns:
            (expanded_game, strategy_mappings)
            where strategy_mappings[player_idx] maps strategy index to {type: action} dictionary.
        """
        # A strategy for player i is a mapping s_i: Theta_i -> A_i
        # Number of pure strategies is |A_i| ^ |Theta_i|
        expanded_actions: list[tuple[str, ...]] = []
        strategy_mappings: dict[int, list[dict[str, str]]] = {}

        for p_idx, player in enumerate(self.players):
            p_types = self.types[p_idx]
            p_acts = self.actions[p_idx]

            # Generate all functions from p_types to p_acts
            # Cartesian product of p_acts repeated |p_types| times
            type_action_tuples = list(product(p_acts, repeat=len(p_types)))
            p_strats: list[str] = []
            p_mappings: list[dict[str, str]] = []

            for t_tuple in type_action_tuples:
                mapping = dict(zip(p_types, t_tuple, strict=False))
                name_parts = [f"{t}:{a}" for t, a in mapping.items()]
                p_strats.append("|".join(name_parts))
                p_mappings.append(mapping)

            expanded_actions.append(tuple(p_strats))
            strategy_mappings[p_idx] = p_mappings

        # Now compute the ex-ante expected payoff for each expanded strategy profile
        m = len(expanded_actions[0])
        n = len(expanded_actions[1])
        joint_profiles = list(product(range(m), range(n)))
        payoffs_list: list[tuple[float, float]] = []

        for s1_idx, s2_idx in joint_profiles:
            map1 = strategy_mappings[0][s1_idx]
            map2 = strategy_mappings[1][s2_idx]

            expected_u1 = 0.0
            expected_u2 = 0.0

            for (theta1, theta2), prob in self.prior_distribution.items():
                if prob <= 0:
                    continue
                # Concrete actions chosen by each player under this type realization
                a1 = map1[theta1]
                a2 = map2[theta2]
                actions_chosen = (a1, a2)
                types_realized = (theta1, theta2)

                if self.payoff_functions:
                    u1 = self.payoff_functions[self.players[0].id](actions_chosen, types_realized)
                    u2 = self.payoff_functions[self.players[1].id](actions_chosen, types_realized)
                elif self.payoff_tables:
                    # Look up payoff in table for this type realization
                    table = self.payoff_tables[types_realized]
                    a1_idx = self.actions[0].index(a1)
                    a2_idx = self.actions[1].index(a2)
                    profile_flat_idx = a1_idx * len(self.actions[1]) + a2_idx
                    u1, u2 = table[profile_flat_idx]
                else:
                    raise ValueError("BayesianGame requires either payoff_functions or payoff_tables.")

                expected_u1 += prob * u1
                expected_u2 += prob * u2

            payoffs_list.append((expected_u1, expected_u2))

        expanded_game = FiniteNormalFormGame(
            id=f"{self.id}_harsanyi_expanded",
            name=f"Harsanyi Expanded: {self.name}",
            players=self.players,
            actions=tuple(expanded_actions),
            payoffs=tuple(payoffs_list),
        )

        return expanded_game, strategy_mappings

    def solve_bayesian_nash(self) -> list[BayesianNashEquilibrium]:
        """Computes all Bayesian Nash Equilibria (BNE) using Exact Support Enumeration."""
        from sse.strategic.solvers.exact_solvers import ExactSupportEnumerationSolver

        expanded_game, strategy_mappings = self.to_harsanyi_normal_form()
        solver = ExactSupportEnumerationSolver()
        res = solver.solve(expanded_game)

        bne_list: list[BayesianNashEquilibrium] = []

        for eq in res.equilibria:
            # Map expanded mixed strategies back to type-contingent distributions
            player_type_strategies: dict[str, dict[str, dict[str, float]]] = {}

            # Player 1
            p1_dict: dict[str, dict[str, float]] = {t: {a: 0.0 for a in self.actions[0]} for t in self.types[0]}
            for s1_idx, prob in enumerate(eq.strategy_1):
                if prob > 1e-8:
                    mapping = strategy_mappings[0][s1_idx]
                    for t, a in mapping.items():
                        p1_dict[t][a] += float(prob)
            player_type_strategies[self.players[0].id] = p1_dict

            # Player 2
            p2_dict: dict[str, dict[str, float]] = {t: {a: 0.0 for a in self.actions[1]} for t in self.types[1]}
            for s2_idx, prob in enumerate(eq.strategy_2):
                if prob > 1e-8:
                    mapping = strategy_mappings[1][s2_idx]
                    for t, a in mapping.items():
                        p2_dict[t][a] += float(prob)
            player_type_strategies[self.players[1].id] = p2_dict

            ex_ante = {
                self.players[0].id: eq.payoff_1,
                self.players[1].id: eq.payoff_2,
            }

            bne_list.append(
                BayesianNashEquilibrium(
                    player_type_strategies=player_type_strategies,
                    ex_ante_expected_payoffs=ex_ante,
                    expanded_equilibrium=eq,
                )
            )

        return bne_list
