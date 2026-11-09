# Strategic Systems Engine (SSE)

[![Tests](https://img.shields.io/badge/tests-47%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()

The **Strategic Systems Engine (SSE)** is an advanced computational software engine for formal mathematical game theory, equilibrium solving, dynamic simulation, multi-agent reinforcement learning, and multi-domain strategic modeling.

---

## Capabilities Overview

- **Universal Strategic Models:** Finite normal-form, extensive-form trees, Bayesian games with incomplete information, cooperative characteristic-function (TU) games, repeated games with discounting, evolutionary population dynamics, stochastic Markov games, Stackelberg commitment models, and congestion/potential games.
- **10 Mathematical Solvers:**
  1. `pure_nash_enumeration`: Complete profile enumeration with exact unilateral deviation checks.
  2. `support_enumeration`: Indifference equation systems for 2-player mixed Nash equilibria.
  3. `dominant_strategy`: Detection of strictly/weakly dominant strategies and Iterated Elimination of Dominated Strategies (IEDS).
  4. `minimax`: Linear programming duality for 2-player zero-sum games with saddle-point detection.
  5. `backward_induction`: Subgame-perfect equilibrium (SPNE) on extensive-form game trees.
  6. `cooperative_solvers`: Axiomatic Shapley value computation and Core feasibility via LP.
  7. `correlated_equilibrium`: Utilitarian social-welfare maximizing correlated equilibrium via LP.
  8. `evolutionary`: Numerical integration of continuous replicator ODEs and Maynard Smith ESS testing.
  9. `stackelberg`: Bilevel optimization for leader commitment under follower best response.
  10. `regret_matching`: Hart & Mas-Colell no-regret learning converging to correlated equilibrium sets.
- **Simulation & Optimization:** Repeated interaction loops, Monte Carlo sweeps, parameter grids, HiGHS linear programming, SLSQP constrained nonlinear optimization, and discrete Pareto frontiers.
- **Multi-Agent Intelligence:** Q-learning, Fictitious Play, Regret Matching, Replicator agents, Tit-for-Tat, Grim Trigger, and round-robin tournament execution.
- **7 Multi-Domain Extensions:** Production scenario packs for Cybersecurity, Economics, Business Strategy, Logistics, Transportation, Social Systems, and Autonomous Robotics (21 total scenarios).
- **Developer Tooling:** Multi-command CLI, Python SDK (`SSEClient`), FastAPI REST microservice, and dynamic plugin loader.

---

## Quick Start

### Installation

```bash
# Clone the repository and enter the directory
cd strategic-systems-engine

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install all dependencies (development, scientific, API)
pip install -e ".[all]"
```

### Run Tests

```bash
pytest
```
*Expected: 47 passed in ~1.3 seconds.*

### CLI Usage

```bash
# Validate a game definition
sse validate examples/prisoners_dilemma.json

# Solve via exact Pure Nash enumeration
sse solve examples/prisoners_dilemma.json --solver pure_nash_enumeration

# Solve via Iterated Elimination of Dominated Strategies (IEDS)
sse solve examples/prisoners_dilemma.json --solver dominant_strategy

# Solve 2-player mixed Nash equilibrium via support enumeration
sse solve examples/matching_pennies.json --solver support_enumeration

# Solve zero-sum minimax value
sse solve examples/matching_pennies.json --solver minimax

# Run a repeated simulation
sse simulate examples/prisoners_dilemma.json --rounds 500 --seed 42

# List all registered solvers and domains
sse list-solvers
sse list-domains

# Export and inspect domain scenarios
sse scenario economics cournot_duopoly --output cournot.json
sse solve cournot.json --solver pure_nash_enumeration
```

### Python SDK

```python
from sse.sdk.client import SSEClient

client = SSEClient()
game = client.get_domain_scenario("social", "hawk_dove")
result = client.solve(game, solver="pure_nash_enumeration")
print("Pure Nash equilibria:", [eq.actions for eq in result.equilibria])
```

### REST API Service

Launch the FastAPI service:
```bash
uvicorn sse.api.app:app --host 0.0.0.0 --port 8000
```
Open interactive API docs at `http://localhost:8000/docs`.

---

## Documentation Index

- [Architecture Specification](docs/ARCHITECTURE.md)
- [Software Requirements Specification (SRS)](docs/SRS.md)
- [Mathematical Foundations](docs/MATHEMATICAL_FOUNDATIONS.md)
- [Data Model & JSON Schemas](docs/DATA_MODEL.md)
- [REST API Specification](docs/API_SPECIFICATION.md)
- [Plugin Architecture](docs/PLUGIN_ARCHITECTURE.md)
- [Testing & Verification Strategy](docs/TESTING_STRATEGY.md)
- [Security & Threat Model](docs/SECURITY_MODEL.md)
- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)
- [Installation Guide](INSTALLATION.md)
- [User Guide](USER_GUIDE.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [API Reference](API_REFERENCE.md)
- [Mathematical Reference](MATHEMATICAL_REFERENCE.md)
- [Domain Guide](DOMAIN_GUIDE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Release Notes](RELEASE_NOTES.md)
- [Final Verification Report](FINAL_VERIFICATION_REPORT.md)
