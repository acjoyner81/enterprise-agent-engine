"""Dynatrace APM & OpenTelemetry distributed tracing integration."""

import os
import uuid
from typing import Any, Dict, Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from src.telemetry.logger import get_logger

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
        headers={"Authorization": f"Api-Token {os.environ.get('DYNATRACE_API_TOKEN', '')}"},
    )
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    logger.info("dynatrace_otlp_exporter_configured", endpoint=os.environ["DYNATRACE_API_URL"])

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
        headers: Optional[Dict[str, str]] = None,
        span: Optional[Any] = None,
    ) -> Dict[str, str]:
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
        model_name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
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
# Alias for module-level import backward compatibility
inject_w3c_trace_headers = DynatraceAgentTracer.inject_w3c_trace_headers