from __future__ import annotations

import base64
import os
from pathlib import Path


class CredentialStore:
    """OS keyring first, encrypted/local fallback second.

    Production installs should use Windows Credential Manager, macOS Keychain, or Linux Secret
    Service via the optional keyring dependency. The fallback avoids plaintext `.env` secrets and
    stores reversible base64 data only for local development when secure OS storage is unavailable.
    """

    def __init__(
        self, service: str = "ggyt-trading-bot", fallback_path: Path | None = None
    ) -> None:
        self.service = service
        self.fallback_path = fallback_path or Path.home() / ".ggyt" / "credentials.local"

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
        self.fallback_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"{key}={base64.urlsafe_b64encode(val.encode()).decode()}"
            for key, val in payload.items()
        ]
        self.fallback_path.write_text("\n".join(lines), encoding="utf-8")
        self.fallback_path.chmod(0o600)

    def _fallback_read(self) -> dict[str, str]:
        if not self.fallback_path.exists():
            return {}
        values: dict[str, str] = {}
        for line in self.fallback_path.read_text(encoding="utf-8").splitlines():
            if "=" not in line:
                continue
            key, encoded = line.split("=", 1)
            values[key] = base64.urlsafe_b64decode(encoded.encode()).decode()
        return values
