"""Dynatrace APM & OpenTelemetry distributed tracing integration."""

import os
import uuid
from typing import Any

import httpx
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from src.telemetry.logger import get_logger

DT_ENVIRONMENT_URL = os.getenv(
    "DT_ENVIRONMENT_URL", "https://your-env.live.dynatrace.com"
)
DT_API_TOKEN = os.getenv("DT_API_TOKEN", "")

logger = get_logger("dynatrace-apm")

# Configure TracerProvider
resource = Resource.create(
    {
        "service.name": "enterprise-agent-engine",
        "service.version": "0.1.0",
        "service.namespace": "enterprise-ai",
        "k8s.namespace.name": "acjoyner-dev",
        "environment": os.environ.get("DEPLOYMENT_ENV", "development"),
    }
)

provider = TracerProvider(resource=resource)
# If DYNATRACE_API_URL is set, wire OTLP exporter
if os.environ.get("DYNATRACE_API_URL"):
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    otlp_exporter = OTLPSpanExporter(
        endpoint=f"{os.environ['DYNATRACE_API_URL']}/api/v2/otlp/v1/traces",
        headers={
            "Authorization": f"Api-Token {os.environ.get('DYNATRACE_API_TOKEN', '')}"
        },
    )
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    logger.info(
        "dynatrace_otlp_exporter_configured", endpoint=os.environ["DYNATRACE_API_URL"]
    )

trace.set_tracer_provider(provider)
tracer = trace.get_tracer("enterprise-agent-engine", "0.1.0")
propagator = TraceContextTextMapPropagator()


class DynatraceAgentTracer:
    """Manages OpenTelemetry spans compatible with Dynatrace PurePath distributed tracing."""

    @staticmethod
    def get_tracer():
        return tracer

    @staticmethod
    def inject_w3c_trace_headers(
        headers: dict[str, str] | None = None,
        span: Any | None = None,
    ) -> dict[str, str]:
        """Inject W3C traceparent headers for distributed tracing to downstream Spring Boot services."""
        hdrs = headers.copy() if headers else {}
        current_span = span or trace.get_current_span()
        span_ctx = current_span.get_span_context() if current_span else None

        if span_ctx and span_ctx.is_valid:
            propagator.inject(hdrs)
        else:
            trace_id = uuid.uuid4().hex
            span_id = uuid.uuid4().hex[:16]
            hdrs["traceparent"] = f"00-{trace_id}-{span_id}-01"

        return hdrs

    @staticmethod
    def start_agent_span(
        name: str,
        correlation_id: str,
        agent_name: str,
        model_name: str | None = None,
        attributes: dict[str, Any] | None = None,
    ):
        """Create an OpenTelemetry span with standardized AI and Dynatrace tags."""
        attrs = {
            "ai.correlation_id": correlation_id,
            "ai.agent.name": agent_name,
            "k8s.namespace.name": "acjoyner-dev",
        }
        if model_name:
            attrs["ai.model.name"] = model_name
        if attributes:
            attrs.update(attributes)

        return tracer.start_span(name, attributes=attrs)

    @staticmethod
    async def verify_trace_ingestion(trace_id: str) -> dict[str, Any]:
        """Queries the Dynatrace v2 Traces API to verify if trace_id has been processed."""
        if not DT_API_TOKEN:
            return {
                "status": "SKIPPED",
                "message": "DT_API_TOKEN environment variable not set.",
                "trace_id": trace_id,
            }

        url = f"{DT_ENVIRONMENT_URL.rstrip('/')}/api/v2/traces/{trace_id}"
        headers = {
            "Authorization": f"Api-Token {DT_API_TOKEN}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "VERIFIED",
                        "trace_id": trace_id,
                        "span_count": len(data.get("spans", [])),
                        "root_service": data.get("rootServiceName", "Unknown"),
                        "details": data,
                    }
                if response.status_code == 404:
                    return {
                        "status": "PENDING_INGESTION",
                        "trace_id": trace_id,
                        "message": "Trace not yet indexed in Dynatrace.",
                    }
                return {
                    "status": "API_ERROR",
                    "status_code": response.status_code,
                    "message": response.text,
                }
            except httpx.HTTPError as exc:
                return {
                    "status": "CONNECTION_FAILED",
                    "error": str(exc),
                }


# Module-level alias exports for direct imports
inject_w3c_trace_headers = DynatraceAgentTracer.inject_w3c_trace_headers
verify_trace_ingestion = DynatraceAgentTracer.verify_trace_ingestion
