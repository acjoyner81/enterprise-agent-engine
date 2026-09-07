import pytest
from src.tracing.langsmith_tracker import DistributedTracer, LocalSpan
from src.evals.guardrail_eval import run_guardrail_evaluations

def test_distributed_tracer_local_span():
    tracer = DistributedTracer(project_name="test-project")
    root_span = tracer.start_trace(
        name="root-agent-chain",
        run_type="chain",
        inputs={"prompt": "Analyze cluster"},
        correlation_id="corr-trace-test-01"
    )
    
    assert root_span is not None
    corr = getattr(root_span, "correlation_id", None) or (
        root_span.extra.get("correlation_id") if hasattr(root_span, "extra") else None
    )
    assert corr == "corr-trace-test-01"
    
    child_span = tracer.create_child_span(
        parent_span=root_span,
        name="mcp-system-health",
        run_type="tool",
        inputs={"tool": "get_system_health"}
    )
    assert child_span is not None
    
    tracer.end_span(child_span, outputs={"status": "HEALTHY"})
    tracer.end_span(root_span, outputs={"result": "Cluster is healthy"})

def test_guardrail_benchmark_evaluations():
    summary = run_guardrail_evaluations()
    assert summary.total_tests == 10
    assert summary.passed_tests == 10
    assert summary.failed_tests == 0
    assert summary.accuracy_pct == 100.0
    assert summary.avg_latency_ms < 50.0  # Fast sub-millisecond execution
    assert "INJECTION" in summary.category_scores
    assert "PII" in summary.category_scores
    assert "BENIGN" in summary.category_scores
