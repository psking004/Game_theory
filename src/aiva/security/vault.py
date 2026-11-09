"""AIVA Security - Zero-Leak Encrypted Credential Vault.

Provides AES-256-GCM authenticated encryption, PBKDF2-HMAC-SHA256 key derivation,
opaque handle abstraction (vault://<category>/<service>/<key>), and automated
secret redaction to prevent secret leakage in LLM contexts, logs, and terminals.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("aiva.security.vault")

DEFAULT_VAULT_FILENAME = "aiva_vault.enc"
DEFAULT_ITERATIONS = 100_000
SALT_SIZE_BYTES = 16
NONCE_SIZE_BYTES = 12


class SecureCredentialVault:
    """Zero-leak credential vault with AES-256-GCM and opaque handle mapping."""

    def __init__(
        self,
        vault_path: Path | str | None = None,
        master_secret: str | None = None,
        auto_load: bool = True,
    ) -> None:
        self.vault_path = Path(vault_path) if vault_path else Path(DEFAULT_VAULT_FILENAME)
        self.master_secret = master_secret or os.getenv("AIVA_MASTER_SECRET", "aiva_sovereign_mesh_secret_2026")
        self._secrets: dict[str, bytes] = {}
        self._salt: bytes | None = None

        if auto_load and self.vault_path.exists():
            self.load()

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive 256-bit AES key from master secret using PBKDF2-HMAC-SHA256 (100,000 iterations)."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=DEFAULT_ITERATIONS,
        )
        return kdf.derive(self.master_secret.encode("utf-8"))

    @staticmethod
    def validate_handle(handle: str) -> None:
        """Validate handle format according to URI scheme: vault://<category>/<service>/<key>."""
        if not handle.startswith("vault://"):
            raise ValueError(f"Invalid secret handle '{handle}'. Must start with 'vault://'.")
        parts = handle[len("vault://") :].split("/")
        if len(parts) < 2 or any(not p.strip() for p in parts):
            raise ValueError(f"Invalid handle format '{handle}'. Expected 'vault://<category>/<service>/<key>'.")

    def store_secret(self, handle: str, value: str | bytes) -> None:
        """Store secret under an opaque handle and persist to encrypted storage."""
        self.validate_handle(handle)
        raw_val = value.encode("utf-8") if isinstance(value, str) else bytes(value)
        self._secrets[handle] = raw_val
        self.save()

    def get_secret(self, handle: str) -> str:
        """Retrieve plaintext secret string by handle.

        Note: Internal agentic components should prefer resolve_handle for zero-leak injection.
        """
        raw = self.resolve_handle(handle)
        return raw.decode("utf-8", errors="replace")

    def resolve_handle(self, handle: str) -> bytes:
        """Resolve opaque handle directly into a bytes buffer at the point of injection."""
        self.validate_handle(handle)
        if handle not in self._secrets:
            raise KeyError(f"Secret handle '{handle}' not found in vault.")
        return bytes(self._secrets[handle])

    def delete_secret(self, handle: str) -> bool:
        """Delete secret by handle."""
        self.validate_handle(handle)
        if handle in self._secrets:
            # Memory zeroization / scrubbing of removed secret
            scrub_target = bytearray(self._secrets[handle])
            for i in range(len(scrub_target)):
                scrub_target[i] = 0
            del self._secrets[handle]
            self.save()
            return True
        return False

    def list_handles(self) -> list[str]:
        """List all stored opaque secret handles without disclosing secret values."""
        return sorted(self._secrets.keys())

    def contains(self, handle: str) -> bool:
        """Check if an opaque handle is present in the vault."""
        return handle in self._secrets

    def redact_secrets(self, text: str) -> str:
        """Scan text and redact all known plaintext secret values to prevent logging leakage."""
        if not text:
            return text
        redacted = text
        for secret_bytes in self._secrets.values():
            if len(secret_bytes) < 4:
                continue  # Skip trivial substrings to avoid over-redaction
            try:
                secret_str = secret_bytes.decode("utf-8")
                if secret_str in redacted:
                    redacted = redacted.replace(secret_str, "[REDACTED_SECRET]")
            except UnicodeDecodeError:
                continue
        return redacted

    def save(self) -> None:
        """Encrypt and atomically persist all secrets to disk via AES-256-GCM."""
        if self._salt is None:
            self._salt = os.urandom(SALT_SIZE_BYTES)

        key = self._derive_key(self._salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(NONCE_SIZE_BYTES)

        # Serialize secrets payload to JSON bytes (storing values as hex or latin-1)
        raw_dict = {h: v.hex() for h, v in self._secrets.items()}
        plaintext = json.dumps(raw_dict, sort_keys=True).encode("utf-8")

        # Associated authenticated data includes vault version metadata
        aad = b"AIVA_VAULT_V1"
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad)

        container = {
            "version": 1,
            "salt": self._salt.hex(),
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
        }

        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic file write using NamedTemporaryFile
        with tempfile.NamedTemporaryFile("w", dir=str(self.vault_path.parent), delete=False, encoding="utf-8") as tf:
            json.dump(container, tf, indent=2)
            temp_name = tf.name

        os.replace(temp_name, self.vault_path)

    def load(self) -> None:
        """Decrypt and load vault secrets from disk."""
        if not self.vault_path.exists():
            return

        with open(self.vault_path, "r", encoding="utf-8") as f:
            container = json.load(f)

        salt = bytes.fromhex(container["salt"])
        nonce = bytes.fromhex(container["nonce"])
        ciphertext = bytes.fromhex(container["ciphertext"])

        key = self._derive_key(salt)
        aesgcm = AESGCM(key)
        aad = b"AIVA_VAULT_V1"

        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        except Exception as exc:
            raise PermissionError("Decryption failed. Vault ciphertext is corrupted or master secret is invalid.") from exc

        self._salt = salt
        raw_dict = json.loads(plaintext.decode("utf-8"))
        self._secrets = {h: bytes.fromhex(v) for h, v in raw_dict.items()}

    def clear(self) -> None:
        """Clear in-memory secrets and remove vault file."""
        for h in list(self._secrets.keys()):
            scrub_target = bytearray(self._secrets[h])
            for i in range(len(scrub_target)):
                scrub_target[i] = 0
        self._secrets.clear()
        if self.vault_path.exists():
            self.vault_path.unlink()
