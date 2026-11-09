"""Command-line interface for SSE."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sse import __version__
from sse.agents.strategies import RandomAgent
from sse.core.actions import DiscreteActionSpace
from sse.domains import DomainRegistry
from sse.io import dump_json, load_game
from sse.simulation.engine import SimulationConfig, SimulationEngine
from sse.solvers.registry import registry as solver_registry


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sse",
        description="Strategic Systems Engine — formal strategic model analysis.",
    )
    parser.add_argument("--version", action="version", version=f"SSE {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate
    validate_p = subparsers.add_parser("validate", help="Validate a JSON game definition.")
    validate_p.add_argument("game", help="Path to a JSON game definition.")

    # solve
    solve_p = subparsers.add_parser("solve", help="Solve a game using a designated solver.")
    solve_p.add_argument("game", help="Path to a JSON game definition.")
    solve_p.add_argument("--solver", default="pure_nash_enumeration", help="Solver name.")
    solve_p.add_argument("--tolerance", type=float, default=0.0, help="Numerical tolerance.")

    # list-solvers
    subparsers.add_parser("list-solvers", help="List all registered mathematical solvers.")

    # list-domains
    subparsers.add_parser("list-domains", help="List all registered application domains.")

    # scenario
    scenario_p = subparsers.add_parser("scenario", help="Export a domain scenario to JSON.")
    scenario_p.add_argument("domain", help="Domain name (e.g. cybersecurity, economics).")
    scenario_p.add_argument("scenario_name", help="Scenario factory name.")
    scenario_p.add_argument("--output", "-o", default=None, help="Optional output JSON path.")

    # simulate
    sim_p = subparsers.add_parser("simulate", help="Run repeated simulation on a game.")
    sim_p.add_argument("game", help="Path to a JSON game definition.")
    sim_p.add_argument("--rounds", type=int, default=100, help="Number of repeated rounds.")
    sim_p.add_argument("--seed", type=int, default=42, help="Random seed.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "list-solvers":
            print(json.dumps({"solvers": solver_registry.list_solvers()}, indent=2))
            return 0

        if args.command == "list-domains":
            domains_info = {
                d: DomainRegistry.get(d).list_scenarios()
                for d in DomainRegistry.list_domains()
            }
            print(json.dumps({"domains": domains_info}, indent=2))
            return 0

        if args.command == "scenario":
            dom = DomainRegistry.get(args.domain)
            game = dom.get_scenario(args.scenario_name)
            game_dict = game.to_dict()
            if args.output:
                out_path = Path(args.output)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(dump_json(game_dict), encoding="utf-8")
                print(f"Scenario exported to {args.output}")
            else:
                print(dump_json(game_dict))
            return 0

        game = load_game(args.game)

        if args.command == "validate":
            print(json.dumps({
                "status": "valid",
                "game_id": game.id,
                "players": len(game.players),
                "profiles": game.profile_count,
            }, indent=2))
            return 0

        if args.command == "solve":
            solver = solver_registry.get(args.solver)
            result = solver.solve(game, tolerance=args.tolerance)

            output: dict[str, Any] = {
                "status": result.status,
                "solution_count": result.solution_count,
                "solver": asdict(result.metadata) if result.metadata else None,
                "diagnostics": result.diagnostics,
            }

            # Add solution-specific fields
            if hasattr(result, "equilibria"):
                output["equilibria"] = [
                    {
                        "action_indices": list(getattr(eq, "action_indices", ())),
                        "actions": list(getattr(eq, "actions", ())),
                        "payoffs": list(getattr(eq, "payoffs", getattr(eq, "expected_payoffs", ()))),
                    }
                    for eq in getattr(result, "equilibria", ())
                ]
            if hasattr(result, "strictly_dominant"):
                output["strictly_dominant"] = result.strictly_dominant
            if hasattr(result, "game_value"):
                output["game_value"] = result.game_value
            if hasattr(result, "social_welfare"):
                output["social_welfare"] = result.social_welfare

            print(json.dumps(output, indent=2))
            return 0

        if args.command == "simulate":
            engine = SimulationEngine()
            config = SimulationConfig(seed=args.seed, max_steps=args.rounds)
            # Create random agents as baseline players
            strategies = {
                p.id: RandomAgent(p.id, DiscreteActionSpace(game.actions[i]))
                for i, p in enumerate(game.players)
            }
            sim_res = engine.run_repeated(game, strategies, num_rounds=args.rounds, config=config)
            print(json.dumps({
                "status": "completed",
                "rounds": len(sim_res.steps),
                "total_payoffs": sim_res.total_payoffs,
                "duration_seconds": sim_res.duration_seconds,
            }, indent=2))
            return 0

        return 0
    except Exception as exc:  # CLI boundary
        print(f"SSE error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
