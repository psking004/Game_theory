"""FastAPI route definitions for the SSE REST API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sse.domains import DomainRegistry
from sse.models import FiniteNormalFormGame, GameValidationError
from sse.solvers.registry import registry as solver_registry

api_router = APIRouter()


class GamePayload(BaseModel):
    id: str
    name: str
    players: list[str]
    actions: dict[str, list[str]]
    payoffs: list[list[float]]


class ValidationResponse(BaseModel):
    status: str
    game_id: str
    players: int
    profiles: int


class SolveRequest(BaseModel):
    game: GamePayload
    solver: str = "pure_nash_enumeration"
    tolerance: float = 0.0


class SolverResultResponse(BaseModel):
    status: str
    solver: str
    solution_count: int
    diagnostics: dict[str, Any]
    details: dict[str, Any]


@api_router.get("/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "Strategic Systems Engine REST API",
        "version": "0.1.0",
    }


@api_router.post("/models/validate", response_model=ValidationResponse)
def validate_model(payload: GamePayload) -> ValidationResponse:
    try:
        game = FiniteNormalFormGame.from_dict(payload.model_dump())
        return ValidationResponse(
            status="valid",
            game_id=game.id,
            players=len(game.players),
            profiles=game.profile_count,
        )
    except GameValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api_router.get("/solvers/list")
def list_solvers() -> dict[str, list[str]]:
    return {"solvers": solver_registry.list_solvers()}


@api_router.post("/solvers/solve", response_model=SolverResultResponse)
def solve_game(request: SolveRequest) -> SolverResultResponse:
    try:
        game = FiniteNormalFormGame.from_dict(request.game.model_dump())
        solver = solver_registry.get(request.solver)
        result = solver.solve(game, tolerance=request.tolerance)

        # Convert result attributes to dictionary
        details: dict[str, Any] = {}
        for attr in dir(result):
            if not attr.startswith("_") and attr not in {"status", "solution_count", "diagnostics", "metadata"}:
                val = getattr(result, attr)
                if not callable(val):
                    details[attr] = str(val) if not isinstance(val, (int, float, bool, list, dict)) else val

        return SolverResultResponse(
            status=result.status,
            solver=result.metadata.solver if result.metadata else request.solver,
            solution_count=result.solution_count,
            diagnostics=result.diagnostics,
            details=details,
        )
    except GameValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid game definition: {exc}") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Solver not found: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Solver failure: {exc}") from exc


@api_router.get("/domains/list")
def list_domains() -> dict[str, list[str]]:
    return {"domains": DomainRegistry.list_domains()}


@api_router.get("/domains/{domain_name}/scenarios")
def list_domain_scenarios(domain_name: str) -> dict[str, Any]:
    try:
        domain = DomainRegistry.get(domain_name)
        return {
            "domain": domain_name,
            "description": domain.description,
            "scenarios": domain.list_scenarios(),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_router.get("/domains/{domain_name}/scenarios/{scenario_name}")
def get_domain_scenario(domain_name: str, scenario_name: str) -> dict[str, Any]:
    try:
        domain = DomainRegistry.get(domain_name)
        game = domain.get_scenario(scenario_name)
        return game.to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
