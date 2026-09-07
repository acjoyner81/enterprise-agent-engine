"""Distributed Tracing Module integrating LangSmith and local Splunk span collectors."""

import os
import time
import uuid
from typing import Any, Dict, List, Optional
from langsmith.run_trees import RunTree
from src.telemetry.logger import get_logger

logger = get_logger("distributed-tracer")


class LocalSpan:
    """Local representation of an execution span when running offline without LangSmith keys."""

    def __init__(
        self,
        name: str,
        run_type: str,
        inputs: Dict[str, Any],
        correlation_id: str,
        parent_id: Optional[str] = None,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.run_type = run_type
        self.inputs = inputs
        self.correlation_id = correlation_id
        self.parent_id = parent_id
        self.start_time = time.perf_counter()
        self.outputs: Dict[str, Any] = {}
        self.error: Optional[str] = None
        self.duration_ms: float = 0.0

    def end(self, outputs: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        """Mark span as finished and record duration."""
        self.duration_ms = (time.perf_counter() - self.start_time) * 1000
        self.outputs = outputs or {}
        self.error = error

        logger.info(
            "span_completed",
            span_id=self.id,
            parent_id=self.parent_id,
            name=self.name,
            run_type=self.run_type,
            correlation_id=self.correlation_id,
            duration_ms=round(self.duration_ms, 2),
            status="ERROR" if error else "SUCCESS",
            error=error,
        )


class DistributedTracer:
    """Enterprise tracer managing LangSmith RunTrees and offline local spans."""

    def __init__(self, project_name: str = "enterprise-agent-engine"):
        self.project_name = project_name
        self.has_langsmith_key = bool(os.environ.get("LANGCHAIN_API_KEY"))

        if self.has_langsmith_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = project_name
            logger.info("langsmith_tracing_enabled", project=project_name)
        else:
            logger.info("local_span_tracing_active", reason="LANGCHAIN_API_KEY not configured")

    def start_trace(
        self,
        name: str,
        run_type: str = "chain",
        inputs: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Any:
        """Initialize a root trace for an agent, tool, or chain execution."""
        corr_id = correlation_id or f"corr-trace-{uuid.uuid4().hex[:8]}"
        inp = inputs or {}

        if self.has_langsmith_key:
            try:
                run = RunTree(
                    name=name,
                    run_type=run_type,
                    inputs=inp,
                    project_name=self.project_name,
                    extra={"correlation_id": corr_id},
                )
                run.post()
                return run
            except Exception as exc:
                logger.warning("langsmith_post_failed", error=str(exc))

        # Fallback to local high-precision span
        return LocalSpan(
            name=name,
            run_type=run_type,
            inputs=inp,
            correlation_id=corr_id,
        )

    def create_child_span(
        self,
        parent_span: Any,
        name: str,
        run_type: str = "tool",
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Create a child span nested under a parent trace node."""
        inp = inputs or {}
        if isinstance(parent_span, RunTree) and self.has_langsmith_key:
            try:
                child = parent_span.create_child(
                    name=name,
                    run_type=run_type,
                    inputs=inp,
                )
                child.post()
                return child
            except Exception as exc:
                logger.warning("langsmith_child_post_failed", error=str(exc))

        # Fallback to child LocalSpan
        parent_id = getattr(parent_span, "id", None)
        corr_id = getattr(parent_span, "correlation_id", "unassigned")
        return LocalSpan(
            name=name,
            run_type=run_type,
            inputs=inp,
            correlation_id=corr_id,
            parent_id=parent_id,
        )

    def end_span(
        self,
        span: Any,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """End trace span and persist outputs to LangSmith or Splunk logger."""
        out = outputs or {}
        if isinstance(span, RunTree) and self.has_langsmith_key:
            try:
                span.end(outputs=out, error=error)
                span.patch()
                return
            except Exception as exc:
                logger.warning("langsmith_patch_failed", error=str(exc))

        if isinstance(span, LocalSpan):
            span.end(outputs=out, error=error)
