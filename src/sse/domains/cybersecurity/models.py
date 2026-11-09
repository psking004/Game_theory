"""Cybersecurity domain models: attacker-defender, security investment, and intrusion response."""

from __future__ import annotations

from collections.abc import Sequence

from sse.models import FiniteNormalFormGame


class AttackerDefenderGame:
    """Security resource allocation game across network assets."""

    def __init__(
        self,
        targets: Sequence[str],
        target_values: Sequence[float],
        defense_cost: float = 1.0,
    ) -> None:
        if len(targets) != len(target_values):
            raise ValueError("Target names and target values must have equal length.")
        self.targets = list(targets)
        self.target_values = list(target_values)
        self.defense_cost = defense_cost

    def to_game(self) -> FiniteNormalFormGame:
        # Attacker chooses target to exploit; Defender chooses target to harden
        attacker_actions = [f"Attack_{t}" for t in self.targets]
        defender_actions = [f"Defend_{t}" for t in self.targets]

        payoffs: list[list[float]] = []
        for a_idx, t_att in enumerate(self.targets):
            v_att = self.target_values[a_idx]
            for d_idx, t_def in enumerate(self.targets):
                if a_idx == d_idx:
                    # Attack caught / blocked
                    u_att = -1.0
                    u_def = 1.0 - self.defense_cost
                else:
                    # Target breached
                    u_att = v_att
                    u_def = -v_att - self.defense_cost
                payoffs.append([u_att, u_def])

        return FiniteNormalFormGame.from_dict({
            "id": "attacker-defender-target-allocation",
            "name": "Attacker-Defender Security Allocation",
            "players": ["Attacker", "Defender"],
            "actions": {
                "Attacker": attacker_actions,
                "Defender": defender_actions,
            },
            "payoffs": payoffs,
        })


class SecurityInvestmentGame:
    """Gordon-Loeb style security investment competition between interdependent organizations."""

    def __init__(
        self,
        firms: Sequence[str] = ("Firm_A", "Firm_B"),
        asset_value: float = 100.0,
        breach_cost: float = 80.0,
    ) -> None:
        self.firms = list(firms)
        self.asset_value = asset_value
        self.breach_cost = breach_cost

    def to_game(self) -> FiniteNormalFormGame:
        levels = ["Low_Investment", "Medium_Investment", "High_Investment"]
        costs = {"Low_Investment": 5.0, "Medium_Investment": 15.0, "High_Investment": 30.0}
        risk = {"Low_Investment": 0.5, "Medium_Investment": 0.2, "High_Investment": 0.05}

        payoffs: list[list[float]] = []
        for l1 in levels:
            c1, r1 = costs[l1], risk[l1]
            for l2 in levels:
                c2, r2 = costs[l2], risk[l2]
                # Spillover risk
                p_breach1 = r1 + 0.2 * r2
                p_breach2 = r2 + 0.2 * r1

                u1 = self.asset_value - c1 - p_breach1 * self.breach_cost
                u2 = self.asset_value - c2 - p_breach2 * self.breach_cost
                payoffs.append([round(u1, 2), round(u2, 2)])

        return FiniteNormalFormGame.from_dict({
            "id": "interdependent-security-investment",
            "name": "Interdependent Security Investment Game",
            "players": self.firms,
            "actions": {
                self.firms[0]: levels,
                self.firms[1]: levels,
            },
            "payoffs": payoffs,
        })
