"""Tests for application factory."""

from fastapi import FastAPI

from canpoli.app import create_app


def test_create_app_builds_fastapi():
    app = create_app()
    assert isinstance(app, FastAPI)

    paths = {route.path for route in app.router.routes}
    assert "/health" in paths
