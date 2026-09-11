"""Structured JSON logging configured for Splunk ingestion and distributed tracing."""

import datetime
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

# Context variable to hold request correlation ID across async agent tasks
current_correlation_id: ContextVar[str] = ContextVar(
    "current_correlation_id", default=""
)


class DynamicStreamHandler(logging.StreamHandler):
    """Stream handler that dynamically references current sys.stdout to prevent closed stream errors."""

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, val):
        pass


def add_correlation_id(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Inject correlation_id if present in contextvars and not already in event_dict."""
    if "correlation_id" not in event_dict or not event_dict["correlation_id"]:
        corr_id = current_correlation_id.get()
        if not corr_id:
            corr_id = f"corr-{uuid.uuid4().hex[:12]}"
            current_correlation_id.set(corr_id)
        event_dict["correlation_id"] = corr_id
    return event_dict


def add_iso_timestamp(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add ISO-8601 UTC timestamp for high precision Splunk event indexing."""
    if "timestamp" not in event_dict:
        event_dict["timestamp"] = datetime.datetime.now(datetime.UTC).isoformat()
    return event_dict


def configure_telemetry_logger(log_level: str = "INFO") -> None:
    """Configure structlog processors to emit Splunk-ready structured JSON."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = DynamicStreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(stream_handler)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            add_correlation_id,
            add_iso_timestamp,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "enterprise-agent") -> structlog.stdlib.BoundLogger:
    """Obtain a structured logger instance bound with a name."""
    return structlog.get_logger(name)


def log_llm_execution(
    logger: structlog.stdlib.BoundLogger,
    *,
    correlation_id: str,
    agent_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    execution_time_ms: float,
    model_name: str,
    status: str = "SUCCESS",
    cost_usd: float | None = None,
    **extra: Any,
) -> None:
    """Log an LLM or Agent execution event with full token, latency, and cost telemetry."""
    event_payload = {
        "correlation_id": correlation_id,
        "agent_name": agent_name,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "execution_time_ms": round(execution_time_ms, 2),
        "model_name": model_name,
        "status": status,
        **extra,
    }
    if cost_usd is not None:
        event_payload["cost_usd"] = cost_usd

    logger.info("llm_call_completed", **event_payload)
