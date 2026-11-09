"""AIVA - Autonomous Intelligent Virtual Agent Platform.

Models the 7 core pillars of production autonomous systems:
1. Connected Accounts (Zero-password OAuth broker)
2. Dedicated Compute Workspace (Isolated scratchpad execution on PC-B / worktrees)
3. Real Headless Browsers (DOM automation & direct-fill secret injection)
4. Zero-Leak Credential Vault (AES-256-GCM encrypted storage)
5. Structured Long-Term Memory (Biographical profile + episodic hash-chain ledger)
6. Proactive Background Daemon (Scheduled tasks & morning brief P2P push)
7. Cryptographic Guardrails (2-of-3 threshold quorum authorization for irreversible actions)
"""

from aiva.browser.controller import HeadlessBrowserSupervisor, VirtualDOMSession
from aiva.governance.guardrails import AivaGuardrailGate, AutonomyTier
from aiva.integrations.oauth_broker import OAuthBroker
from aiva.memory.profile import AivaMemoryManager
from aiva.proactive.daemon import ProactiveDaemon
from aiva.security.vault import SecureCredentialVault

__all__ = [
    "AivaGuardrailGate",
    "AivaMemoryManager",
    "AutonomyTier",
    "HeadlessBrowserSupervisor",
    "OAuthBroker",
    "ProactiveDaemon",
    "SecureCredentialVault",
    "VirtualDOMSession",
]
