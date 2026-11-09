"""Strategic Systems Engine - AIVA Strategic Intelligence Client.

Unified SDK interface for AIVA, exposing strategic reasoning, scenario prediction,
decision formulation, bounded authorization, and controlled execution.
"""

from __future__ import annotations

from typing import Any

from sse.contracts.action import ActionDefinition, ActionResult
from sse.contracts.authorization import (
    AuthorizationRequest,
    AutonomyLevel,
    PermissionScope,
)
from sse.contracts.decision import DecisionRequest, DecisionResponse
from sse.contracts.world_state import WorldStateSnapshot
from sse.execution.dispatcher import ActionDispatcher
from sse.governance.authorization import AuthorizationGate
from sse.orchestrator.decision_engine import StrategicDecisionEngine
from sse.strategic.prediction.scenario_generator import ScenarioGenerator
from sse.world_model.state_manager import WorldStateManager


class StrategicIntelligenceClient:
    """Primary AIVA interface to the Strategic Systems Engine."""

    def __init__(
        self,
        decision_engine: StrategicDecisionEngine | None = None,
        authorization_gate: AuthorizationGate | None = None,
        action_dispatcher: ActionDispatcher | None = None,
        state_manager: WorldStateManager | None = None,
    ) -> None:
        self.state_manager = state_manager or WorldStateManager()
        self.decision_engine = decision_engine or StrategicDecisionEngine(state_manager=self.state_manager)
        self.authorization_gate = authorization_gate or AuthorizationGate(state_manager=self.state_manager)
        self.dispatcher = action_dispatcher or ActionDispatcher(authorization_gate=self.authorization_gate)
        self.scenario_generator = ScenarioGenerator()
        self._decisions_cache: dict[str, DecisionResponse] = {}

    def analyse(
        self,
        context: str,
        goal: str,
        candidate_actions: list[dict[str, Any]] | None = None,
        required_confidence: float = 0.60,
        max_risk_tolerance: float = 0.40,
    ) -> DecisionResponse:
        """Analyzes a strategic situation and formulates a complete DecisionResponse."""
        request = DecisionRequest(
            context_description=context,
            goal=goal,
            candidate_actions=candidate_actions or [],
            required_confidence=required_confidence,
            max_risk_tolerance=max_risk_tolerance,
        )
        response = self.decision_engine.formulate_decision(request)
        self._decisions_cache[response.decision_id] = response
        return response

    def predict(
        self,
        action: ActionDefinition,
        snapshot: WorldStateSnapshot | None = None,
    ) -> dict[str, float]:
        """Projects outcome distributions and downside risk metrics across scenarios."""
        snap = snapshot or self.state_manager.capture_snapshot()
        scenarios = self.scenario_generator.generate_scenarios(snap)
        base_payoff = float(action.parameters.get("expected_return", 100.0))
        return self.decision_engine.evaluator.forecaster.evaluate_action(
            action=action,
            base_payoff=base_payoff,
            scenarios=scenarios,
        )

    def request_authorization(
        self,
        decision_id: str,
        action: ActionDefinition,
        requester_id: str = "aiva_orchestrator",
        autonomy_level: AutonomyLevel = AutonomyLevel.BOUNDED_AUTONOMOUS,
        scope: PermissionScope = PermissionScope.EXECUTION_LOW_RISK,
        timeout_seconds: float = 300.0,
    ) -> dict[str, Any]:
        """Requests an execution authorization grant from the AuthorizationGate."""
        decision = self._decisions_cache.get(decision_id)
        if not decision:
            return {"approved": False, "reason": "Decision ID not found"}

        snapshot = self.state_manager.capture_snapshot()
        auth_req = AuthorizationRequest(
            decision_id=decision_id,
            action_id=action.action_id,
            requester_id=requester_id,
            requested_autonomy=autonomy_level,
            requested_scope=scope,
            estimated_cost=action.estimated_cost,
            is_reversible=action.reversibility.value == "reversible",
            timeout_seconds=timeout_seconds,
        )

        auth_eval = self.authorization_gate.evaluate_authorization(
            request=auth_req,
            action=action,
            verification=decision.verification,
            baseline_snapshot=snapshot,
        )

        if auth_eval["approved"] and auth_eval["grant"]:
            decision.authorization.is_authorized = True
            decision.authorization.grant_token = auth_eval["grant"].grant_token
            decision.authorization.autonomy_level = int(autonomy_level)
            decision.state = decision.state.AUTHORIZED

        return auth_eval

    def execute(
        self,
        action: ActionDefinition,
        grant_token: str,
        parameters: dict[str, Any] | None = None,
    ) -> ActionResult:
        """Executes an authorized action through the ActionDispatcher."""
        return self.dispatcher.dispatch_action(
            action=action,
            grant_token=grant_token,
            parameters=parameters,
        )

    def rollback(self, reason: str = "Manual operator rollback") -> dict[str, Any]:
        """Triggers compensation rollback for dispatched actions."""
        return self.dispatcher.rollback_coordinator.trigger_rollback(reason=reason)

    def explain(self, decision_id: str) -> str:
        """Generates a human- and agent-readable markdown explanation of a decision."""
        decision = self._decisions_cache.get(decision_id)
        if not decision:
            return f"Decision '{decision_id}' not found."

        rec = decision.recommendation
        lines = [
            f"# Strategic Decision Explanation: {decision.decision_id}",
            f"**Problem Classification:** `{decision.problem_type.value}`",
            f"**State:** `{decision.state.value}`",
            f"**Rationale:** {decision.rationale}",
            "",
            "## Recommendation",
        ]
        if rec:
            lines.extend([
                f"- **Action:** {rec.action_name} (`{rec.selected_action_id}`)",
                f"- **Justification:** {rec.justification}",
                f"- **Reversibility:** {rec.reversibility}",
                "- **Execution Steps:**",
            ])
            for step in rec.execution_steps:
                lines.append(f"  1. {step}")
        else:
            lines.append("*(No action recommended — Engine abstained)*")

        lines.extend([
            "",
            "## Uncertainty & Risk Profile",
            f"- **Confidence Score:** {decision.uncertainty.confidence_score:.1%}",
            f"- **Value-at-Risk (95% VaR):** {decision.uncertainty.value_at_risk_95:.2f}",
            f"- **Epistemic Uncertainty:** {decision.uncertainty.epistemic_uncertainty:.2f}",
            f"- **Aleatoric Uncertainty:** {decision.uncertainty.aleatoric_uncertainty:.2f}",
            "",
            "## Evaluated Alternatives",
        ])
        for alt in decision.alternatives:
            lines.append(
                f"- **{alt.name}**: Expected Payoff = {alt.expected_payoff:.2f}, Risk = {alt.risk_score:.3f}"
            )
            for p in alt.pros:
                lines.append(f"  - [Pro] {p}")
            for c in alt.cons:
                lines.append(f"  - [Con] {c}")

        lines.extend([
            "",
            "## Governance & Verification",
            f"- **Formally Verified:** {decision.verification.is_valid}",
            f"- **Authorized for Execution:** {decision.authorization.is_authorized}",
        ])

        return "\n".join(lines)
