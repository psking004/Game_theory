"""Strategic Systems Engine - Tri-Node Adversarial Arena Tournament Dispatcher.

Offloads heavy adversarial Monte Carlo and concurrency stress tournaments
from Node A to Node B over the zero-hang P2P mesh, with immediate fallback
to local execution on network partitions.
"""

from __future__ import annotations

import contextlib
import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

from sse.swarm.arena import SwarmArena, TournamentSummary
from sse.tri_node.sovereign_core import NodeID

logger = logging.getLogger("sse.tri_node.arena_dispatcher")


class ArenaTournamentDispatcher:
    """Dispatches adversarial tournament workloads across the Sovereign Tri-Node Mesh."""

    def __init__(
        self,
        node_id: str | NodeID = NodeID.PC_A,
        peer_url: str = "http://127.0.0.1:8202",
        local_arena: SwarmArena | None = None,
    ) -> None:
        self.node_id = str(node_id.value if isinstance(node_id, NodeID) else node_id)
        self.peer_url = peer_url.rstrip("/")
        self.local_arena = local_arena or SwarmArena()

    def dispatch_tournament(
        self,
        workspace_dir: Path | str,
        candidate_id: str = "candidate_01",
        rounds: int = 20,
        timeout: float = 15.0,
    ) -> TournamentSummary:
        """Attempt to offload tournament execution to peer node; fallback to local on failure."""
        work_path = Path(workspace_dir).resolve()

        # 1. Package workspace files for offload
        files: dict[str, str] = {}
        if work_path.exists():
            for p in work_path.rglob("*"):
                if p.is_file():
                    rel = str(p.relative_to(work_path)).replace("\\", "/")
                    with contextlib.suppress(Exception):
                        files[rel] = p.read_text(encoding="utf-8")

        # 2. Attempt remote dispatch
        if self.peer_url:
            url = f"{self.peer_url}/mesh/arena"
            req_data = {
                "candidate_id": candidate_id,
                "rounds": rounds,
                "files": files,
                "sender_node_id": self.node_id,
            }
            body = json.dumps(req_data, separators=(",", ":")).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        res_json = json.loads(resp.read().decode("utf-8"))
                        return TournamentSummary(
                            candidate_id=res_json["candidate_id"],
                            rounds_played=res_json["rounds"],
                            wins=res_json["wins"],
                            losses=res_json["losses"],
                            draws=res_json["draws"],
                            survival_rate=res_json["survival_rate"],
                            initial_elo=res_json["initial_elo"],
                            final_elo=res_json["final_elo"],
                            elo_delta=res_json["elo_delta"],
                            passed_gate=res_json["passed_gate"],
                            worst_case_regret=res_json["worst_case_regret"],
                        )
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                logger.warning(
                    "Arena peer %s unreachable (%s). Initiating instant local fallback on %s.",
                    self.peer_url,
                    exc,
                    self.node_id,
                )

        # 3. Local Sovereign Execution Fallback (Zero socket hanging, 100% resilient)
        return self.local_arena.run_tournament(
            workspace_dir=work_path,
            candidate_id=candidate_id,
            rounds=rounds,
        )
