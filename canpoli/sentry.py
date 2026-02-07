"""Sentry initialization."""

from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from canpoli.config import get_settings


def init_sentry() -> None:
    """Initialize Sentry if a DSN is configured."""
    settings = get_settings()
    if not settings.sentry_dsn:
        return

    environment = settings.sentry_environment or (
        "development" if settings.debug else "production"
    )

    init_kwargs: dict[str, object] = {
        "dsn": settings.sentry_dsn,
        "environment": environment,
        "release": settings.sentry_release,
        "send_default_pii": settings.sentry_send_default_pii,
    }

    if settings.is_lambda:
        init_kwargs["integrations"] = [AwsLambdaIntegration()]

    if settings.sentry_traces_sample_rate is not None:
        init_kwargs["traces_sample_rate"] = settings.sentry_traces_sample_rate

    sentry_sdk.init(**init_kwargs)
