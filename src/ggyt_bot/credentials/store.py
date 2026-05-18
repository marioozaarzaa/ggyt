from __future__ import annotations

import base64
import os
from pathlib import Path


class CredentialStore:
    """OS keyring first, Fernet-encrypted local fallback second.

    Production installs should use Windows Credential Manager, macOS Keychain, or Linux Secret
    Service via the optional keyring dependency. If keyring is unavailable and cryptography is
    installed, the fallback encrypts values with Fernet and stores them with owner-only perms.
    """

    def __init__(
        self, service: str = "ggyt-trading-bot", fallback_path: Path | None = None
    ) -> None:
        self.service = service
        self.fallback_path = fallback_path or Path.home() / ".ggyt" / "credentials.fernet"
        self.key_path = self.fallback_path.with_suffix(".key")

    def get(self, name: str) -> str | None:
        try:
            import keyring  # type: ignore[import-not-found]

            value = keyring.get_password(self.service, name)
            if value:
                return value
        except Exception:
            pass
        return self._fallback_read().get(name) or os.getenv(name)

    def set(self, name: str, value: str) -> None:
        try:
            import keyring  # type: ignore[import-not-found]

            keyring.set_password(self.service, name, value)
            return
        except Exception:
            pass
        payload = self._fallback_read()
        payload[name] = value
        self._fallback_write(payload)

    def _fallback_read(self) -> dict[str, str]:
        if not self.fallback_path.exists():
            return {}
        try:
            fernet = self._fernet()
        except ModuleNotFoundError:
            return self._legacy_base64_read()
        encrypted = self.fallback_path.read_bytes()
        if not encrypted:
            return {}
        raw = fernet.decrypt(encrypted).decode()
        return dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)

    def _fallback_write(self, payload: dict[str, str]) -> None:
        self.fallback_path.parent.mkdir(parents=True, exist_ok=True)
        raw = "\n".join(f"{key}={value}" for key, value in payload.items()).encode()
        try:
            data = self._fernet().encrypt(raw)
        except ModuleNotFoundError:
            data = base64.urlsafe_b64encode(raw)
        self.fallback_path.write_bytes(data)
        self.fallback_path.chmod(0o600)

    def _fernet(self):
        from cryptography.fernet import Fernet  # type: ignore[import-not-found]

        if not self.key_path.exists():
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            self.key_path.write_bytes(Fernet.generate_key())
            self.key_path.chmod(0o600)
        return Fernet(self.key_path.read_bytes())

    def _legacy_base64_read(self) -> dict[str, str]:
        try:
            raw = base64.urlsafe_b64decode(self.fallback_path.read_bytes()).decode()
        except Exception:
            return {}
        return dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
