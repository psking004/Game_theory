"""Command-line interface for SSE."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from sse import __version__
from sse.agents.policies import (
    AdaptiveReciprocalDefender,
    GenerousTitForTatPolicy,
    GreedyMyopicPolicy,
    TitForTatPolicy,
    ZeroDeterminantPolicy,
)
from sse.agents.strategies import RandomAgent
from sse.contracts.decision import DecisionRequest
from sse.core.actions import DiscreteActionSpace
from sse.domains import DomainRegistry
from sse.io import dump_json, load_game
from sse.orchestrator.decision_engine import StrategicDecisionEngine
from sse.simulation.engine import SimulationConfig, SimulationEngine
from sse.simulation.runtime import RepeatedGameRuntime
from sse.solvers.registry import registry as solver_registry
from sse.strategic.solvers.exact_solvers import (
    BilevelStackelbergSolver,
    ExactSupportEnumerationSolver,
    LemkeHowsonSolver,
)
from sse.verification.benchmarks import (
    CanonicalBenchmarkSuite,
    MathematicalInvariantEngine,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sse",
        description="Strategic Systems Engine — formal strategic model analysis & decision intelligence.",
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

    # benchmarks
    bm_p = subparsers.add_parser("benchmarks", help="List or verify canonical game benchmarks.")
    bm_p.add_argument("--verify", default=None, help="Benchmark game to verify (e.g. prisoners_dilemma, rps, all).")

    # exact-solve
    exact_p = subparsers.add_parser("exact-solve", help="Solve via exact Support Enumeration, Lemke-Howson, or Stackelberg.")
    exact_p.add_argument("game", help="Path to JSON game or canonical benchmark name.")
    exact_p.add_argument("--method", default="support_enumeration", choices=["support_enumeration", "lemke_howson", "stackelberg_sse", "stackelberg_wse"])

    # repeated-sim
    r_sim_p = subparsers.add_parser("repeated-sim", help="Run repeated policy tournament simulation.")
    r_sim_p.add_argument("--p1", default="tft", choices=["tft", "gtft", "greedy", "zd", "defender"])
    r_sim_p.add_argument("--p2", default="greedy", choices=["tft", "gtft", "greedy", "zd", "defender"])
    r_sim_p.add_argument("--rounds", type=int, default=1000)
    r_sim_p.add_argument("--seeds", type=int, default=50)
    r_sim_p.add_argument("--delta", type=float, default=0.95)
    r_sim_p.add_argument("--noise", type=float, default=0.05)

    # decide
    decide_p = subparsers.add_parser("decide", help="Formulate autonomous strategic decision from context.")
    decide_p.add_argument("--context", required=True, help="Description of the strategic situation.")
    decide_p.add_argument("--goal", required=True, help="Strategic objective.")
    decide_p.add_argument("--confidence", type=float, default=0.60, help="Minimum confidence threshold.")

    return parser


def _get_benchmark_game(name: str):
    suite_map = {
        "prisoners_dilemma": CanonicalBenchmarkSuite.prisoners_dilemma,
        "matching_pennies": CanonicalBenchmarkSuite.matching_pennies,
        "rock_paper_scissors": CanonicalBenchmarkSuite.rock_paper_scissors,
        "rps": CanonicalBenchmarkSuite.rock_paper_scissors,
        "battle_of_the_sexes": CanonicalBenchmarkSuite.battle_of_the_sexes,
        "stag_hunt": CanonicalBenchmarkSuite.stag_hunt,
        "hawk_dove": CanonicalBenchmarkSuite.hawk_dove,
        "cournot_duopoly": CanonicalBenchmarkSuite.cournot_duopoly,
        "bertrand_competition": CanonicalBenchmarkSuite.bertrand_competition,
        "stackelberg_market": CanonicalBenchmarkSuite.stackelberg_market,
        "public_goods": CanonicalBenchmarkSuite.public_goods_dilemma,
    }
    factory = suite_map.get(name.lower())
    if not factory:
        raise ValueError(f"Unknown canonical benchmark: '{name}'. Available: {list(suite_map.keys())}")
    return factory()


def _get_policy(name: str):
    name = name.lower()
    if name == "tft":
        return TitForTatPolicy("TitForTat")
    if name == "gtft":
        return GenerousTitForTatPolicy("GenerousTitForTat")
    if name == "greedy":
        return GreedyMyopicPolicy("GreedyMyopic")
    if name == "zd":
        return ZeroDeterminantPolicy("ZeroDeterminant")
    if name == "defender":
        return AdaptiveReciprocalDefender("AdaptiveDefender")
    raise ValueError(f"Unknown policy: {name}")


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

        if args.command == "benchmarks":
            available = [
                "prisoners_dilemma", "matching_pennies", "rock_paper_scissors",
                "battle_of_the_sexes", "stag_hunt", "hawk_dove",
                "cournot_duopoly", "bertrand_competition", "stackelberg_market",
                "public_goods",
            ]
            if not args.verify:
                print(json.dumps({"canonical_benchmarks": available}, indent=2))
                return 0

            to_verify = available if args.verify == "all" else [args.verify]
            results = {}
            solver = ExactSupportEnumerationSolver()

            for b_name in to_verify:
                game = _get_benchmark_game(b_name)
                res = solver.solve(game)
                first_eq = res.equilibria[0] if res.equilibria else None
                valid_eps = False
                dev = 0.0
                if first_eq:
                    valid_eps, dev = MathematicalInvariantEngine.verify_epsilon_nash(game, first_eq)
                results[b_name] = {
                    "equilibria_count": len(res.equilibria),
                    "epsilon_nash_satisfied": valid_eps,
                    "max_deviation": dev,
                }
            print(json.dumps({"benchmark_verification": results}, indent=2))
            return 0

        if args.command == "exact-solve":
            # Load from file or canonical benchmark
            if Path(args.game).exists():
                game = load_game(args.game)
            else:
                game = _get_benchmark_game(args.game)

            if args.method == "support_enumeration":
                res = ExactSupportEnumerationSolver().solve(game)
                eq_data = []
                for eq in res.equilibria:
                    eq_data.append({
                        "is_pure": eq.is_pure,
                        "strategy_1": list(np.round(eq.strategy_1, 4)),
                        "strategy_2": list(np.round(eq.strategy_2, 4)),
                        "payoff_1": round(eq.payoff_1, 4),
                        "payoff_2": round(eq.payoff_2, 4),
                    })
                print(json.dumps({
                    "game": game.name,
                    "method": "exact_support_enumeration",
                    "equilibria_count": len(eq_data),
                    "equilibria": eq_data,
                }, indent=2))
                return 0

            if args.method == "lemke_howson":
                res = LemkeHowsonSolver().solve(game)
                eq = res.equilibrium
                print(json.dumps({
                    "game": game.name,
                    "method": "lemke_howson_lcp",
                    "pivots": res.pivots_count,
                    "strategy_1": list(np.round(eq.strategy_1, 4)),
                    "strategy_2": list(np.round(eq.strategy_2, 4)),
                    "payoff_1": round(eq.payoff_1, 4),
                    "payoff_2": round(eq.payoff_2, 4),
                }, indent=2))
                return 0

            if args.method in ("stackelberg_sse", "stackelberg_wse"):
                mode = "SSE" if args.method == "stackelberg_sse" else "WSE"
                res = BilevelStackelbergSolver().solve_pure(game, mode=mode)
                print(json.dumps({
                    "game": game.name,
                    "method": f"stackelberg_{mode.lower()}",
                    "leader_action_idx": int(np.argmax(res.leader_strategy)),
                    "follower_action_idx": res.follower_action_idx,
                    "leader_payoff": round(res.leader_payoff, 4),
                    "follower_payoff": round(res.follower_payoff, 4),
                }, indent=2))
                return 0

        if args.command == "repeated-sim":
            # Prisoner's Dilemma standard payoff tensor
            pd_matrix = np.array([
                [[3.0, 3.0], [0.0, 5.0]],
                [[5.0, 0.0], [1.0, 1.0]],
            ])
            runtime = RepeatedGameRuntime(
                payoff_matrix=pd_matrix,
                rounds_t=args.rounds,
                discount_factor_delta=args.delta,
                trembling_noise=args.noise,
            )
            p1 = _get_policy(args.p1)
            p2 = _get_policy(args.p2)

            res = runtime.run_monte_carlo(p1, p2, n_seeds=args.seeds)
            print(json.dumps({
                "policy_1": res.policy_name_p1,
                "policy_2": res.policy_name_p2,
                "rounds": args.rounds,
                "trials": res.trials_count,
                "p1_mean_discounted_payoff": res.mean_discounted_payoff_p1,
                "p1_payoff_std": res.std_discounted_payoff_p1,
                "p2_mean_discounted_payoff": res.mean_discounted_payoff_p2,
                "p2_payoff_std": res.std_discounted_payoff_p2,
                "p1_cooperation_rate": res.mean_cooperation_rate_p1,
                "p2_cooperation_rate": res.mean_cooperation_rate_p2,
                "exploitability": res.exploitability,
            }, indent=2))
            return 0

        if args.command == "decide":
            engine = StrategicDecisionEngine()
            req = DecisionRequest(
                context_description=args.context,
                goal=args.goal,
                required_confidence=args.confidence,
            )
            resp = engine.formulate_decision(req)
            rec = resp.recommendation
            output = {
                "decision_id": resp.decision_id,
                "problem_type": resp.problem_type.value,
                "state": resp.state.value,
                "recommendation": {
                    "action": rec.action_name if rec else None,
                    "action_id": rec.selected_action_id if rec else None,
                    "justification": rec.justification if rec else None,
                } if rec else None,
                "rationale": resp.rationale,
                "confidence_score": resp.uncertainty.confidence_score,
                "value_at_risk_95": resp.uncertainty.value_at_risk_95,
                "is_executable": resp.is_executable,
            }
            print(json.dumps(output, indent=2))
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
