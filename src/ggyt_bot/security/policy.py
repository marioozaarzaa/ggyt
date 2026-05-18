from __future__ import annotations

from dataclasses import dataclass


class SecurityError(RuntimeError):
    """Raised when a local-only or live-trading safety invariant is violated."""


@dataclass(frozen=True)
class LocalOnlyPolicy:
    run_mode: str = "LOCAL_ONLY"
    allow_remote: bool = False
    allow_webhooks: bool = False
    allow_external_commands: bool = False
    bind_host: str = "127.0.0.1"

    def validate(self) -> None:
        if self.run_mode != "LOCAL_ONLY":
            raise SecurityError("Only RUN_MODE=LOCAL_ONLY is supported")
        if self.allow_remote:
            raise SecurityError("Remote control is forbidden: ALLOW_REMOTE must be false")
        if self.allow_webhooks:
            raise SecurityError("External webhooks are forbidden: ALLOW_WEBHOOKS must be false")
        if self.allow_external_commands:
            raise SecurityError(
                "External command execution is forbidden: ALLOW_EXTERNAL_COMMANDS must be false"
            )
        if self.bind_host != "127.0.0.1":
            raise SecurityError("Local dashboards/APIs must bind to 127.0.0.1 only")

    def dashboard_host(self) -> str:
        self.validate()
        return "127.0.0.1"


def disable_remote_api() -> None:
    """Documented no-op guard: no remote API surface is registered by this application."""


def disable_external_control() -> None:
    """Documented no-op guard: no webhooks/sockets/external command handlers are registered."""


def enforce_local_only(policy: LocalOnlyPolicy) -> None:
    policy.validate()
    if policy.run_mode == "LOCAL_ONLY":
        disable_remote_api()
        disable_external_control()
