# TDD-002: structlog GCP Cloud Logging Integration

| Field | Value |
|-------|-------|
| Version | 0.2.0 |
| Date | 2025-12-29 |
| Related ADRs | [ADR-004](../adr/004-prescribed-dependencies.md) |

## Overview

This TDD provides **consumer guidance** for integrating structlog with GCP Cloud Logging. The plugin does not implement logging itself—consumers configure logging in their applications.

## Plugin Role

| Aspect         | Plugin Responsibility                                     |
| -------------- | --------------------------------------------------------- |
| Enforcement    | Ruff T201 bans `print()` in src/ (encourages structlog)   |
| Guidance       | SKILL.md documents patterns; CLAUDE.md references ADR-004 |
| Dependencies   | Consumer template includes structlog in pyproject.toml    |
| Implementation | Consumer responsibility (patterns documented below)       |

## Consumer Implementation

### Dependencies

```toml
[project]
dependencies = [
    "structlog>=24.1.0",
]

[project.optional-dependencies]
gcp = [
    "google-cloud-logging>=3.10.0",
]
```

### Standard Configuration

```python
# src/package_name/logging_config.py
from __future__ import annotations

import logging
import os
import sys

import structlog


def configure_logging(
    *,
    json_output: bool | None = None,
    level: int = logging.INFO,
) -> None:
    if json_output is None:
        json_output = os.getenv("ENV", "development") != "development"

    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### GCP Cloud Functions Configuration

```python
# src/package_name/logging_gcp.py
from __future__ import annotations

import logging

import structlog
from google.cloud import logging as gcp_logging


def configure_gcp_logging(*, level: int = logging.INFO) -> None:
    client = gcp_logging.Client()
    client.setup_logging()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.EventRenamer("message"),  # GCP expects 'message'
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

## Field Mapping

| structlog | GCP Cloud Logging |
|-----------|-------------------|
| `event` | `message` (via EventRenamer) |
| `level` | `severity` (auto-mapped) |
| `timestamp` | `timestamp` |
| Other keys | `jsonPayload.*` |

## Security: Sensitive Field Filtering

```python
def filter_sensitive(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    sensitive_keys = {"password", "token", "secret", "api_key"}
    return {k: v for k, v in event_dict.items() if k not in sensitive_keys}
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Logs not in GCP | Verify `setup_logging()` called |
| Duplicate logs | Use `cache_logger_on_first_use=True` |
| Missing context | Ensure `merge_contextvars` is first processor |
