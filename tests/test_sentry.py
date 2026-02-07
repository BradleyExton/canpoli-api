"""Tests for Sentry initialization."""

from __future__ import annotations

from typing import Any

import sentry_sdk
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from canpoli.config import get_settings
from canpoli.sentry import init_sentry


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_init_sentry_no_dsn_does_nothing(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    _clear_settings_cache()

    called = {"count": 0}

    def fake_init(**_kwargs: Any) -> None:
        called["count"] += 1

    monkeypatch.setattr(sentry_sdk, "init", fake_init)

    init_sentry()

    assert called["count"] == 0


def test_init_sentry_with_dsn_sets_expected_options(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "https://public@o0.ingest.sentry.io/0")
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "test")
    monkeypatch.setenv("SENTRY_SEND_DEFAULT_PII", "false")
    monkeypatch.delenv("SENTRY_TRACES_SAMPLE_RATE", raising=False)
    _clear_settings_cache()

    captured: dict[str, Any] = {}

    def fake_init(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(sentry_sdk, "init", fake_init)

    init_sentry()

    assert captured["dsn"] == "https://public@o0.ingest.sentry.io/0"
    assert captured["environment"] == "test"
    assert captured["send_default_pii"] is False
    assert "traces_sample_rate" not in captured


def test_init_sentry_in_lambda_adds_lambda_integration(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "https://public@o0.ingest.sentry.io/0")
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "canpoli-test")
    _clear_settings_cache()

    captured: dict[str, Any] = {}

    def fake_init(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(sentry_sdk, "init", fake_init)

    init_sentry()

    integrations = captured.get("integrations", [])
    assert any(isinstance(i, AwsLambdaIntegration) for i in integrations)
