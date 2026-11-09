# Strategic Systems Engine (SSE)

[![Tests](https://img.shields.io/badge/tests-151%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()
[![Memory Limit](https://img.shields.io/badge/RAM-%3C80MB-success.svg)]()
[![Sovereign Mesh](https://img.shields.io/badge/Tri--Node-Zero--SPOF-blueviolet.svg)]()

The **Strategic Systems Engine (SSE)** is an advanced computational software engine for formal mathematical game theory, equilibrium solving, dynamic simulation, multi-agent reinforcement learning, and multi-domain strategic modeling.

---

## Capabilities Overview

- **Universal Strategic Models:** Finite normal-form, extensive-form trees, Bayesian games with incomplete information, cooperative characteristic-function (TU) games, repeated games with discounting, evolutionary population dynamics, stochastic Markov games, Stackelberg commitment models, and congestion/potential games.
- **Exact & Approximate Equilibrium Solvers:**
  1. `support_enumeration`: Exhaustive support enumeration across dimension pairs for all isolated and component mixed Nash equilibria.
  2. `lemke_howson`: Linear Complementarity Problem (LCP) pivoting algorithm traversing extreme points to find mixed equilibria in bimatrix games.
  3. `stackelberg`: Bilevel optimization solver identifying optimal leader commitments under follower best response sets.
  4. `pure_nash_enumeration`: Complete profile enumeration with exact unilateral deviation checks.
  5. `dominant_strategy`: Detection of strictly/weakly dominant strategies and Iterated Elimination of Dominated Strategies (IEDS).
  6. `minimax`: Linear programming duality for 2-player zero-sum games with saddle-point detection.
  7. `backward_induction`: Subgame-perfect equilibrium (SPNE) on extensive-form game trees.
  8. `cooperative_solvers`: Axiomatic Shapley value computation and Core feasibility via LP.
  9. `correlated_equilibrium`: Utilitarian social-welfare maximizing correlated equilibrium via LP.
  10. `evolutionary`: Numerical integration of continuous replicator ODEs and Maynard Smith ESS testing.
  11. `regret_matching`: Hart & Mas-Colell no-regret learning converging to correlated equilibrium sets.
- **Memory-Bounded Tiered Decision Core (`optimized_core.py`):**
  * **Tier 1 (Fast Dominance):** $O(m \times n)$ Iterated Elimination of Strictly Dominated Strategies without redundant allocations.
  * **Tier 2 (Bounded Stackelberg):** Bilevel LP optimization over bounded support sets ($k \le 4$).
  * **Tier 3 (Minimax Regret):** Savage Minimax Regret fallback ensuring robust choices under indeterminate equilibria.
  * **Character-Budgeted Payloads:** `< 400` characters / `< 1.2` KB JSON compact verdicts (`CompactStrategicVerdict`).
- **Streamed $O(1)$-Memory Monte Carlo Runtime:**
  * Welford one-pass running mean and variance accumulation.
  * Lower semi-variance and reservoir-sampled Value-at-Risk ($\text{VaR}_{0.95}$) over $10,000+$ rounds under $50$ KB memory footprint.
- **Seven Application Domain Packs:**
  1. **Cybersecurity:** Attacker-defender Stackelberg security games, honeypot signaling, and cyber contagion percolation.
  2. **Economics:** Cournot/Bertrand duopolies, spectrum auctions, and principal-agent contract moral hazard.
  3. **Business Strategy:** R&D patent races, market entry deterrence, and supply chain double marginalization.
  4. **Logistics:** Multi-depot vehicle routing games, cross-docking coalition cost-sharing, and warehouse fulfillment matching.
  5. **Transportation:** Wardrop user equilibrium on traffic networks, Braess's paradox, and dynamic congestion tolling.
  6. **Social Systems:** Public goods voluntary provision, opinion polarization bounded confidence, and strategic voting manipulation.
  7. **Autonomous Systems:** Collision avoidance intersection games, distributed sensor consensus, and multi-robot task allocation.
- **Developer Tooling & Packaging:** Typer CLI (`sse`), Rich-formatted diagnostic suites (`sse doctor`), Python SDK (`SSEClient`), and FastAPI REST microservice.

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

# Install all dependencies (development, scientific, CLI, API)
pip install -e ".[all]"
```

### Run Diagnostic and Test Suite

```bash
# Run the built-in system diagnostic
sse doctor

# Run the complete test suite
pytest
```
*Expected: 133 passed in ~2.4 seconds.*

### CLI Commands

```bash
# Inspect all 7 domain packs
sse domain list

# Inspect a specific domain (Cybersecurity, Economics, Transportation, etc.)
sse domain inspect cybersecurity
sse domain inspect transportation --format json

# Run canonical scenarios directly from the CLI
sse domain run cybersecurity honeypot
sse domain run transportation braess
sse domain run economics cournot

# Solve games using exact or memory-optimized solvers
sse solve examples/prisoners_dilemma.json --method optimized
sse solve examples/matching_pennies.json --method exact

# Run streamed O(1)-memory Monte Carlo simulations
sse simulate examples/prisoners_dilemma.json --rounds 1000 --policy tit_for_tat

# Query live hardware & accelerator telemetry (CPU, RAM, Disk, NVML VRAM on PC-A)
sse telemetry
sse telemetry --format json

# Launch the PC-B distributed execution worker service
sse worker run --host 0.0.0.0 --port 8220

# Sovereign Tri-Node Mesh execution (Air-Gapped Solo / P2P Mesh)
sse node solve --node-id PC_A --solo
sse node run --role PC_B --port 8202
sse node sync --peer-url http://192.168.1.50:8202 --node-id PC_A

# Standalone single-file zero-dependency execution (Mobile / Termux / Server)
python sse_standalone.py doctor
python sse_standalone.py solve
```

---

## Verification Reports

- [Mathematical Verification Report](MATHEMATICAL_VERIFICATION_REPORT.md): Invariant checks across Lemke-Howson, Support Enumeration, Bayesian games, and ESS.
- [Optimized Engine Benchmark](OPTIMIZED_ENGINE_BENCHMARK.md): Empirical benchmarks showing $< 0.45$ MB peak RAM, $< 0.15$ ms solver latency, and $71.8\%$ latency reduction.
- [Domain Packs Verification Report](DOMAIN_PACKS_VERIFICATION_REPORT.md): Formal scenario verification for all 7 application domains.
- [Tri-Node Sovereign Verification Report](TRI_NODE_SOVEREIGN_VERIFICATION.md): Zero-SPOF multi-tier cascades, append-only hash ledgers, tamper rejection, and air-gapped fallback metrics.

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
