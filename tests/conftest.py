"""Shared pytest configuration and fixtures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "e2e: end-to-end tests requiring Claude CLI")
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Skip E2E tests if Claude CLI is not available."""
    if not shutil.which("claude"):
        skip_marker = pytest.mark.skip(reason="Claude CLI not found in PATH")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def plugin_root() -> Path:
    """Path to the plugin source directory."""
    return Path(__file__).parent.parent.absolute()
