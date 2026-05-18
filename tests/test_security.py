import pytest

from ggyt_bot.security.policy import LocalOnlyPolicy, SecurityError, enforce_local_only
from ggyt_bot.settings import RuntimeSettings


def test_local_only_rejects_remote_bind() -> None:
    with pytest.raises(SecurityError):
        enforce_local_only(LocalOnlyPolicy(bind_host="0.0.0.0"))


def test_live_trading_requires_confirmed_account_id() -> None:
    settings = RuntimeSettings(
        alpaca_paper=False,
        ggyt_allow_live_trading=True,
        ggyt_dry_run=True,
        ggyt_confirm_live_account_id="",
    )

    with pytest.raises(ValueError, match="GGYT_CONFIRM_LIVE_ACCOUNT_ID"):
        settings.validate_execution_safety()
