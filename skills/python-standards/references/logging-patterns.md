# Structlog Logging Patterns

Detailed patterns for structlog configuration and usage in this project.

## Basic Setup

Import and use the logger:

```python
import structlog

log = structlog.get_logger()
```

## Event-Based Logging

Log events with structured context, not string interpolation:

```python
# Good - structured context
log.info("user_created", user_id=123, email="user@example.com")
log.error("payment_failed", order_id=456, reason="insufficient_funds")

# Bad - string interpolation
log.info(f"User {user_id} created")  # Don't do this
```

## Application Configuration

Configure structlog at application entry point:

```python
from __future__ import annotations

import logging
import os
import structlog


def configure_logging(*, json_output: bool | None = None) -> None:
    """Configure structlog for the application.

    Args:
        json_output: Force JSON output. If None, auto-detect from ENV.
    """
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
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
```

## Sensitive Field Filtering

Filter sensitive fields before logging:

```python
def filter_sensitive(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Remove sensitive fields from log output."""
    sensitive_keys = {"password", "token", "secret", "api_key", "authorization"}
    return {
        k: "[REDACTED]" if k.lower() in sensitive_keys else v
        for k, v in event_dict.items()
    }
```

Add to processors:

```python
processors = [
    filter_sensitive,  # Add early in chain
    structlog.processors.add_log_level,
    # ... rest of processors
]
```

## Context Variables

Add context that persists across log calls:

```python
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

# At request start
bind_contextvars(request_id="abc-123", user_id=456)

# All subsequent logs include request_id and user_id
log.info("processing_started")  # Includes request_id, user_id
log.info("item_processed", item_id=789)  # Includes request_id, user_id

# At request end
clear_contextvars()
```

## Exception Logging

Log exceptions with full context:

```python
try:
    process_payment(order_id=123)
except PaymentError as e:
    log.exception(
        "payment_processing_failed",
        order_id=e.order_id,
        reason=e.reason,
    )
    raise
```

## Log Levels

Use appropriate log levels:

| Level | Use For |
|-------|---------|
| `debug` | Detailed diagnostic info (disabled in production) |
| `info` | Normal operations, events |
| `warning` | Unexpected but handled situations |
| `error` | Errors that need attention |
| `exception` | Errors with stack trace |

## GCP Cloud Logging Integration

For GCP environments, configure JSON output with Cloud Logging format:

```python
def configure_gcp_logging() -> None:
    """Configure structlog for GCP Cloud Logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            # GCP expects 'severity' not 'level'
            structlog.processors.CallsiteParameterAdder(
                [structlog.processors.CallsiteParameter.FUNC_NAME]
            ),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
```

## Testing with Logs

Capture logs in tests:

```python
import structlog
from structlog.testing import capture_logs


def test_logs_user_creation() -> None:
    with capture_logs() as logs:
        create_user(email="test@example.com")

    assert len(logs) == 1
    assert logs[0]["event"] == "user_created"
    assert logs[0]["email"] == "test@example.com"
```

## References

- [ADR-004: Prescribed Dependencies](../../../docs/adr/004-prescribed-dependencies.md)
- [TDD-002: GCP Logging Integration](../../../docs/tdd/002-gcp-logging-integration.md)
- [structlog Documentation](https://www.structlog.org/)
