"""Strategic Systems Engine - Autonomous Sub-Agent Swarm Package.

Coordinates the specialized sub-agent division (Architect, Builder, Runtime,
Auditor, Red Team, Healer) to design, build, test, audit, and patch software
deliverables from scratch within sandboxed workspaces.
"""

from sse.swarm.contracts import (
    ExecutionResult,
    SwarmFileArtifact,
    SwarmWorkspaceState,
    TaskStatus,
    VulnerabilityFinding,
    VulnerabilitySeverity,
)
from sse.swarm.orchestrator import SwarmOrchestrationEngine
from sse.swarm.security_sandbox import (
    HardenedProcessExecutor,
    SandboxedWorkspaceGuard,
    get_sanitized_environment,
)

__all__ = [
    "ExecutionResult",
    "HardenedProcessExecutor",
    "SandboxedWorkspaceGuard",
    "SwarmFileArtifact",
    "SwarmOrchestrationEngine",
    "SwarmWorkspaceState",
    "TaskStatus",
    "VulnerabilityFinding",
    "VulnerabilitySeverity",
    "get_sanitized_environment",
]

