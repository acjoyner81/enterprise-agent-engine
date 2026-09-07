"""Dynatrace & OpenTelemetry instrumentation package."""

from .tracer import DynatraceAgentTracer, tracer

__all__ = ["DynatraceAgentTracer", "tracer"]
